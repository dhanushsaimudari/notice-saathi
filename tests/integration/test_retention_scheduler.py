import os
import shutil
import tempfile
import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

from backend.database.models import Base, Document, DocumentPage, TextBlock, ExtractedFact, ActionCard
from backend.modules.storage.service import StorageService
from backend.modules.documents.service import delete_document_cascade, process_document_pipeline
from scripts.cleanup_expired_documents import purge_expired_documents, RetentionLock

@pytest.fixture
def disposable_env():
    """
    Creates an isolated in-memory SQLite database and isolated temp storage directory.
    Zero interaction with development database or files.
    """
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    temp_dir = tempfile.mkdtemp(prefix="notice_saathi_retention_test_")
    storage = StorageService(base_dir=temp_dir)

    yield db, storage, Path(temp_dir)

    db.close()
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_retention_purges_expired_and_preserves_non_expired(disposable_env, monkeypatch):
    """
    1. Expired document assets and related database records are removed.
    2. Non-expired documents remain untouched.
    """
    db, storage, temp_path = disposable_env
    monkeypatch.setattr("backend.modules.documents.service.storage_service", storage)

    now = datetime.now(timezone.utc)
    old_time = now - timedelta(hours=50)   # Expired (>48h)
    fresh_time = now - timedelta(hours=10) # Fresh (<48h)

    # 1. Setup Expired Document with physical assets and child records
    doc_expired = Document(
        document_id="doc_expired_01",
        owner_id="user_exp",
        storage_key="expired_doc.pdf",
        checksum="chk_exp",
        original_filename="expired.pdf",
        media_type="application/pdf",
        state="READY",
        created_at=old_time
    )
    p_exp = DocumentPage(page_id="p_exp_1", document_id="doc_expired_01", page_index=1, derived_image_key="exp_page_1.png")
    tb_exp = TextBlock(block_id="tb_exp_1", document_id="doc_expired_01", page_id="p_exp_1", page_number=1, text_original="Court order 2026", text_normalized="court order 2026")
    fact_exp = ExtractedFact(fact_id="f_exp_1", document_id="doc_expired_01", field_type="amount", raw_value="5000", normalized_value="5000")
    card_exp = ActionCard(card_id="c_exp_1", document_id="doc_expired_01", title="Notice", what_says="Says text", what_means="Means", what_action="Action")

    # Create physical files on disk
    storage.save_original("expired_doc.pdf", b"%PDF-1.4 mock content")
    storage.save_page_image("exp_page_1.png", b"mock image content")

    # 2. Setup Non-Expired (Fresh) Document
    doc_fresh = Document(
        document_id="doc_fresh_01",
        owner_id="user_fresh",
        storage_key="fresh_doc.pdf",
        checksum="chk_fresh",
        original_filename="fresh.pdf",
        media_type="application/pdf",
        state="READY",
        created_at=fresh_time
    )
    p_fresh = DocumentPage(page_id="p_fresh_1", document_id="doc_fresh_01", page_index=1, derived_image_key="fresh_page_1.png")
    storage.save_original("fresh_doc.pdf", b"%PDF-1.4 fresh content")
    storage.save_page_image("fresh_page_1.png", b"mock fresh image")

    db.add_all([doc_expired, p_exp, tb_exp, fact_exp, card_exp, doc_fresh, p_fresh])
    db.commit()

    # Verify physical files exist before cleanup
    assert (temp_path / "originals" / "expired_doc.pdf").exists()
    assert (temp_path / "pages" / "exp_page_1.png").exists()
    assert (temp_path / "originals" / "fresh_doc.pdf").exists()
    assert (temp_path / "pages" / "fresh_page_1.png").exists()

    # Execute retention cleanup with 48h threshold
    res = purge_expired_documents(
        retention_hours=48,
        db_session=db,
        lock_dir=temp_path
    )

    assert res["status"] == "COMPLETED"
    assert res["scanned"] == 1
    assert res["purged"] == 1
    assert res["failed"] == 0

    # 1. Expired document physical files MUST be deleted
    assert not (temp_path / "originals" / "expired_doc.pdf").exists()
    assert not (temp_path / "pages" / "exp_page_1.png").exists()

    # Child rows MUST be physically deleted
    assert db.query(DocumentPage).filter(DocumentPage.document_id == "doc_expired_01").count() == 0
    assert db.query(TextBlock).filter(TextBlock.document_id == "doc_expired_01").count() == 0
    assert db.query(ExtractedFact).filter(ExtractedFact.document_id == "doc_expired_01").count() == 0
    assert db.query(ActionCard).filter(ActionCard.document_id == "doc_expired_01").count() == 0

    # Parent Document row is soft-deleted for DPDP compliance audit log
    doc_exp_db = db.query(Document).filter(Document.document_id == "doc_expired_01").first()
    assert doc_exp_db.deleted_at is not None
    assert doc_exp_db.state == "DELETED"

    # 2. Non-expired document MUST remain untouched
    assert (temp_path / "originals" / "fresh_doc.pdf").exists()
    assert (temp_path / "pages" / "fresh_page_1.png").exists()
    doc_fresh_db = db.query(Document).filter(Document.document_id == "doc_fresh_01").first()
    assert doc_fresh_db.deleted_at is None
    assert doc_fresh_db.state == "READY"
    assert db.query(DocumentPage).filter(DocumentPage.document_id == "doc_fresh_01").count() == 1

