# NoticeSaathi — Automated 48-Hour Data Retention Architecture

## 1. Objective and Legal Basis
Under the Digital Personal Data Protection (DPDP) Act and core privacy engineering principles, personal notices, court summons, and tax documents must not linger indefinitely on application servers. NoticeSaathi implements an automated 48-hour data retention lifecycle that enforces strict data minimization.

---

## 2. Retention Lifecycle & Deletion Semantics

When a document exceeds the retention threshold (default: `RETENTION_HOURS=48`), the automated retention worker executes cascade purging:

### A. Physical Asset Destruction (Irreversible)
1. **Original Uploaded Files:** Removed from disk via `storage_service.delete_document_assets(doc.storage_key)` (`./data/storage/originals/`).
2. **Derived Page Images:** All processed, normalized PNG page renderings are unlinked (`./data/storage/pages/`).
3. **Audio Synthesis Cache:** Any cached TTS WAV files associated with the document are deleted (`./data/storage/audio/`).

### B. Child Database Records (Hard-Deleted)
The following relational entities are permanently deleted within an atomic database transaction:
- `ActionCard` records (`action_cards` table)
- `ExtractedFact` records (`extracted_facts` table)
- `TextBlock` records (`text_blocks` table with OCR texts and bounding boxes)
- `DocumentPage` records (`document_pages` table)
- `ProcessingJob` records (`processing_jobs` table)

### C. Parent Document Row (Soft-Deleted Audit Container)
- The root `Document` record has its `deleted_at` timestamp set to the current UTC time and `state` set to `"DELETED"`.
- **Zero personal identifiable information (PII) or text content is retained.**
- The soft-deleted container provides an immutable audit trail confirming when the user's data minimization obligation was satisfied, while ensuring all active queries (`deleted_at.is_(None)`) treat the document as nonexistent.
- Background ingestion workers strictly reject processing any document where `deleted_at is not None` or `state in ["DELETED", "DELETION_REQUESTED"]`.

---

## 3. Scheduler Implementation & Overlap Prevention

### A. Lockfile Concurrency Guard
To prevent race conditions and overlapping cleanup executions across multiple containers or scheduled ticks, `RetentionLock` acquires an exclusive lockfile (`.retention_cleanup.lock`) in the storage volume:
- If another worker is currently running, subsequent invocations immediately log a `LOCKED` warning and cleanly skip the cycle without conflicting.
- Stale locks older than 30 minutes are automatically reclaimed.

### B. Deployment via Docker Compose
In production deployments, the retention worker runs as an isolated support service (`retention-worker`) sharing the same database and storage volume:

```yaml
  retention-worker:
    build:
      context: ..
      dockerfile: infra/Dockerfile.api
    container_name: notice_saathi_retention
    command: python scripts/cleanup_expired_documents.py --daemon --interval-seconds 3600 --hours 48
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://saathi:saathipass@postgres:5432/noticesaathi
      - STORAGE_LOCAL_DIR=/app/data/storage
      - RETENTION_HOURS=48
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - storage_data:/app/data/storage
    depends_on:
      - postgres
    restart: unless-stopped
```

---

## 4. Operational Runbook

### A. Manual Execution (One-Shot)
To run a one-time cleanup pass:
```bash
python scripts/cleanup_expired_documents.py --hours 48
```

### B. Dry-Run Verification
To inspect which documents are due for purging without deleting any files or records:
```bash
python scripts/cleanup_expired_documents.py --dry-run --hours 48
```

### C. Daemon Mode (Continuous Background Service)
To run as a continuous background daemon (e.g., checking every hour):
```bash
python scripts/cleanup_expired_documents.py --daemon --interval-seconds 3600 --hours 48
```

### D. Disabling the Scheduler
- In Docker Compose: Remove or comment out the `retention-worker` service definition in `infra/docker-compose.yml`.
- In standalone environments: Terminate the background daemon process or remove the corresponding cron entry.

### E. Health & Error Visibility
- Summary metrics are logged with zero document contents or PII:
  ```text
  [INFO] RetentionScheduler: Retention cycle finished: 12 purged, 0 failed out of 12 scanned. Status: COMPLETED
  ```
- If a file deletion fails due to an OS/filesystem error, the failure is captured and reported as `PARTIAL_FAILURE` with a non-zero exit code, alerting infrastructure monitoring.

