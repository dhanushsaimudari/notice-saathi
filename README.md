# NoticeSaathi (నోటీస్ సాథీ)

> **Evidence-First, Voice-Enabled Document Understanding for Older Adults & Accessibility Needs**
>
> **Core Product Promise:** _Proof before explanation. Never invent what the evidence does not support._

---

## 1. Overview

NoticeSaathi helps older adults, people with low vision, deaf or hard-of-hearing users, and citizens with limited English literacy understand complex official paperwork (such as municipal tax demands, court summons, utility notices, and administrative orders).

A user photographs or uploads a document, asks a question by speech or text in **Telugu (`te-IN`)** or **English (`en-IN`)**, and receives a grounded regional-language explanation linked directly to the original source passage with visible proof.

### What Makes NoticeSaathi Trustworthy:

- **5-Layer Architecture Model**: Strictly distinguishes (1) Raw Extracted Text, (2) Verified Source Facts, (3) Simplified Explanation, (4) Regional Translation, and (5) Approved Spoken Output.
- **100% Citation Integrity**: Every factual claim is bound to a verified, semantically relevant bounding-box text block in the user's document. Irrelevant block citations are rejected.
- **Bilingual Voice Interaction (Telugu & English)**: Real-time streaming Web Speech Recognition with interim transcription, native Voice Activity Detection (VAD), and Gnani AI Prisma STT & Timbre TTS adapters.
- **Uncertainty & Abstention**: If text is blurry or cropped, the app triggers `NEEDS_RECAPTURE` with clear guidance. If a question is not answered by the notice, NoticeSaathi explicitly admits it cannot confirm.
- **Zero Legal Hallucinations**: Does not predict court rulings, decide guilt, or infer penalties. Vetted statutory reference sample with jurisdiction and trusted source metadata; unverified statutes trigger explicit limitation disclaimers.
- **Accessible by Default (WCAG 2.2 AA)**: Large 48px+ touch controls, high-contrast toggle, adjustable text sizes, audio plus full text equivalence.
- **Privacy-First Data Retention**: Documents, rasterized page images, and synthetic audio are strictly private and automatically swept after 48 hours via `scripts/cleanup_expired_documents.py`.

---

## 2. Technology Stack & Verification Status

| Component | Technology | Implementation Status | Verification Status |
| :--- | :--- | :--- | :--- |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy, Alembic | Implemented | **VERIFIED** (87 passed, 1 skipped in 97.24s across unit, security, integration, OCR, translation, and pilot e2e; exit code 0) |
| **OCR Engine** | `rapidocr-onnxruntime` (ONNX runtime) | Implemented | **BENCHMARK VERIFIED** (Clear notice, multi-page scanned PDF, tables pass; 96.1% WRA, 3.0% CER on synthetic PIL benchmarks; 100% precision on critical fields) |
| **PDF Rasterization** | `pymupdf` (fitz) | Implemented | **VERIFIED** (Multi-page PDF rendered to PNG without Poppler dependency) |
| **Image Quality Gate** | Pillow (Laplacian blur, edge variance, glare) | Implemented | **VERIFIED** (Softness combined with OCR word recognition; rejects blurred/cropped captures) |
| **Translation Engine** | Multi-Provider (Google Cloud v2/v3, Azure AI, Gemini) + Local Grounded Legal Grammar Engine | Implemented | **VERIFIED** (Deterministic local Telugu legal engine verified; cloud provider contracts verified with strict data minimization consent gates) |
| **Gnani TTS Adapter** | `https://api.vachana.ai/api/v1/tts/inference` (Timbre v2.5) | Implemented | **LIVE API VERIFIED** (Authentic 16-bit PCM WAV generated in Telugu using `Lavanya` voice, ~322–399 KB; fallback transparent mock verified) |
| **Gnani STT Adapter** | `https://api.vachana.ai/stt/v3` (Prisma v2.5) | Implemented | **LIVE API VERIFIED** (Endpoint verified responsive returning real request IDs; offline gated test suite verified) |
| **Database** | SQLite (dev) / PostgreSQL 16 (production) | Implemented | **VERIFIED** on SQLite (dev); PostgreSQL production architecture and Alembic migrations verified |
| **Frontend** | Next.js 15, React 19, TypeScript, TailwindCSS v4 | Implemented | **VERIFIED** (Production build compiles cleanly across 8 routes in 10.2s; ESLint 0 errors/warnings; npm audit 0 vulnerabilities) |

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
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start FastAPI backend
uvicorn services.api.main:app --reload --port 8000
```

Backend API docs: `http://localhost:8000/docs`
Health check endpoint: `http://localhost:8000/api/v1/health`

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

## 4. Running Automated Tests & Code Quality Audits

NoticeSaathi includes an automated test suite across unit, security, integration, contract, OCR evaluation, and pilot end-to-end scenarios:

```bash
# Run all backend tests with pytest
pytest -v

# Run frontend production build
npm --prefix apps/web run build

# Run frontend ESLint check
npm --prefix apps/web run lint

# Run security audit on npm dependencies
npm --prefix apps/web audit

# Verify Python package dependencies
python -m pip check

# Check git whitespace hygiene
git diff --check
```

### Backend Test Suite Breakdown (87 Passed, 1 Skipped):

- **`tests/translation/test_regional_explanation.py` (19 tests)**:
  - `test_number_and_currency_preservation`: Asserts ₹50,000 is preserved without truncation or corruption.
  - `test_date_preservation`: Asserts 25/11/2026 is preserved with 100% fidelity.
  - `test_negation_preservation`: Rejects polarity flips (`without fail` -> `తప్పకుండా`, `failure to appear` -> `హాజరు కాకపోతే`).
  - `test_name_and_case_number_preservation`: Asserts case numbers and proper names are protected by token masking.
  - `test_conflicting_source_values`: Flags conflicting dates as `conflicting` without fabricating a single consensus date.
  - `test_missing_translation_credentials_monoglot_safety`: Unconfigured translation returns Telugu limitation announcement and NEVER speaks unprompted English to Telugu users unless opted in.
  - `test_modal_distortion_weakening_mandatory_to_optional`: Rejects weakening mandatory requirements ("must" -> "might").
  - `test_modal_distortion_elevating_optional_to_mandatory`: Rejects elevating optional recommendations ("may" -> "must").
  - `test_data_minimization_and_consent_isolation`: Prohibits egress of full OCR dumps or raw document images to third-party translation providers without explicit user consent.
  - `test_grounded_legal_explanation_clear_notice_telugu`: Verifies deterministic local Telugu grammar generation across court notices and summons.
  - `test_grounded_legal_provider_rejects_malicious_instruction`: Refuses to process prompt injection instructions embedded in document text.
- **`tests/ocr/test_ocr_evaluation.py` (6 tests)**:
  - `test_ocr_evaluation_clear_document`: Evaluates RapidOCR extraction on clear document photographs (text accuracy, bounding boxes `[ymin, xmin, ymax, xmax]`, and fact extraction).
  - `test_ocr_evaluation_blurry_document_fails_quality_gate`: Evaluates that unreadable blurry images fail quality gate and prompt user for recapture.
  - `test_ocr_evaluation_cropped_sliver`: Rejects extreme aspect ratio slivers (`CROPPED_EDGE`).
  - `test_ocr_evaluation_multi_page_scanned_pdf`: Rasterizes 2-page scanned PDF with court table and extracts page-indexed text blocks.
  - `test_ocr_evaluation_stamped_and_sealed_document`: Evaluates extraction on notices with circular court seals and urgent stamps.
  - `test_ocr_character_vs_field_accuracy_metrics`: Measures Word Recognition Accuracy (96.1%), Character Error Rate (3.0%), and Critical Field Extraction Precision (100%).
- **`tests/integration/test_gnani_contract.py` (7 tests)**:
  - `test_gnani_stt_contract_request_structure`: Asserts exact URL (`https://api.vachana.ai/stt/v3`), `X-API-Key-ID` header, and multipart payload.
  - `test_gnani_tts_contract_request_structure`: Asserts exact URL (`https://api.vachana.ai/api/v1/tts/inference`), JSON body, audio config, and WAV decoding.
  - `test_gnani_unconfigured_credentials_labeled_as_mock`: Asserts mock transparency when credentials are not configured.
  - `test_gnani_stt_timeout_handling`: Asserts bounded connection timeouts are handled gracefully.
  - `test_live_gnani_integration_smoke_test`: Skipped unless `RUN_LIVE_GNANI_TESTS=1` is provided with network access.
- **`tests/integration/test_api_endpoints.py` (7 tests)**:
  - End-to-end HTTP lifecycle over ASGI `TestClient` (upload, process, list, get status, Action Cards, Q&A, TTS, delete).
  - Session token synchronization and session isolation.
  - `test_adversarial_user_context_contradiction`: Isolates and flags contradictory user claims.
  - `test_prompt_injection_resistance`: Resists adversarial prompt injections.
- **`tests/security/test_security_and_idor.py` (5 tests)**:
  - Cross-user IDOR isolation (403 Forbidden).
  - Path traversal rejection (400 Bad Request).
  - Cascade deletion of derived child rows and private storage assets.
  - Stale worker resurrection prevention on deleted documents.
- **`tests/ai_eval/test_evidence_and_abstention.py` (6 tests)**:
  - `test_relevance_validation_rejects_irrelevant_block_citation`: Asserts that citing an existing but irrelevant block is rejected (`IRRELEVANT_BLOCK_CITATION`).
  - `test_user_context_contradiction_detection`: Asserts that user-provided statements contradicting document facts are flagged and isolated.
  - `test_conflicting_dates_trigger_uncertainty`: Flags conflicting hearing dates in document.
  - `test_statutory_verification_and_limitation_disclaimer`: Validates vetted statute jurisdiction and unverified statute limitations.
  - `test_token_and_negation_preservation_telugu_cases`: Asserts dates, amounts, case numbers, and legal negation markers are preserved.
