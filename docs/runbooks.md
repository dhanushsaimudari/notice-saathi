# NoticeSaathi — Operational Runbooks

## 1. Gnani AI Outage or Rate Limiting

### Symptom
- STT or TTS API requests return HTTP 429 (Rate Limited), 500, or 503 from `https://api.vachana.ai`.
- Audio player displays "Audio temporarily unavailable".

### Immediate Operational Steps
1. **Verify Outage**:
   Check health via command line:
   ```bash
   curl -I https://api.vachana.ai/stt/v3 -H "X-API-Key-ID: $GNANI_API_KEY"
   ```
2. **Fallback Mode**:
   NoticeSaathi backend automatically falls back to transparent synthesized WAV responses with `X-Is-Mock: True` if the upstream provider is unavailable, ensuring the UI text and proof viewing never break.
3. **Notify Users**:
   The user interface displays: *"Audio is temporarily unavailable. The verified explanation remains available to read as text."*

---

## 2. Document Stuck in `PROCESSING`

### Symptom
- Document remains in `PROCESSING` state for more than 60 seconds.

### Resolution Procedure
1. Check background job status in database:
   ```sql
   SELECT job_id, document_id, state, attempt_count, error_message FROM processing_jobs WHERE state = 'PROCESSING';
   ```
2. If the worker process restarted or stalled, re-enqueue or set state to `FAILED_RETRYABLE`:
   ```sql
   UPDATE documents SET state = 'FAILED_RETRYABLE' WHERE state = 'PROCESSING' AND created_at < NOW() - INTERVAL '5 minutes';
   ```
3. The frontend displays an honest retry button rather than an endless spinner.

---

## 3. Data Deletion Verification & Compliance

### Verification Drill
1. User triggers deletion of a document via `DELETE /api/v1/documents/{document_id}`.
2. Verify cascade:
   - Physical file deleted from `data/storage/originals/<storage_key>`.
   - Derived page images deleted from `data/storage/pages/`.
   - Audio caches deleted from `data/storage/audio/`.
   - Database records deleted from `action_cards`, `extracted_facts`, `text_blocks`, and `document_pages`.
   - `Document.state` marked as `DELETED`.
3. Negative authorization check:
   Calling `GET /api/v1/documents/{document_id}` must return `404 DOCUMENT_NOT_FOUND`.

---

## 4. Compromised Credential or Secret Rotation

1. Immediately revoke the affected `GNANI_API_KEY` on `https://app.gnani.ai/voice`.
2. Generate a new API key.
3. Update environment configuration (`.env` or production secret manager).
4. Restart the API service:
   ```bash
   docker-compose restart api
   ```
5. Run test suite to verify connectivity:
   ```bash
   pytest tests/integration/test_gnani_adapters.py -v
   ```

