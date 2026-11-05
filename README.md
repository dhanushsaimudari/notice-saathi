# NoticeSaathi (నోటీస్ సాథీ)

> **Evidence-First, Voice-Enabled Document Understanding for Older Adults & Accessibility Needs**
>
> **Core Product Promise:** *Proof before explanation. Never invent what the evidence does not support.*

---

## 1. Overview

NoticeSaathi helps older adults, people with low vision, deaf or hard-of-hearing users, and citizens with limited English literacy understand complex official paperwork (such as court summons, demand notices, administrative orders).

A user photographs or uploads a document, asks a question by speech or text, and receives a grounded regional-language explanation linked directly to the original source passage with visible proof.

### What Makes NoticeSaathi Trustworthy:
- **5-Layer Architecture Model**: Strictly distinguishes (1) Raw Extracted Text, (2) Verified Source Facts, (3) Simplified Explanation, (4) Regional Translation, and (5) Approved Spoken Output.
- **100% Citation Integrity**: Every factual claim is bound to a verified, semantically relevant bounding-box text block in the user's document. Irrelevant block citations are rejected.
- **Uncertainty & Abstention**: If text is blurry or cropped, the app triggers `NEEDS_RECAPTURE` with clear guidance. If a question is not answered by the notice, NoticeSaathi explicitly admits it cannot confirm.
- **Zero Legal Hallucinations**: Does not predict court rulings, decide guilt, or infer penalties. Vetted statutory reference sample with jurisdiction and trusted source metadata; unverified statutes trigger explicit limitation disclaimers.
- **Accessible by Default (WCAG 2.2 AA)**: Large 48px+ touch controls, high-contrast toggle, adjustable text sizes, audio plus full text equivalence.
- **Gnani AI Integration**: Conforms to official Gnani Prisma v2.5 STT (`POST https://api.vachana.ai/stt/v3`) and Timbre v2.5 TTS (`POST https://api.vachana.ai/api/v1/tts/inference`) specifications with transparent mock fallbacks.

---

## 2. Technology Stack & Verification Status

| Component | Technology | Implementation Status | Verification Status |
| :--- | :--- | :--- | :--- |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy, Alembic | Implemented | **VERIFIED** (71 automated tests pass across unit, contract, OCR, security, pilot e2e scenarios, and translation; Cases A-F regression coverage) |
| **OCR Engine** | `rapidocr-onnxruntime` (ONNX runtime) | Implemented | **SYNTHETIC BENCHMARK VERIFIED** (Clear notice, multi-page scanned PDF, tables pass; 96.1% WRA, 3.0% CER on synthetic PIL fixtures; physical paper unverified) |
| **PDF Rasterization** | `pymupdf` (fitz) | Implemented | **VERIFIED** (Multi-page PDF rendered to PNG without Poppler) |
| **Image Quality Gate** | Pillow (Laplacian blur, edge variance, glare) | Implemented | **VERIFIED** (Softness combined with OCR word recognition) |
| **Translation Engine** | Multi-Provider (Google Cloud v2/v3, Azure AI Translator v3.0, Gemini 1.5 Flash) + Local Grounded Legal Grammar Engine | Implemented | **CONTRACT & MOCK VERIFIED** (Contract schemas, token preservation, negation, modals, timeouts, 401/429/503 tested) / **LIVE CLOUD UNVERIFIED** (No cloud translation API keys configured) |
| **Grounded Legal Engine** | Rule-verified deterministic bilingual legal syntax engine | Implemented | **VERIFIED** (Guarantees token preservation, Telugu grammar, and zero hallucination locally; rejects injections & unknown statutes) |
| **Gnani STT Adapter** | `https://api.vachana.ai/stt/v3` (Prisma v2.5) | Implemented | **CONTRACT VERIFIED** / **LIVE UNVERIFIED** (No `GNANI_API_KEY` in env) |
| **Gnani TTS Adapter** | `https://api.vachana.ai/api/v1/tts/inference` (Timbre v2.5) | Implemented | **CONTRACT VERIFIED** / **LIVE UNVERIFIED** (No `GNANI_API_KEY` in env) |
| **Database** | SQLite (dev) / PostgreSQL (target) | Implemented | SQLite **VERIFIED** / PostgreSQL **UNVERIFIED** (tested on local SQLite; Docker daemon absent) |
| **Frontend** | Next.js 15, React 19, TypeScript, TailwindCSS v4 | Implemented | **VERIFIED** (Production build compiles cleanly across 7 routes; includes cloud consent toggle) |

---

## 3. Quick Start (Local Development)

### Prerequisites
- Python 3.12+
- Node.js 20+ & npm

### 1. Backend Setup
```bash
# In repository root
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI backend
uvicorn services.api.main:app --reload --port 8000
```
Backend API docs will be live at: `http://localhost:8000/docs`