def test_deleted_document_not_reprocessed_by_workers(disposable_env, monkeypatch):
    """
    Verifies that a document with state='DELETED' or deleted_at set cannot be reprocessed.
    """
    db, storage, temp_path = disposable_env
    monkeypatch.setattr("backend.modules.documents.service.storage_service", storage)

    doc = Document(
        document_id="doc_deleted_test",
        owner_id="u1",
        storage_key="test.pdf",
        checksum="chk",
        original_filename="test.pdf",
        media_type="application/pdf",
        state="DELETED",
        deleted_at=datetime.now(timezone.utc)
    )
    db.add(doc)
    db.commit()

    with pytest.raises(HTTPException) as exc:
        process_document_pipeline(db, "doc_deleted_test")
    assert exc.value.status_code == 400
    assert "Cannot process document marked for deletion" in exc.value.detail

def test_failed_file_deletion_is_surfaced_rather_than_silently_reported(disposable_env, monkeypatch):
    """
    Verifies that if physical file deletion fails (e.g. disk/permission error),
    the failure is captured, logged, and surfaced in the retention summary metrics
    rather than falsely reported as clean.
    """
    db, storage, temp_path = disposable_env
    monkeypatch.setattr("backend.modules.documents.service.storage_service", storage)

    old_time = datetime.now(timezone.utc) - timedelta(hours=72)
    doc = Document(
        document_id="doc_fail_file",
        owner_id="u1",
        storage_key="locked.pdf",
        checksum="c1",
        original_filename="locked.pdf",
        media_type="application/pdf",
        state="READY",
        created_at=old_time
    )
    db.add(doc)
    db.commit()

    storage.save_original("locked.pdf", b"data")

    # Mock unlink to raise PermissionError
    def mock_failing_delete(*args, **kwargs):
        raise IOError("OS PermissionError: Access Denied to locked file")

    monkeypatch.setattr(storage, "delete_document_assets", mock_failing_delete)

    res = purge_expired_documents(
        retention_hours=48,
        db_session=db,
        lock_dir=temp_path
    )

    # Must surface failure!
    assert res["status"] == "PARTIAL_FAILURE"
    assert res["failed"] == 1
    assert res["purged"] == 0

def test_prevent_overlapping_cleanup_runs(disposable_env):
    """
    Verifies that the retention lock prevents concurrent / overlapping runs.
    """
    db, storage, temp_path = disposable_env

    # 1. First lock acquired
    lock1 = RetentionLock(lock_dir=temp_path)
    assert lock1.acquire() is True

    # 2. Second overlapping attempt MUST be rejected
    lock2 = RetentionLock(lock_dir=temp_path)
    assert lock2.acquire() is False

    # 3. Running purge while lock held returns LOCKED status
    res = purge_expired_documents(db_session=db, lock_dir=temp_path)
    assert res["status"] == "LOCKED"

    # 4. Release lock allows subsequent runs
    lock1.release()
    assert lock2.acquire() is True
    lock2.release()