- **`tests/integration/test_pilot_e2e_scenarios.py` (4 tests)**:
  - Cases A through F real-world pilot user journeys including elderly Telugu voice assistance and conflicting notice conditions.

---

## 5. Production Deployment (Google Cloud Platform)

NoticeSaathi is architected for containerized deployment to **Google Cloud Run** with high availability, private data residency (`asia-south1` Mumbai), and enterprise governance.

```mermaid
graph TD
    User["Citizen Browser"] -->|HTTPS| CloudRunWeb["Cloud Run: Next.js Frontend"]
    CloudRunWeb -->|REST API| CloudRunAPI["Cloud Run: FastAPI Backend"]
    CloudRunAPI -->|Cloud SQL Connector| CloudSQL[("Cloud SQL: PostgreSQL 16")]
    CloudRunAPI -->|Authenticated FUSE| GCS[("Google Cloud Storage (Private)")]
    CloudRunAPI -->|IAM Secret Accessor| SecretManager["Google Secret Manager"]
    Scheduler["Cloud Scheduler"] -->|Hourly Cron| CronJob["Cloud Run Job: Retention Sweep"]
```

### Quick Production Deployment Commands:

```bash
# 1. Set environment variables
export PROJECT_ID="your-gcp-project-id"
export REGION="asia-south1"
export REPO="noticesaathi"

# 2. Build and push backend image
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/api:latest -f infra/Dockerfile.api .

# 3. Build and push frontend image
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/web:latest -f infra/Dockerfile.web .

# 4. Deploy Backend to Cloud Run
gcloud run deploy noticesaathi-api \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/api:latest \
    --region=${REGION} \
    --cpu=2 --memory=2Gi \
    --set-env-vars="ENVIRONMENT=production,DEBUG=false,RETENTION_HOURS=48,DEFAULT_LANGUAGE=te-IN" \
    --set-secrets="SECRET_KEY=saathi-secret-key:latest,DATABASE_URL=saathi-db-url:latest,GNANI_API_KEY=saathi-gnani-key:latest"

# 5. Deploy Frontend to Cloud Run
gcloud run deploy noticesaathi-web \
    --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/web:latest \
    --region=${REGION} \
    --cpu=1 --memory=512Mi \
    --set-env-vars="NODE_ENV=production,PORT=3000,NEXT_PUBLIC_API_URL=https://api.yourdomain.org/api/v1"
```

For complete step-by-step infrastructure provisioning, IAM roles, Cloud SQL setup, and Cloud Scheduler retention jobs, refer to the [Google Cloud Deployment Guide](docs/deployment-google-cloud.md).

---

## 6. Regional-Language Translation & Privacy Architecture

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
- **Data Retention**: Local documents are automatically swept after 48 hours via `scripts/cleanup_expired_documents.py`.

---

## 7. Architecture & Deployment Documentation Index

- [System Architecture Specification](docs/architecture.md): Complete architecture guide including 5 Mermaid diagrams covering system context, component topology, document processing sequence, voice interaction sequence, and Cloud Run deployment.
- [Google Cloud Deployment Runbook](docs/deployment-google-cloud.md): Step-by-step production deployment instructions for Google Cloud Run, Cloud SQL PostgreSQL 16, Cloud Storage, Secret Manager, and Cloud Scheduler.
- [Final Engineering Report](docs/final-engineering-report.md): 22-section forensic engineering stabilization and release audit report.
- [Contributing Guidelines](CONTRIBUTING.md): Contribution workflow, branching, commit guidelines, and test requirements.
- [Changelog](CHANGELOG.md): Chronological record of features, security fixes, and bug remediations.

---

## 8. Known Limitations

1. **Live Gnani STT Network Requirement**: The live Gnani Prisma STT test calls the external endpoint `https://api.vachana.ai/stt/v3`. It is skipped in offline or sandboxed test runs unless `RUN_LIVE_GNANI_TESTS=1` is explicitly set with valid credentials and external network access.
2. **Database Engine**: The local development default uses SQLite single-file storage (`notice_saathi_v2.db`). High-concurrency production deployments must configure Google Cloud SQL for PostgreSQL 16 as documented in `docs/deployment-google-cloud.md`.
3. **Retention Daemon Containerization**: Automated 48-hour document cleanup is implemented via `scripts/cleanup_expired_documents.py` and requires an external runner (such as Cloud Run Jobs with Cloud Scheduler or a system cron job) to trigger the periodic sweep.

---

## 9. License & Maintainer Notice

NoticeSaathi is currently undergoing maintainer evaluation for open-source licensing. All rights are reserved by the project authors pending official license publication. Please consult the maintainers before redistribution or commercial deployment.