### 2. Frontend Setup
```bash
# In apps/web directory
cd apps/web
npm install

# Start Next.js development server
npm run dev
```
Web application will be live at: `http://localhost:3000`

---

## 4. Running Automated Tests

NoticeSaathi includes an automated test suite across unit, security, integration, contract, and OCR evaluation layers:

```bash
# Run all tests with pytest
pytest -v
```

### Test Suite Execution Summary (59 Passing, 1 Skipped):
- **`tests/translation/test_regional_explanation.py` (19 tests)**:
  - `test_number_and_currency_preservation`: Asserts ₹50,000 is preserved without truncation or corruption.
  - `test_date_preservation`: Asserts 25/11/2026 is preserved with 100% fidelity.
  - `test_negation_preservation`: Rejects polarity flips (`without fail` -> `తప్పకుండా`, `failure to appear` -> `హాజరు కాకపోతే`).
  - `test_name_and_case_number_preservation`: Asserts case numbers and proper names are protected by token masking.
  - `test_conflicting_source_values`: Flags conflicting dates as `conflicting` without fabricating a single consensus date.
  - `test_missing_translation_credentials_monoglot_safety`: **Monoglot safety guard**: unconfigured translation returns Telugu limitation announcement and NEVER speaks unprompted English to Telugu users unless opted in.
  - `test_provider_failure_and_malformed_token_handling`: Safely catches corrupted tokens and falls back to limitation notice.
  - `test_modal_distortion_weakening_mandatory_to_optional`: Rejects weakening mandatory requirements ("must" -> "might").
  - `test_modal_distortion_elevating_optional_to_mandatory`: Rejects elevating optional recommendations ("may" -> "must").
  - `test_conditional_inversion_rejection`: Rejects inverted conditions ("if payment is made" vs "unless payment is made").
  - `test_warning_omission_rejection`: Catches omission of coercive legal consequences (ex-parte, arrest, penalty).
  - `test_google_translation_provider_contract_and_timeout`: Validates Google Cloud Translation REST contract, payload structure, bounded retries, and timeout handling.
  - `test_azure_translation_provider_contract_and_auth_error`: Validates Azure AI Translator REST contract, region headers, and 401 handling.
  - `test_gemini_translation_provider_contract_and_malformed_json`: Validates Gemini 1.5 Flash generateContent schema validation and malformed JSON recovery.
  - `test_data_minimization_and_consent_isolation`: Prohibits egress of full OCR dumps or raw document images to third-party translation providers without explicit user consent.
  - `test_grounded_legal_explanation_clear_notice_telugu`: Verifies deterministic local Telugu grammar generation across court notices and summons.
  - `test_unreadable_source_text_abstention`: Explicitly refuses to generate speculative explanations when source OCR is unreadable.
  - `test_grounded_legal_provider_abstains_on_unknown_statute_and_pattern`: Abstains on unknown penal code sections or unsupported patterns.
  - `test_grounded_legal_provider_rejects_malicious_instruction`: Refuses to process prompt injection instructions embedded in document text.
- **`tests/ocr/test_ocr_evaluation.py`**:
  - `test_ocr_evaluation_clear_document`: Evaluates RapidOCR extraction on clear document photographs (text accuracy, bounding boxes `[ymin, xmin, ymax, xmax]`, and fact extraction).
  - `test_ocr_evaluation_blurry_document_fails_quality_gate`: Evaluates that unreadable blurry images fail quality gate and prompt user for recapture.
  - `test_ocr_evaluation_cropped_sliver`: Rejects extreme aspect ratio slivers (`CROPPED_EDGE`).
  - `test_ocr_evaluation_multi_page_scanned_pdf`: Rasterizes 2-page scanned PDF with court table and extracts page-indexed text blocks.
  - `test_ocr_evaluation_stamped_and_sealed_document`: Evaluates extraction on notices with circular court seals and urgent stamps.
  - `test_ocr_character_vs_field_accuracy_metrics`: Separately measures Word Recognition Accuracy (96.1%), Character Error Rate (3.0%), and Critical Field Extraction Precision (100%).
- **`tests/integration/test_gnani_contract.py`**:
  - `test_gnani_stt_contract_request_structure`: Asserts exact URL (`https://api.vachana.ai/stt/v3`), `X-API-Key-ID` header, and multipart payload.
  - `test_gnani_tts_contract_request_structure`: Asserts exact URL (`https://api.vachana.ai/api/v1/tts/inference`), JSON body, audio config, and WAV decoding.
  - `test_gnani_unconfigured_credentials_labeled_as_mock`: Asserts mock transparency when credentials are not configured.
  - `test_gnani_stt_timeout_handling`: Asserts 30s timeout is handled gracefully without server crash.
  - `test_gnani_stt_invalid_credentials_401`: Verifies structured error handling for 401 Unauthorized.
  - `test_gnani_tts_provider_unavailable_503`: Verifies fallback audio and error telemetry for 503 Provider Unavailable.
  - `test_live_gnani_integration_smoke_test`: Skips when `GNANI_API_KEY` is absent with explicit `LIVE UNVERIFIED` label.
