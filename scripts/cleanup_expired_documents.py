#!/usr/bin/env python3
"""
NoticeSaathi — Automated 48-Hour Data Retention & Cleanup Worker
Purges expired documents and associated derived assets (OCR blocks, action cards, audio cache)
in accordance with data minimization and DPDP Act requirements.
"""

import sys
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import settings
from backend.database.session import SessionLocal
from backend.database.models import Document
from backend.modules.documents.service import delete_document_cascade

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("RetentionWorker")

def purge_expired_documents(retention_hours: int = 48) -> int:
    """
    Finds all active documents older than the retention threshold and executes
    cascade deletion on both the database records and physical filesystem assets.
    """
    db = SessionLocal()
    purged_count = 0
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
        logger.info(f"Scanning for active documents created before {cutoff.isoformat()} (Retention: {retention_hours}h)...")
        
        expired_docs = db.query(Document).filter(
            Document.deleted_at.is_(None),
            Document.created_at < cutoff
        ).all()
        
        if not expired_docs:
            logger.info("No expired documents found. Database is clean.")
            return 0
            
        logger.info(f"Found {len(expired_docs)} expired document(s) to purge.")
        for doc in expired_docs:
            doc_id = doc.document_id
            logger.info(f"Purging expired document ID={doc_id} (Created: {doc.created_at})...")
            delete_document_cascade(db, doc_id)
            purged_count += 1
            
        logger.info(f"Retention purge complete. Total documents wiped: {purged_count}")
        return purged_count
    except Exception as e:
        logger.error(f"Retention worker encountered an error: {e}", exc_info=True)
        return purged_count
    finally:
        db.close()

if __name__ == "__main__":
    hours = settings.RETENTION_HOURS if hasattr(settings, "RETENTION_HOURS") else 48
    purge_expired_documents(retention_hours=hours)

