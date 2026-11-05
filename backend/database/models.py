import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON, Enum
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String(36), primary_key=True, default=generate_uuid)
    locale = Column(String(10), default="te-IN")
    accessibility_preferences = Column(JSON, default=dict)
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=get_utc_now)

class GuestSession(Base):
    __tablename__ = "guest_sessions"
    
    session_id = Column(String(36), primary_key=True, default=generate_uuid)
    token = Column(String(64), unique=True, nullable=False, index=True)
    consent_version = Column(String(20), default="v1.0")
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=get_utc_now)
    expires_at = Column(DateTime, nullable=False)

class ConsentRecord(Base):
    __tablename__ = "consent_records"
    
    consent_id = Column(String(36), primary_key=True, default=generate_uuid)
    actor_id = Column(String(36), nullable=False, index=True)
    purpose = Column(String(100), nullable=False)
    policy_version = Column(String(20), default="v1.0")
    granted_at = Column(DateTime, default=get_utc_now)
    withdrawn_at = Column(DateTime, nullable=True)

class Document(Base):
    __tablename__ = "documents"
    
    document_id = Column(String(36), primary_key=True, default=generate_uuid)
    owner_id = Column(String(36), nullable=False, index=True)
    storage_key = Column(String(255), nullable=False)
    checksum = Column(String(64), nullable=False)
    original_filename = Column(String(255), nullable=False)
    media_type = Column(String(50), nullable=False)
    state = Column(String(30), default="UPLOAD_PENDING", index=True)
    page_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now)
    retention_policy = Column(String(50), default="auto_delete_48h")
    deleted_at = Column(DateTime, nullable=True)
    
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    text_blocks = relationship("TextBlock", back_populates="document", cascade="all, delete-orphan")
    facts = relationship("ExtractedFact", back_populates="document", cascade="all, delete-orphan")
    cards = relationship("ActionCard", back_populates="document", cascade="all, delete-orphan")
    jobs = relationship("ProcessingJob", back_populates="document", cascade="all, delete-orphan")

class DocumentPage(Base):
    __tablename__ = "document_pages"
    
    page_id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    page_index = Column(Integer, nullable=False)
    derived_image_key = Column(String(255), nullable=True)
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    quality_state = Column(String(30), default="READABLE")  # READABLE, BLURRED, CROPPED, LOW_RES
    quality_metrics = Column(JSON, default=dict)
    
    document = relationship("Document", back_populates="pages")
    blocks = relationship("TextBlock", back_populates="page", cascade="all, delete-orphan")

