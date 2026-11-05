# NoticeSaathi — Voice & Multi-Channel Privacy, Consent & Retention Architecture

**Version:** 2.0 (Controlled Pilot Standard)  
**Date:** 2026-10-30  
**Compliance Framework:** Digital Personal Data Protection Act (DPDP Act, India, 2023) & Ethical AI Guidelines for Vulnerable Users  
**Core Privacy Mandate:** *Zero unconsented transmission. Proof before explanation. Never leak user documents or voice recordings.*

---

## 1. Executive Summary & Data Flow Audit

NoticeSaathi processes sensitive legal documents (such as court summons, cheque dishonour notices under Section 138 NI Act, demand notices, and administrative orders) for older adults and vulnerable citizens.

### Server-Side vs. On-Device Architecture Disclosure
> [!IMPORTANT]
> **Accurate Architecture Disclosure**: NoticeSaathi does **NOT** describe its backend operations as entirely "on-device". PDF rasterization, text recognition via RapidOCR, entity validation, and legal grammar synthesis execute on the **dedicated NoticeSaathi backend server**. Original document files and derived text blocks are stored in private local server storage (`./data/storage`) under restricted file permissions (POSIX `0600`).

---

## 2. Granular 4-Scope Consent Model

NoticeSaathi enforces four distinct processing scopes at the backend API layer. Consent is never bundled into a single opaque agreement:

| Consent Scope | User-Facing Scope Title | Data Transmitted | Receiving Entity & Endpoint | Purpose & Legal Justification | Fallback Alternative When Unconsented |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`document_processing`** | Notice Processing on NoticeSaathi Server | Raw document file bytes (PDF / JPEG / PNG) | NoticeSaathi Dedicated Server (`POST /api/v1/documents`) | RapidOCR text recognition, entity extraction (dates, amounts, case numbers), and legal safety analysis. | Request rejected with HTTP 403 (`CONSENT_REQUIRED_DOCUMENT_PROCESSING`). User is informed that server processing is required to analyze notices. |
| **`gnani_stt`** | Voice Question to Gnani Prisma STT | Temporary microphone audio recording (16-bit PCM WAV) | Gnani.ai Cloud (`POST https://api.vachana.ai/stt/v3`) | Speech-to-text transcription of spoken user questions in Telugu / Indian languages. | Audio recording is **NOT** transmitted. Rejected with HTTP 403 (`CONSENT_REQUIRED_GNANI_STT`). Full **text-based question input** is provided on screen. |
| **`gnani_tts`** | Explanation Text to Gnani Timbre TTS | Verified Telugu explanation text string only | Gnani.ai Cloud (`POST https://api.vachana.ai/api/v1/tts/inference`) | Natural voice synthesis (`Lavanya` timbre-v2.5) for older adults and low-vision users. | Text is **NOT** transmitted to external TTS. Rejected with HTTP 403 (`CONSENT_REQUIRED_GNANI_TTS`). Full explanation and source proof are displayed in **high-contrast text on screen**. |
| **`external_translation`** | Masked Text to Cloud Translation Provider | Token-masked plain text (e.g. `__CASE_0__ on __DATE_1__`) | Google Cloud Translation / Azure Translator / Gemini API | Multilingual translation for complex or non-standard notice formulations. | Cloud API call is **NOT** made. System uses the **local deterministic GroundedLegalExplanationProvider** or provides monoglot limitation notice. |

---

## 3. Backend Consent Enforcement Mechanisms

Backend enforcement does not rely solely on client-side checkboxes:
1. **Persistent Consent Records**: Every grant or revocation is recorded in the `consent_records` database table (`actor_id`, `purpose`, `policy_version`, `granted_at`, `withdrawn_at`).
2. **API Gatekeepers**:
   - `upload_document`: Checks `has_consent(db, actor_id, "document_processing")`.
   - `voice_question_turn`: Checks `has_consent(db, actor_id, "gnani_stt")`. If missing, the audio file is **immediately discarded from memory without invoking Gnani STT**.
   - `synthesize_speech`: Checks `has_consent(db, actor_id, "gnani_tts")`. If missing, no request is dispatched to Gnani Timbre TTS.
   - `ask_question`: Checks `has_consent(db, actor_id, "external_translation")`. If missing, external cloud translation is strictly bypassed.
3. **Revocation Support**: Users can revoke any consent scope at any time via `POST /api/v1/auth/consent` (`{"consents": {"gnani_stt": false}}`). Revocation is immediate and invalidates cached tokens.

---

## 4. Data Minimization & Token Masking Pipeline

When cloud translation is permitted with explicit user consent:
1. **Never Transmit Raw Notice Images or Scanned PDFs**: Document photographs and scans **never** leave the NoticeSaathi backend.
2. **Pre-Transmission Token Masking**:
   ```
   Original: "The accused shall appear in person on 18/11/2026 for CC No. 1042/2026 regarding cheque Rs. 50,000."
   Masked Sent: "The recipient must attend on __DATE_0__ regarding case __CASE_1__ for amount __CURR_2__."
   ```
3. **Post-Translation Token Restoration**: Tokens are validated and restored exactly, ensuring dates, amounts, and case identifiers cannot be hallucinated or modified in transit.

---

## 5. Retention & Deletion Schedule

| Asset Type | Storage Location | Retention Period | Automated Deletion Mechanism | Manual User Deletion |
| :--- | :--- | :--- | :--- | :--- |
| **Notice Files (PDF/Images)** | `./data/storage/{checksum}.bin` | 48 Hours | `scripts/cleanup_expired_documents.py` (Cron worker) | Immediate permanent unlink via `DELETE /api/v1/documents/{id}` |
| **OCR Blocks & Bounding Boxes** | `text_blocks` table | 48 Hours | Cascade database delete on parent document record | Immediate wipe via `delete_document_cascade()` |
| **Action Cards & Extracted Facts** | `action_cards`, `extracted_facts` | 48 Hours | Cascade database delete on parent document record | Immediate wipe via `delete_document_cascade()` |
| **Temporary Microphone Audio** | Memory buffer only | 0 Seconds (In-flight turn only) | Discarded immediately after transcription completes | Never persisted to disk |
| **Synthesized Speech Audio** | In-memory stream | 0 Seconds | Streamed directly to browser; never stored in permanent database | N/A |
| **User Guest Sessions** | `guest_sessions` table | 24 Hours | Session TTL expiration | Invalidate on browser close or token expiration |

---

## 6. Log Scrubbing & Telemetry Protection

All application logs pass through `scrub_sensitive_info()`:
- Authorization headers (`Bearer ***REDACTED***`).
- API keys (`X-API-Key-ID: ***REDACTED***`).
- Document text blocks and recipient names are excluded from access logs.
- System metrics record structured status codes (`201 Created`, `403 Forbidden`, `404 Not Found`, `503 Unavailable`), completely isolating user PII from monitoring sinks.

