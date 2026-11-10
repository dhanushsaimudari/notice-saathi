#!/usr/bin/env python3
"""
NoticeSaathi — Automated 48-Hour Data Retention & Cleanup Worker & Scheduler
Purges expired documents and associated derived assets (OCR blocks, action cards, audio cache)
in accordance with data minimization and DPDP Act requirements.
"""

import sys
import os
import time
import signal
import logging
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

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
logger = logging.getLogger("RetentionScheduler")

LOCK_FILENAME = ".retention_cleanup.lock"

class RetentionLock:
    """
    Prevents overlapping cleanup executions across processes or scheduler ticks.
    """
    def __init__(self, lock_dir: Optional[Path] = None):
        self.lock_dir = lock_dir or Path(settings.STORAGE_LOCAL_DIR).resolve()
        self.lock_file = self.lock_dir / LOCK_FILENAME
        self._acquired = False

    def acquire(self) -> bool:
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        if self.lock_file.exists():
            # Check stale lock (older than 30 minutes)
            try:
                mtime = self.lock_file.stat().st_mtime
                if (time.time() - mtime) > 1800:
                    logger.warning("Found stale retention lock file (>30m old). Reclaiming lock.")
                    self.lock_file.unlink()
                else:
                    return False
            except Exception:
                return False

        try:
            with open(self.lock_file, "x") as f:
                f.write(f"PID: {os.getpid()} | Timestamp: {datetime.now(timezone.utc).isoformat()}\n")
            self._acquired = True
            return True
        except FileExistsError:
            return False
        except Exception as e:
            logger.error(f"Error creating lock file: {e}")
            return False

    def release(self) -> None:
        if self._acquired and self.lock_file.exists():
            try:
                self.lock_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to remove retention lock file: {e}")
            finally:
                self._acquired = False

    def __enter__(self):
        if not self.acquire():
            raise BlockingIOError("Overlapping execution prevented: Retention cleanup is already running.")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

def purge_expired_documents(
    retention_hours: int = 48,
    db_session: Optional[Session] = None,
    lock_dir: Optional[Path] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Finds all active documents older than the retention threshold and executes
    cascade deletion on both the database records and physical filesystem assets.

    Returns summary metrics:
      {"scanned": int, "purged": int, "failed": int, "status": "COMPLETED"|"LOCKED"|"ERROR"}
    """
    lock = RetentionLock(lock_dir=lock_dir)
    if not lock.acquire():
        logger.warning("Another retention cleanup run is currently active. Skipping cycle to prevent overlap.")
        return {"scanned": 0, "purged": 0, "failed": 0, "status": "LOCKED"}

    db = db_session if db_session is not None else SessionLocal()
    close_db_on_exit = db_session is None
    purged_count = 0
    failed_count = 0

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
        logger.info(f"Scanning for active documents created before {cutoff.isoformat()} (Retention: {retention_hours}h, DryRun: {dry_run})...")

        expired_docs = db.query(Document).filter(
            Document.deleted_at.is_(None),
            Document.created_at < cutoff
        ).all()

        scanned_count = len(expired_docs)
        if not expired_docs:
            logger.info("Retention scan complete: 0 expired documents found. Database is clean.")
            return {"scanned": 0, "purged": 0, "failed": 0, "status": "COMPLETED"}

        logger.info(f"Found {scanned_count} expired document(s) due for purge.")
        for doc in expired_docs:
            doc_id = doc.document_id
            if dry_run:
                logger.info(f"[DRY RUN] Would purge expired document ID={doc_id} (Created: {doc.created_at})")
                purged_count += 1
                continue

            logger.info(f"Purging expired document ID={doc_id} (Created: {doc.created_at})...")
            try:
                delete_document_cascade(db, doc_id)
                purged_count += 1
            except Exception as e:
                failed_count += 1
                logger.error(f"FAILURE: Could not complete purge for document ID={doc_id}: {e}", exc_info=False)

        status_str = "COMPLETED" if failed_count == 0 else "PARTIAL_FAILURE"
        logger.info(
            f"Retention cycle finished: {purged_count} purged, {failed_count} failed out of {scanned_count} scanned. Status: {status_str}"
        )
        return {"scanned": scanned_count, "purged": purged_count, "failed": failed_count, "status": status_str}

    except Exception as e:
        logger.error(f"Retention worker encountered an unexpected error: {e}", exc_info=True)
        return {"scanned": 0, "purged": purged_count, "failed": failed_count + 1, "status": "ERROR", "error": str(e)}
    finally:
        lock.release()
        if close_db_on_exit:
            db.close()

def run_retention_daemon(interval_seconds: int = 3600, retention_hours: int = 48) -> None:
    """
    Runs the retention worker on a recurring background schedule.
    """
    logger.info(f"NoticeSaathi Retention Scheduler started. Interval: {interval_seconds}s | Retention: {retention_hours}h")
    running = True

    def _handle_exit(signum, frame):
        nonlocal running
        logger.info("Received termination signal. Shutting down retention scheduler...")
        running = False

    try:
        signal.signal(signal.SIGINT, _handle_exit)
        signal.signal(signal.SIGTERM, _handle_exit)
    except Exception:
        pass

    while running:
        logger.info("Executing scheduled retention cleanup cycle...")
        result = purge_expired_documents(retention_hours=retention_hours)
        logger.info(f"Scheduled cycle completed: {result}")
        for _ in range(interval_seconds):
            if not running:
                break
            time.sleep(1)

    logger.info("Retention scheduler stopped cleanly.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NoticeSaathi Automated 48-Hour Retention Cleanup & Scheduler")
    parser.add_argument("--daemon", action="store_true", help="Run continuously as a scheduled daemon service")
    parser.add_argument("--interval-seconds", type=int, default=3600, help="Scheduler poll interval in seconds (default: 3600)")
    parser.add_argument("--hours", type=int, default=getattr(settings, "RETENTION_HOURS", 48), help="Retention threshold in hours (default: 48)")
    parser.add_argument("--dry-run", action="store_true", help="Scan and log expired documents without deleting")

    args = parser.parse_args()

    if args.daemon:
        run_retention_daemon(interval_seconds=args.interval_seconds, retention_hours=args.hours)
    else:
        res = purge_expired_documents(retention_hours=args.hours, dry_run=args.dry_run)
        sys.exit(0 if res.get("failed", 0) == 0 else 1)
