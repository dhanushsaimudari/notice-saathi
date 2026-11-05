import io
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Header, status, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel

from backend.config import settings
from backend.database.session import get_db, init_db
from backend.database.models import Document, ActionCard, TextBlock, ExtractedFact
from backend.modules.auth.service import (
    get_or_create_guest_session,
    get_current_actor_id,
    verify_document_ownership,
    record_consent,
    revoke_consent,
    has_consent,
    get_actor_consents,
    CONSENT_SCOPES
)
from backend.modules.documents.service import create_document_record, process_document_pipeline, delete_document_cascade
from backend.modules.answers.service import answer_user_question
from backend.modules.gnani_stt.adapter import gnani_stt_adapter
from backend.modules.gnani_tts.adapter import gnani_tts_adapter

# Initialize DB tables
init_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Evidence-first, voice-enabled document understanding application API."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Schemas ---

class SessionResponse(BaseModel):
    session_id: str
    token: str
    status: str

class ConsentUpdateRequest(BaseModel):
    consents: Dict[str, bool]

class QuestionRequest(BaseModel):
    question_text: str
    response_language: str = "te-IN"
    user_context: Optional[str] = None
    allow_english_audio: bool = False
    consent_for_cloud_translation: bool = False

class SpeechRequest(BaseModel):
    text: str
    language: str = "te-IN"
    speed: float = 1.0

# --- Health Check ---
@app.get("/api/v1/health")
def health_check(db: Session = Depends(get_db)):
    """Comprehensive readiness and health probe for staging and pilot deployment."""
    # 1. Check DB connectivity
    db_ok = True
    try:
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    # 2. Check storage directory accessibility
    storage_ok = True
    try:
        import os
        from pathlib import Path
        storage_path = Path(settings.STORAGE_LOCAL_DIR)
        storage_path.mkdir(parents=True, exist_ok=True)
        test_file = storage_path / ".health_check.tmp"
        test_file.write_text("probe")
        test_file.unlink()
    except Exception:
        storage_ok = False

    # 3. Check OCR Engine status
    ocr_ok = True
    try:
        from backend.modules.ocr.service import _ocr_engine
        ocr_ok = _ocr_engine is not None
    except Exception:
        ocr_ok = False

    is_healthy = db_ok and storage_ok and ocr_ok
    status_str = "healthy" if is_healthy else "degraded"

    return {
        "status": status_str,
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": {
            "database": "connected" if db_ok else "failed",
            "storage": "writable" if storage_ok else "failed",
            "ocr_engine": "ready" if ocr_ok else "failed"
        },
        "gnani_integration": {
            "configured": bool(settings.GNANI_API_KEY),
            "mode": "live" if bool(settings.GNANI_API_KEY) else "mock_development",
            "stt_endpoint": settings.GNANI_STT_ENDPOINT,
            "tts_endpoint": settings.GNANI_TTS_ENDPOINT
        },
        "translation_engine": {
            "default_provider": settings.TRANSLATION_PROVIDER,
            "grounded_local_engine": "ready",
            "cloud_consent_required": settings.REQUIRE_CONSENT_FOR_CLOUD_TRANSLATION
        }
    }

# --- Auth / Session & Consent ---
@app.post("/api/v1/auth/session", response_model=SessionResponse)
def create_session(
    token: Optional[str] = None,
    db: Session = Depends(get_db)
):
    session = get_or_create_guest_session(db, token)
    return {
        "session_id": session.session_id,
        "token": session.token,
        "status": session.status
    }

