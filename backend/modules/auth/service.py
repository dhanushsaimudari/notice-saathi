import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, Header, Request, status
from sqlalchemy.orm import Session
from backend.config import settings
from backend.database.models import GuestSession, User, Document, ConsentRecord

CONSENT_SCOPES: Dict[str, Dict[str, str]] = {
    "document_processing": {
        "title": "Notice Processing on NoticeSaathi Server",
        "description": "Uploads and processes your notice on the NoticeSaathi backend server for RapidOCR text recognition, entity verification, and legal safety analysis. Raw files are stored in private local server storage and deleted automatically within 48 hours or immediately upon deletion request.",
        "recipient": "NoticeSaathi Dedicated Server (Self-Hosted)",
        "data_sent": "Document file bytes (PDF / JPEG / PNG)"
    },
    "gnani_stt": {
        "title": "Voice Question to Gnani Prisma STT",
        "description": "Transmits microphone audio recordings via HTTPS to Gnani.ai Prisma STT (https://api.vachana.ai/stt/v3) for real-time speech transcription. Audio is processed for transcription only.",
        "recipient": "Gnani.ai (Third-Party Cloud STT Provider)",
        "data_sent": "Temporary microphone voice recording (WAV format)"
    },
    "gnani_tts": {
        "title": "Explanation Text to Gnani Timbre TTS",
        "description": "Transmits verified explanation text in Telugu/regional language via HTTPS to Gnani.ai Timbre TTS (https://api.vachana.ai/api/v1/tts/inference) to generate natural speech audio. No document images or user identity details are sent.",
        "recipient": "Gnani.ai (Third-Party Cloud TTS Provider)",
        "data_sent": "Verified regional-language explanation text only"
    },
    "external_translation": {
        "title": "Masked Plain Text to Cloud Translation Provider",
        "description": "Transmits a simplified, token-masked sentence (where names, amounts, dates, and case numbers are replaced with anonymous tokens like __DATE_0__) to Google Cloud Translation, Azure Translator, or Gemini. Never transmits raw notices.",
        "recipient": "Google Cloud Translation / Azure Translator / Gemini Cloud",
        "data_sent": "Token-masked plain-language sentence (no document files, no PII)"
    }
}

def record_consent(db: Session, actor_id: str, purpose: str, policy_version: str = "v1.0") -> ConsentRecord:
    """Records or activates explicit user consent for a specific processing scope."""
    now = datetime.now(timezone.utc)
    record = db.query(ConsentRecord).filter(
        ConsentRecord.actor_id == actor_id,
        ConsentRecord.purpose == purpose
    ).first()
    
    if record:
        record.withdrawn_at = None
        record.granted_at = now
        record.policy_version = policy_version
    else:
        record = ConsentRecord(
            actor_id=actor_id,
            purpose=purpose,
            policy_version=policy_version,
            granted_at=now,
            withdrawn_at=None
        )
        db.add(record)
        
    db.commit()
    db.refresh(record)
    return record

def revoke_consent(db: Session, actor_id: str, purpose: str) -> None:
    """Revokes consent for a processing scope, preventing future transmission."""
    now = datetime.now(timezone.utc)
    record = db.query(ConsentRecord).filter(
        ConsentRecord.actor_id == actor_id,
        ConsentRecord.purpose == purpose,
        ConsentRecord.withdrawn_at.is_(None)
    ).first()
    
    if record:
        record.withdrawn_at = now
        db.commit()

def has_consent(db: Session, actor_id: str, purpose: str) -> bool:
    """Checks whether active, unrevoked consent exists for the specified scope."""
    record = db.query(ConsentRecord).filter(
        ConsentRecord.actor_id == actor_id,
        ConsentRecord.purpose == purpose,
        ConsentRecord.withdrawn_at.is_(None)
    ).first()
    return record is not None

def get_actor_consents(db: Session, actor_id: str) -> Dict[str, Any]:
    """Returns the consent state and metadata for all supported processing scopes."""
    records = db.query(ConsentRecord).filter(
        ConsentRecord.actor_id == actor_id,
        ConsentRecord.withdrawn_at.is_(None)
    ).all()
    granted_purposes = {r.purpose: r.granted_at.isoformat() if r.granted_at else None for r in records}
    
    result = {}
    for scope_key, meta in CONSENT_SCOPES.items():
        is_granted = scope_key in granted_purposes
        result[scope_key] = {
            "scope": scope_key,
            "title": meta["title"],
            "description": meta["description"],
            "recipient": meta["recipient"],
            "data_sent": meta["data_sent"],
            "granted": is_granted,
            "granted_at": granted_purposes.get(scope_key)
        }
    return result

def get_or_create_guest_session(
    db: Session,
    token: str | None = None,
    default_consents: Optional[List[str]] = None
) -> GuestSession:
    now = datetime.now(timezone.utc)
    if token:
        session = db.query(GuestSession).filter(
            GuestSession.token == token,
            GuestSession.status == "active",
            GuestSession.expires_at > now
        ).first()
        if session:
            return session
            
    # Create new guest session
    new_token = secrets.token_hex(32)
    session = GuestSession(
        token=new_token,
        consent_version="v1.0",
        status="active",
        expires_at=now + timedelta(hours=settings.GUEST_SESSION_EXPIRE_HOURS)
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    
    # Initialize baseline consents if specified or default pilot baseline
    initial = default_consents if default_consents is not None else ["document_processing", "gnani_stt", "gnani_tts"]
    for p in initial:
        if p in CONSENT_SCOPES:
            record_consent(db, session.session_id, p)
            
    return session

def get_current_session(
    db: Session,
    authorization: str | None = None,
    x_session_token: str | None = None
) -> GuestSession:
    token = None
    if x_session_token:
        token = x_session_token
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        
    return get_or_create_guest_session(db, token)

def get_current_actor_id(
    db: Session,
    authorization: str | None = None,
    x_session_token: str | None = None
) -> str:
    session = get_current_session(db, authorization, x_session_token)
    return session.session_id

def verify_document_ownership(db: Session, document_id: str, actor_id: str) -> Document:
    doc = db.query(Document).filter(
        Document.document_id == document_id,
        Document.deleted_at.is_(None)
    ).first()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "DOCUMENT_NOT_FOUND",
                "message": "Document not found or has been deleted.",
                "recoverable": False
            }
        )
        
    if doc.owner_id != actor_id:
        # Prevent IDOR: uniform safe error response
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "DOCUMENT_ACCESS_DENIED",
                "message": "You do not have permission to view or access this document.",
                "recoverable": False
            }
        )
        
    return doc