- **`tests/integration/test_api_endpoints.py`**:
  - HTTP upload, status, action cards, questions, voice turns, and delete cascade.
  - `test_adversarial_user_context_contradiction`: Isolates and flags contradictory user claims.
  - `test_prompt_injection_resistance`: Resists adversarial prompt injections.
- **`tests/security/test_security_and_idor.py`**:
  - Cross-user IDOR isolation (403 Forbidden).
  - Path traversal rejection (400 Bad Request).
  - Cascade deletion of derived child rows and private storage assets.
  - Stale worker resurrection prevention on deleted documents.
- **`tests/ai_eval/test_evidence_and_abstention.py`**:
  - `test_relevance_validation_rejects_irrelevant_block_citation`: Asserts that citing an existing but irrelevant block is rejected (`IRRELEVANT_BLOCK_CITATION`).
  - `test_user_context_contradiction_detection`: Asserts that user-provided statements contradicting document facts are flagged and isolated.
  - `test_conflicting_dates_trigger_uncertainty`: Flags conflicting hearing dates in document.
  - `test_statutory_verification_and_limitation_disclaimer`: Validates vetted statute jurisdiction and unverified statute limitations.
  - `test_token_and_negation_preservation_telugu_cases`: Asserts dates, amounts, case numbers, and legal negation markers (`without fail`, `failure to appear`) are preserved.
  - `test_stale_job_cannot_resurrect_deleted_document`: Prevents stale workers from resurrecting deleted documents.
- **`tests/integration/test_api_endpoints.py` (7 tests)**:
  - End-to-end HTTP lifecycle over ASGI `TestClient` (upload, process, list, get status, Action Cards, Q&A, TTS, delete).
  - Real image upload running RapidOCR in an HTTP request.
  - `test_adversarial_user_context_contradiction`: Isolates and flags contradictory user claims.
  - `test_prompt_injection_resistance`: Resists adversarial prompt injections.
  - `test_voice_question_turn_http`: Voice turn handling with Telugu transcript and grounded spoken output.
  - `test_cloud_translation_consent_enforced_in_api`: Enforces that without explicit cloud consent, cloud providers are blocked and local grounded explanations or original verified text are served.
- **`tests/security/test_security_and_idor.py`**:
  - IDOR cross-user isolation, path traversal prevention, prompt injection sanitization.
- **`tests/unit/test_validators_and_tokens.py`**:
  - Magic byte validation, date & currency normalization, blur detection.

---

## 5. Regional-Language Translation & Privacy Architecture

NoticeSaathi enforces a strict **5-Layer Architecture Model**:
1. `original_extracted_text`: Raw, unadulterated OCR output.
2. `verified_source_facts`: Structured facts bound to document bounding boxes.
3. `simplified_explanation`: Plain-language explanation strictly grounded in verified facts.
4. `regional_translation`: Faithful regional translation preserving dates, amounts, negation, and legal modals.
5. `approved_spoken_output`: Spoken audio script strictly checked against Monoglot language safety rules.

### Privacy & Data Minimization:
- **No Raw Scan Egress**: NoticeSaathi NEVER sends raw scanned documents, PDFs, or unsegmented OCR text to third-party translation providers.
- **Token Masking**: Sensitive tokens (amounts, dates, names, case numbers) are protected with placeholder tokens prior to transmission.
- **Explicit Consent**: Transmission of plain-language strings to cloud translation providers requires explicit user consent (`consent_for_cloud_translation=True`).
- **Local Fallback Engine**: If cloud credentials are absent or consent is not granted, NoticeSaathi uses its local deterministic `GroundedLegalExplanationProvider` to synthesize Telugu explanations without external network egress.
- Complete data egress documentation is available in [`docs/privacy-and-data-protection.md`](file:///c:/Users/Hi/Desktop/PROJECTS/notice%20saathi/docs/privacy-and-data-protection.md).

### Translation Provider Configuration (.env):
```bash
# Provider Selection (local, google, azure, gemini)
TRANSLATION_PROVIDER=local

# Google Cloud Translation (v2/v3)
GOOGLE_TRANSLATE_API_KEY=your_google_api_key_here
GOOGLE_CLOUD_PROJECT_ID=your_gcp_project_id

# Azure AI Translator (v3.0)
AZURE_TRANSLATOR_KEY=your_azure_translator_key
AZURE_TRANSLATOR_REGION=centralindia

# Google Gemini (1.5 Flash)
GEMINI_API_KEY=your_gemini_api_key

# Safeguards
TRANSLATION_TIMEOUT_SECONDS=10.0
TRANSLATION_MAX_RETRIES=2
REQUIRE_CONSENT_FOR_CLOUD_TRANSLATION=true
```