@app.get("/api/v1/auth/consent")
def get_consent_status(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Retrieves current granular consent state for the active session."""
    actor_id = get_current_actor_id(db, authorization, x_session_token)
    return {
        "actor_id": actor_id,
        "consents": get_actor_consents(db, actor_id)
    }

@app.post("/api/v1/auth/consent")
def update_consent(
    payload: ConsentUpdateRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Updates user consent preferences with explicit backend persistence."""
    actor_id = get_current_actor_id(db, authorization, x_session_token)
    for purpose, is_granted in payload.consents.items():
        if purpose in CONSENT_SCOPES:
            if is_granted:
                record_consent(db, actor_id, purpose)
            else:
                revoke_consent(db, actor_id, purpose)
                
    return {
        "success": True,
        "actor_id": actor_id,
        "consents": get_actor_consents(db, actor_id)
    }

# --- Documents ---
@app.post("/api/v1/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    consent_document_processing: Optional[bool] = Form(None),
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    actor_id = get_current_actor_id(db, authorization, x_session_token)
    
    # Backend consent enforcement for server-side document processing
    if consent_document_processing is True:
        record_consent(db, actor_id, "document_processing")
    elif consent_document_processing is False:
        revoke_consent(db, actor_id, "document_processing")
        
    if not has_consent(db, actor_id, "document_processing"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "CONSENT_REQUIRED_DOCUMENT_PROCESSING",
                "message": "Explicit consent for document processing on NoticeSaathi backend server is required before uploading.",
                "scope": "document_processing",
                "recoverable": True
            }
        )

    content = await file.read()
    
    # 1. Create record and store safely
    doc = create_document_record(
        db=db,
        owner_id=actor_id,
        file_bytes=content,
        original_filename=file.filename or "upload.pdf",
        declared_media_type=file.content_type or "application/pdf"
    )
    
    # 2. Synchronous trigger for MVP/local pipeline (or enqueued worker)
    processed_doc = process_document_pipeline(db, doc.document_id)
    
    return {
        "document_id": processed_doc.document_id,
        "state": processed_doc.state,
        "original_filename": processed_doc.original_filename,
        "page_count": processed_doc.page_count
    }

@app.get("/api/v1/documents")
def list_documents(
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    actor_id = get_current_actor_id(db, authorization, x_session_token)
    docs = db.query(Document).filter(
        Document.owner_id == actor_id,
        Document.deleted_at.is_(None)
    ).order_by(Document.created_at.desc()).all()
    
    return [
        {
            "document_id": d.document_id,
            "original_filename": d.original_filename,
            "state": d.state,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "page_count": d.page_count
        }
        for d in docs
    ]

@app.get("/api/v1/documents/{document_id}")
def get_document(
    document_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    actor_id = get_current_actor_id(db, authorization, x_session_token)
    doc = verify_document_ownership(db, document_id, actor_id)
    
    pages = [
        {
            "page_id": p.page_id,
            "page_index": p.page_index,
            "quality_state": p.quality_state,
            "width": p.width,
            "height": p.height
        }
        for p in doc.pages
    ]
    
    return {
        "document_id": doc.document_id,
        "original_filename": doc.original_filename,
        "state": doc.state,
        "page_count": doc.page_count,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "pages": pages
    }

@app.get("/api/v1/documents/{document_id}/status")
def get_document_status(
    document_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    actor_id = get_current_actor_id(db, authorization, x_session_token)
    doc = verify_document_ownership(db, document_id, actor_id)
    
    message = "Document is ready."
    if doc.state == "NEEDS_RECAPTURE":
        message = "Image quality is too low or blurry to verify important details. Please take a clearer photo."
    elif doc.state == "PROCESSING":
        message = "Extracting text and verifying evidence..."
        
    return {
        "document_id": doc.document_id,
        "state": doc.state,
        "message": message
    }

@app.get("/api/v1/documents/{document_id}/action-cards")
def get_action_cards(
    document_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    actor_id = get_current_actor_id(db, authorization, x_session_token)
    doc = verify_document_ownership(db, document_id, actor_id)
    
    cards = db.query(ActionCard).filter(ActionCard.document_id == document_id).all()
    return {
        "document_id": doc.document_id,
        "document_state": doc.state,
        "cards": [
            {
                "card_id": c.card_id,
                "title": c.title,
                "what_says": c.what_says,
                "what_means": c.what_means,
                "what_action": c.what_action,
                "uncertainty": c.uncertainty,
                "proof_refs": c.proof_refs,
                "status": c.status,
                "approved_spoken_output": f"{c.what_means} {c.what_action}".strip()
            }
            for c in cards
        ]
    }

@app.get("/api/v1/documents/{document_id}/pages")
def get_document_pages(
    document_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    actor_id = get_current_actor_id(db, authorization, x_session_token)
    doc = verify_document_ownership(db, document_id, actor_id)
    
    blocks = db.query(TextBlock).filter(TextBlock.document_id == document_id).all()
    return {
        "document_id": doc.document_id,
        "blocks": [
            {
                "block_id": b.block_id,
                "page_index": getattr(b, "page_number", 1),
                "text_original": b.text_original,
                "bbox": b.bbox,
                "confidence": b.confidence
            }
            for b in blocks
        ]
    }

@app.post("/api/v1/documents/{document_id}/questions")
def ask_question(
    document_id: str,
    payload: QuestionRequest,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    actor_id = get_current_actor_id(db, authorization, x_session_token)
    doc = verify_document_ownership(db, document_id, actor_id)
    
    # Check persistent consent for external translation
    has_cloud_consent = (
        payload.consent_for_cloud_translation 
        or has_consent(db, actor_id, "external_translation")
    )
    
    result = answer_user_question(
        db=db,
        document_id=doc.document_id,
        question_text=payload.question_text,
        user_context=payload.user_context,
        language=payload.response_language,
        allow_english_audio=payload.allow_english_audio,
        has_cloud_consent=has_cloud_consent
    )
    return result

@app.post("/api/v1/documents/{document_id}/voice-turns")
def voice_question_turn(
    document_id: str,
    audio_file: UploadFile = File(...),
    language_code: str = Form("te-IN"),
    consent_gnani_stt: Optional[bool] = Form(None),
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    actor_id = get_current_actor_id(db, authorization, x_session_token)
    doc = verify_document_ownership(db, document_id, actor_id)
    
    if consent_gnani_stt is True:
        record_consent(db, actor_id, "gnani_stt")
    elif consent_gnani_stt is False:
        revoke_consent(db, actor_id, "gnani_stt")
        
    if not has_consent(db, actor_id, "gnani_stt"):
        # Without permission: DO NOT transmit microphone audio to Gnani STT
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "CONSENT_REQUIRED_GNANI_STT",
                "message": "Microphone audio was not transmitted. Consent for transmitting voice recordings to Gnani Prisma STT has not been granted.",
                "scope": "gnani_stt",
                "text_alternative": "You can type your question directly in the text box below without transmitting any audio recordings.",
                "recoverable": True
            }
        )
    
    content = audio_file.file.read()
    stt_result = gnani_stt_adapter.transcribe(content, language_code=language_code)
    
    transcript = stt_result.get("transcript", "")
    
    # Process question against document if transcript exists
    answer_result = None
    if transcript:
        has_cloud = has_consent(db, actor_id, "external_translation")
        answer_result = answer_user_question(
            db=db,
            document_id=doc.document_id,
            question_text=transcript,
            language=language_code,
            has_cloud_consent=has_cloud
        )
        
    return {
        "stt": stt_result,
        "transcript": transcript,
        "answer": answer_result
    }

@app.post("/api/v1/speech/synthesize")
def synthesize_speech(
    payload: SpeechRequest,
    consent_gnani_tts: Optional[bool] = Header(None),
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """Synthesizes validated answer text into audio."""
    actor_id = get_current_actor_id(db, authorization, x_session_token)
    
    if consent_gnani_tts is True:
        record_consent(db, actor_id, "gnani_tts")
    elif consent_gnani_tts is False:
        revoke_consent(db, actor_id, "gnani_tts")
        
    if not has_consent(db, actor_id, "gnani_tts"):
        # Without permission: DO NOT transmit text to external TTS services
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "CONSENT_REQUIRED_GNANI_TTS",
                "message": "Speech synthesis was refused. Consent for transmitting explanation text to Gnani Timbre TTS has not been granted.",
                "scope": "gnani_tts",
                "text_alternative": "The complete explanation and source proof are displayed directly on screen in high-contrast text.",
                "recoverable": True
            }
        )
        
    audio_bytes, meta = gnani_tts_adapter.synthesize(
        text=payload.text,
        language=payload.language,
        speed=payload.speed
    )
    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers={
            "X-Is-Mock": str(meta.get("is_mock", False)),
            "X-Voice": str(meta.get("voice", "")),
            "X-Model": str(meta.get("model", ""))
        }
    )

@app.delete("/api/v1/documents/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(
    document_id: str,
    authorization: Optional[str] = Header(None),
    x_session_token: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    actor_id = get_current_actor_id(db, authorization, x_session_token)
    doc = verify_document_ownership(db, document_id, actor_id)
    
    delete_document_cascade(db, doc.document_id)
    return {
        "success": True,
        "document_id": document_id,
        "state": "DELETED",
        "message": "Document and all associated derived data deleted permanently."
    }
