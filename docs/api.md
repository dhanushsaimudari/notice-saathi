# NoticeSaathi API Documentation

Base URL: `/api/v1`

All responses follow predictable schema formats and never expose raw stack traces, database keys, or third-party credentials.

---

## 1. Authentication & Session

### Create or Restore Guest Session
`POST /api/v1/auth/session`

- **Query Parameters**:
  - `token` (optional string): Existing session token to restore.
- **Response** (`200 OK`):
  ```json
  {
    "session_id": "9702f029-6c3c-4c4a-a9af-df84e4f8a82a",
    "token": "a1b2c3d4e5f6...",
    "status": "active"
  }
  ```

---

## 2. Document Management

### Upload Document
`POST /api/v1/documents`

- **Headers**:
  - `X-Session-Token`: Guest session token
- **Content-Type**: `multipart/form-data`
- **Body**:
  - `file`: Binary file (PDF, JPEG, or PNG, max 15MB)
- **Response** (`201 Created`):
  ```json
  {
    "document_id": "doc_8f91a2bc",
    "state": "READY",
    "original_filename": "notice_photo.jpg",
    "page_count": 1
  }
  ```

### List Documents
`GET /api/v1/documents`

- **Headers**: `X-Session-Token: <token>`
- **Response** (`200 OK`):
  ```json
  [
    {
      "document_id": "doc_8f91a2bc",
      "original_filename": "notice_photo.jpg",
      "state": "READY",
      "created_at": "2026-10-28T16:45:00Z",
      "page_count": 1
    }
  ]
  ```

### Get Document Status
`GET /api/v1/documents/{document_id}/status`

- **Response** (`200 OK`):
  ```json
  {
    "document_id": "doc_8f91a2bc",
    "state": "READY",
    "message": "Document is ready."
  }
  ```
- *Possible states*: `UPLOAD_PENDING`, `UPLOADED`, `PROCESSING`, `READY`, `NEEDS_RECAPTURE`, `FAILED_FINAL`, `DELETED`.

### Get Action Cards with Proof
`GET /api/v1/documents/{document_id}/action-cards`

- **Response** (`200 OK`):
  ```json
  {
    "document_id": "doc_8f91a2bc",
    "document_state": "READY",
    "cards": [
      {
        "card_id": "card_01",
        "title": "న్యాయస్థాన నోటీసు (కోర్టు నోటీసు)",
        "what_says": "Document mentions: Case CC/1042/2026. Date: 18/11/2026. Amount: ₹50,000.",
        "what_means": "This document is an official notice. It lists an important date (18/11/2026) and specifies an amount (₹50,000).",
        "what_action": "You are required to appear in person before this Court on 18/11/2026 at 10:30 AM.",
        "uncertainty": null,
        "proof_refs": [
          {
            "page_number": 1,
            "block_id": "tb_1_1_369",
            "bbox": [0.08, 0.08, 0.23, 0.92],
            "text": "IN THE COURT OF THE PRINCIPAL DISTRICT AND SESSIONS JUDGE..."
          }
        ],
        "status": "supported"
      }
    ]
  }
  ```

### Permanently Delete Document
`DELETE /api/v1/documents/{document_id}`

- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "document_id": "doc_8f91a2bc",
    "state": "DELETED",
    "message": "Document and all associated derived data deleted permanently."
  }
  ```

---

## 3. Question Answering & Speech

### Ask Question (Text / Context Cross-Check)
`POST /api/v1/documents/{document_id}/questions`

- **Body**:
  ```json
  {
    "question_text": "What date is mentioned?",
    "response_language": "te-IN"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "answer_status": "supported",
    "summary_text": "The date mentioned in the document is 18/11/2026.",
    "claims": [
      {
        "claim_id": "c1",
        "claim_text": "The date mentioned in the document is 18/11/2026.",
        "status": "supported",
        "evidence": [
          { "page_index": 1, "block_id": "tb_1_1_369", "text_snippet": "..." }
        ]
      }
    ],
    "uncertainties": []
  }
  ```

### Voice Question Turn (STT)
`POST /api/v1/documents/{document_id}/voice-turns`

- **Content-Type**: `multipart/form-data`
- **Body**:
  - `audio_file`: Audio recording (WAV/MP3/WebM)
  - `language_code`: `te-IN`, `hi-IN`, `en-IN`
- **Response** (`200 OK`):
  ```json
  {
    "stt": {
      "success": true,
      "transcript": "ఈ పత్రంలో ఉన్న తేదీ ఏమిటి?",
      "is_mock": false
    },
    "transcript": "ఈ పత్రంలో ఉన్న తేదీ ఏమిటి?",
    "answer": {
      "answer_status": "supported",
      "summary_text": "The date mentioned in the document is 18/11/2026."
    }
  }
  ```

### Synthesize Speech (TTS)
`POST /api/v1/speech/synthesize`

- **Body**:
  ```json
  {
    "text": "విచారణ తేదీ 18 నవంబర్ 2026 న నిర్ణయించబడింది.",
    "language": "te-IN",
    "speed": 1.0
  }
  ```
- **Response** (`200 OK`):
  - Content-Type: `audio/wav`
  - Body: Binary WAV audio data
  - Headers: `X-Is-Mock`, `X-Voice`, `X-Model`

---

## 4. Error Code Reference

| Code | HTTP Status | Meaning & User Action |
| :--- | :--- | :--- |
| `DOCUMENT_NEEDS_RECAPTURE` | 422 | The photo is blurred, overexposed, or cropped. Action: User prompted to take a sharper photo. |
| `UNSUPPORTED_FILE_TYPE` | 400 | File extension is not allowed. Only `.pdf`, `.jpg`, `.jpeg`, `.png` are accepted. |
| `INVALID_FILE_SIGNATURE` | 400 | File magic bytes do not match expected signature. Rejects disguised files. |
| `FILE_TOO_LARGE` | 413 | Uploaded file exceeds the 15 MB limit. |
| `DOCUMENT_NOT_FOUND` | 404 | Document does not exist or has been deleted. |
| `DOCUMENT_ACCESS_DENIED` | 403 | IDOR prevention. Current session does not own the requested document ID. |
| `PROMPT_INJECTION_DETECTED` | 422 | Adversarial instruction pattern identified in document or question text. |