class TextBlock(Base):
    __tablename__ = "text_blocks"
    
    block_id = Column(String(36), primary_key=True, default=generate_uuid)
    page_id = Column(String(36), ForeignKey("document_pages.page_id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, default=1)
    document_id = Column(String(36), ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    text_original = Column(Text, nullable=False)
    text_normalized = Column(Text, nullable=False)
    bbox = Column(JSON, nullable=True)  # [x1, y1, x2, y2]
    confidence = Column(Float, default=1.0)
    extraction_version = Column(String(50), default="pdf_native_v1")
    
    page = relationship("DocumentPage", back_populates="blocks")
    document = relationship("Document", back_populates="text_blocks")

class ExtractedFact(Base):
    __tablename__ = "extracted_facts"
    
    fact_id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    field_type = Column(String(50), nullable=False)  # date, amount, party, case_number, statutory_provision, required_action
    raw_value = Column(String(255), nullable=False)
    normalized_value = Column(String(255), nullable=False)
    status = Column(String(30), default="supported")  # supported, uncertain, unsupported
    reason_code = Column(String(50), nullable=True)
    evidence_refs = Column(JSON, default=list)  # [{"page_id": ..., "block_id": ...}]
    verifier_version = Column(String(50), default="v1.0")
    created_at = Column(DateTime, default=get_utc_now)
    
    document = relationship("Document", back_populates="facts")

class ActionCard(Base):
    __tablename__ = "action_cards"
    
    card_id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    what_says = Column(Text, nullable=False)
    what_means = Column(Text, nullable=False)
    what_action = Column(Text, nullable=False)
    uncertainty = Column(Text, nullable=True)
    proof_refs = Column(JSON, default=list)  # list of evidence objects
    status = Column(String(30), default="supported")
    created_at = Column(DateTime, default=get_utc_now)
    
    document = relationship("Document", back_populates="cards")

class Question(Base):
    __tablename__ = "questions"
    
    question_id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(String(36), nullable=False)
    input_type = Column(String(20), default="typed")  # typed, voice, preset
    text = Column(Text, nullable=False)
    transcript_status = Column(String(30), default="confirmed")
    language = Column(String(10), default="te-IN")
    created_at = Column(DateTime, default=get_utc_now)

class Answer(Base):
    __tablename__ = "answers"
    
    answer_id = Column(String(36), primary_key=True, default=generate_uuid)
    question_id = Column(String(36), ForeignKey("questions.question_id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(String(36), ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    response_language = Column(String(10), default="te-IN")
    summary_text = Column(Text, nullable=False)
    answer_status = Column(String(30), default="supported")  # supported, partial_uncertain, unsupported
    model_version = Column(String(50), default="rule_evidence_v1")
    prompt_version = Column(String(50), default="v1.0")
    created_at = Column(DateTime, default=get_utc_now)
    
    claims = relationship("Claim", back_populates="answer", cascade="all, delete-orphan")

class Claim(Base):
    __tablename__ = "claims"
    
    claim_id = Column(String(36), primary_key=True, default=generate_uuid)
    answer_id = Column(String(36), ForeignKey("answers.answer_id", ondelete="CASCADE"), nullable=False, index=True)
    claim_text = Column(Text, nullable=False)
    status = Column(String(30), default="supported")  # supported, uncertain, unsupported
    reason_code = Column(String(50), nullable=True)
    
    answer = relationship("Answer", back_populates="claims")
    evidence = relationship("ClaimEvidence", back_populates="claim", cascade="all, delete-orphan")

class ClaimEvidence(Base):
    __tablename__ = "claim_evidence"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    claim_id = Column(String(36), ForeignKey("claims.claim_id", ondelete="CASCADE"), nullable=False, index=True)
    block_id = Column(String(36), nullable=False)
    relation_type = Column(String(50), default="direct_citation")
    verifier_result = Column(String(50), default="verified_supported")
    
    claim = relationship("Claim", back_populates="evidence")

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    
    job_id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    job_type = Column(String(50), default="DOCUMENT_INGEST")
    state = Column(String(30), default="QUEUED", index=True)  # QUEUED, PROCESSING, READY, NEEDS_RECAPTURE, FAILED_RETRYABLE, FAILED_FINAL
    attempt_count = Column(Integer, default=0)
    next_attempt_at = Column(DateTime, nullable=True)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    
    document = relationship("Document", back_populates="jobs")

class AudioAsset(Base):
    __tablename__ = "audio_assets"
    
    audio_id = Column(String(36), primary_key=True, default=generate_uuid)
    owner_id = Column(String(36), nullable=False, index=True)
    source_answer_id = Column(String(36), nullable=False)
    object_key = Column(String(255), nullable=False)
    language = Column(String(10), default="te-IN")
    duration_seconds = Column(Float, default=0.0)
    expires_at = Column(DateTime, nullable=False)
    status = Column(String(30), default="ready")

class UserCorrection(Base):
    __tablename__ = "user_corrections"
    
    correction_id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), nullable=False, index=True)
    field_id = Column(String(36), nullable=False)
    field_type = Column(String(50), nullable=False)
    prior_value = Column(String(255), nullable=False)
    corrected_value = Column(String(255), nullable=False)
    actor_id = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=get_utc_now)

class AuditEvent(Base):
    __tablename__ = "audit_events"
    
    event_id = Column(String(36), primary_key=True, default=generate_uuid)
    actor_id = Column(String(36), nullable=False, index=True)
    document_id = Column(String(36), nullable=True, index=True)
    action = Column(String(50), nullable=False)
    request_id = Column(String(64), nullable=True)
    metadata_json = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=get_utc_now)

class FeedbackEvent(Base):
    __tablename__ = "feedback_events"
    
    feedback_id = Column(String(36), primary_key=True, default=generate_uuid)
    answer_id = Column(String(36), nullable=False, index=True)
    document_id = Column(String(36), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    user_comment = Column(Text, nullable=True)
    review_state = Column(String(30), default="pending")
    created_at = Column(DateTime, default=get_utc_now)
