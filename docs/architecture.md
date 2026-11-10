# NoticeSaathi — Architectural Design & System Documentation

> **Core Product Promise: Proof before explanation. Never invent what the evidence does not support.**

---

## 1. System Mission & Philosophy

NoticeSaathi is an evidence-first, voice-enabled document comprehension companion engineered specifically for older adults, individuals with low vision, deaf or hard-of-hearing citizens, and people facing language or literacy barriers.

Unlike generic conversational AI assistants that extrapolate or hallucinate, NoticeSaathi enforces strict deterministic checks: every claim must resolve to verified bounding-box passages in the user's document, high-impact facts (dates, amounts, legal sections, directives) are validated individually, and the system abstains or marks information as uncertain when evidence is absent, ambiguous, or contradictory.

---

## 2. System Context Diagram

```mermaid
flowchart TD
    User["Citizen / Older Adult User"] -->|Uploads Notice (PDF / JPG / PNG)| WebApp["Next.js 15 Web Application\n(Port 3000 / Cloud Run)"]
    User -->|Voice / Text Questions in Telugu / English| WebApp

    subgraph TrustBoundary["NoticeSaathi Secure Processing Boundary"]
        WebApp -->|REST API Calls (X-Session-Token)| APIService["FastAPI Backend Service\n(Port 8000 / Cloud Run)"]
        APIService --> DB[(Database\nSQLite / PostgreSQL)]
        APIService --> Storage["Private Encrypted Storage\n(Local / Google Cloud Storage)"]
        APIService --> OCR["RapidOCR ONNX Engine\n(Local In-Memory Inference)"]
        APIService --> GroundedQA["Grounded Q&A Engine\n(Case F Conflict Logic & Citations)"]
    end

    subgraph ExternalGateways["External Services (Strict Affirmative Consent Required)"]
        APIService -->|Explicit Voice Consent| GnaniSTT["Gnani Prisma v2.5 STT\n(POST https://api.vachana.ai/stt/v3)"]
        APIService -->|Explicit Voice Consent| GnaniTTS["Gnani Timbre v2.5 TTS\n(POST https://api.vachana.ai/api/v1/tts/inference)"]
        APIService -->|Explicit Cloud Consent| CloudTranslate["Optional Cloud Translation\n(Google / Azure / Gemini)"]
    end

    APIService -->|Action Cards with Highlighted Proof| WebApp
    APIService -->|Synthesized Audio Stream .wav| WebApp
    WebApp -->|Audio Playback & WCAG 2.2 AA Visuals| User
```

---

## 3. Component Architecture Diagram

```mermaid
flowchart LR
    subgraph ClientLayer["Frontend Client Layer (Next.js 15 App Router)"]
        UI_Home["Home Page (/)"]
        UI_Upload["Upload Page (/upload)\nFile Picker & Live Camera"]
        UI_Doc["Document View (/documents/[id])\nAction Cards & Proof Highlight"]
        UI_Ask["Ask View (/documents/[id]/ask)\nSpoken & Typed Q&A"]
        UI_History["History View (/history)"]
        UI_Privacy["Privacy View (/privacy)"]
        A11yContext["Accessibility Provider\n(Font Scaling, High Contrast, WCAG 2.2)"]
        APIClient["API Client (`api.ts`)\nSession Sync, Bounded Retry, Polling"]
    end

    subgraph APILayer["API Gateway & Middleware Layer (FastAPI)"]
        MainApp["`services/api/main.py`\nFastAPI Routes & CORS"]
        AuthMiddleware["Session & Token Validator\n(`modules/auth/service.py`)"]
        ConsentGate["DPDP Purpose Consent Enforcement"]
        SafeErrors["Production Error Sanitizer\n(Zero Stack Traces in Prod)"]
    end

    subgraph ServiceLayer["Core Domain Services"]
        DocPipeline["Document Pipeline Service\n(`modules/documents/service.py`)"]
        OCREngine["RapidOCR ONNX Engine\n(`modules/ocr/service.py`)"]
        QualityGate["Quality Evaluator (Laplacian Blur/Glare)"]
        FactService["Entity Normalizer & Fact Extractor\n(`modules/extraction/fact_service.py`)"]
        CitationVal["Citation Validator\n(`modules/citations/validator.py`)"]
        AnswerEngine["Grounded Legal Answering Engine\n(`modules/answers/service.py`)"]
        GnaniSTT["Gnani STT Adapter (`modules/gnani_stt/adapter.py`)"]
        GnaniTTS["Gnani TTS Adapter (`modules/gnani_tts/adapter.py`)"]
    end

    subgraph PersistenceLayer["Storage & Data Layer"]
        SQLStore[(SQL Database\nDocuments, TextBlocks, Facts, ActionCards)]
        BlobStore["Private File Storage\n(Original Files, Rendered Slices, Audio Caches)"]
    end

    APIClient --> MainApp
    MainApp --> AuthMiddleware --> ConsentGate
    ConsentGate --> DocPipeline
    ConsentGate --> AnswerEngine

    DocPipeline --> QualityGate
    QualityGate --> OCREngine
    OCREngine --> FactService
    FactService --> CitationVal
    AnswerEngine --> CitationVal

    DocPipeline --> SQLStore
    DocPipeline --> BlobStore
    AnswerEngine --> SQLStore
    AnswerEngine --> GnaniSTT
    AnswerEngine --> GnaniTTS
```

---

## 4. Document Processing Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Citizen
    participant Web as Next.js Web App
    participant API as FastAPI Backend
    participant Auth as Auth & Consent Module
    participant DocSvc as Document Pipeline
    participant OCR as RapidOCR ONNX
    participant DB as SQL Database
    participant Store as Private Storage

    Citizen->>Web: Selects notice image or captures camera photo
    Web->>API: POST /api/v1/documents (file, consent_document_processing=true)
    API->>Auth: get_current_session(token)
    Auth-->>API: GuestSession (actor_id, token)
    API->>Auth: record_consent(actor_id, 'document_processing')

    API->>Store: Write original file bytes to private storage
    API->>DB: create_document_record(state='UPLOADED')

    API->>DocSvc: process_document_pipeline(document_id)
    DocSvc->>Store: Read file bytes & validate magic bytes
    DocSvc->>DocSvc: Assess image quality (blur & crop variance)

    alt Image is severely blurred or cropped
        DocSvc->>DB: Update state='NEEDS_RECAPTURE'
        DocSvc-->>API: Document (state='NEEDS_RECAPTURE')
        API-->>Web: 201 Created (state='NEEDS_RECAPTURE', session_token)
        Web-->>Citizen: Prompt to retake clearly with guidance
    else Image passes quality threshold
        DocSvc->>OCR: Extract text blocks and bounding boxes
        OCR-->>DocSvc: List of TextBlocks with coordinates [ymin, xmin, ymax, xmax]
        DocSvc->>DB: Persist TextBlocks
        DocSvc->>DocSvc: Extract candidate facts (amounts, dates, case numbers)
        DocSvc->>DocSvc: Generate grounded Action Cards with ProofRefs
        DocSvc->>DB: Persist ActionCards
        DocSvc->>DB: Update state='READY'
        DocSvc-->>API: Document (state='READY')
        API-->>Web: 201 Created (state='READY', headers: X-Session-Token)
        Web->>Web: Store active session_token in localStorage
        Web-->>Citizen: Navigate immediately to /documents/[id]
        Web-->>Citizen: Display Action Cards with clickable [Proof] citations
    end
```

---

## 5. Voice Interaction Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Citizen
    participant Web as Next.js Web App
    participant API as FastAPI Backend
    participant STT as Gnani Prisma STT
    participant QA as Grounded Q&A Service
    participant TTS as Gnani Timbre TTS
    participant DB as SQL Database

    Citizen->>Web: Taps 'Tap to Speak' and asks in Telugu: "విచారణ తేదీ ఎప్పుడు?"
    Web->>Web: Record audio/wav via browser MediaRecorder
    Web->>API: POST /api/v1/documents/[id]/voice-turns (audio_file, consent_gnani_stt=true)

    API->>DB: Check affirmative consent for Gnani STT
    API->>STT: POST https://api.vachana.ai/stt/v3 (question.wav, language_code='te-IN')
    STT-->>API: { success: true, transcript: "విచారణ తేదీ ఎప్పుడు?" }

    API->>QA: answer_user_question(document_id, transcript, language='te-IN')
    QA->>DB: Fetch verified document TextBlocks and ExtractedFacts
    QA->>QA: Check Case F conflict detection (opposing demands/waivers)
    QA->>QA: Match query intent against verified document facts

    alt Supported by document text
        QA-->>API: Answer (status='supported', summary_text, proof_refs)
    else Contradictory document instructions
        QA-->>API: Answer (status='conflicting', explains both directives)
    else Legal advice inquiry (e.g., 'Will I go to jail?')
        QA-->>API: Answer (status='unsupported', statutory limitation disclaimer)
    end

    API-->>Web: 200 OK (transcript, answer_result)
    Web-->>Citizen: Display answer text with supporting evidence proof

    alt User taps 'Listen to explanation'
        Web->>API: POST /api/v1/speech/synthesize (text, language='te-IN', consent_gnani_tts=true)
        API->>DB: Check affirmative consent for Gnani TTS
        API->>TTS: POST https://api.vachana.ai/api/v1/tts/inference (text, voice='Lavanya', model='timbre-v2.5')
        TTS-->>API: Binary audio/wav bytes
        API-->>Web: 200 OK (Content-Type: audio/wav)
        Web-->>Citizen: Audio plays smoothly with speed controls (0.85x, 1x, 1.15x)
    end
```

---

## 6. Google Cloud Run Deployment Architecture Diagram

```mermaid
flowchart TD
    subgraph Client["Citizen Endpoints"]
        Mobile["Mobile Smartphone Browser"]
        Desktop["Desktop / Laptop Browser"]
    end

    subgraph GCP["Google Cloud Platform Environment"]
        LB["Cloud Load Balancer / Custom Domain SSL"]

        subgraph CloudRunCluster["Serverless Compute (Google Cloud Run)"]
            WebContainer["notice-saathi-web Container\n(Next.js 15 Standalone Node Runtime)"]
            APIContainer["notice-saathi-api Container\n(FastAPI Uvicorn Multi-Worker Runtime)"]
            WorkerJob["retention-worker Scheduled Job\n(Cloud Run Job triggered every 30 mins)"]
        end

        subgraph ManagedData["Managed State & Secrets"]
            Postgres[(Cloud SQL for PostgreSQL 16\nMulti-AZ High Availability Database)]
            GCSBucket["Cloud Storage Bucket (Private)\n`notice-saathi-document-storage`"]
            SecretMgr["Google Cloud Secret Manager\n(GNANI_API_KEY, SECRET_KEY, DB_PASS)"]
        end
    end

    Mobile -->|HTTPS| LB
    Desktop -->|HTTPS| LB
    LB -->|Path /*| WebContainer
    LB -->|Path /api/*| APIContainer

    WebContainer -->|Internal / Public API| APIContainer
    APIContainer -->|SQLAlchemy Connection Pool| Postgres
    APIContainer -->|Private Object Reads/Writes| GCSBucket
    APIContainer -->|Runtime Secret Ingestion| SecretMgr

    WorkerJob -->|Retention Sweep SQL| Postgres
    WorkerJob -->|Purge Expired Blobs| GCSBucket
```

---

## 7. Main Repository Directories & Responsibilities

| Directory | Responsibilities | Key Technologies |
| :--- | :--- | :--- |
| `apps/web/app/` | Next.js 15 App Router pages: `/`, `/upload`, `/documents/[id]`, `/history`, `/privacy`. | React 19, TypeScript, TailwindCSS v4 |
| `apps/web/components/` | Accessible UI components: `ActionCardComponent`, `ProofModal`, `Navbar`. | Lucide React, Headless accessible elements |
| `apps/web/lib/` | Frontend API client (`api.ts`) and Accessibility context (`accessibility.tsx`). | TypeScript, Web Audio API, LocalStorage |
| `backend/database/` | Database session manager (`session.py`) and schema definitions (`models.py`). | SQLAlchemy 2.0, SQLite / PostgreSQL |
| `backend/modules/answers/` | Question-answering engine with strict Case F conflict rules and abstentions. | Python 3.12, regex, token validation |
| `backend/modules/auth/` | Guest session creation, token validation, and DPDP consent tracking. | Cryptographic tokens, granular scopes |
| `backend/modules/citations/`| Citation integrity engine validating bounding-box coordinate proof. | Python, Bounding Box geometry |
| `backend/modules/documents/`| Document ingestion, PDF rasterization, and image quality assessment. | PyMuPDF, Pillow, Laplacian variance |
| `backend/modules/extraction/`| Structured entity and fact extraction (dates, currencies, directives). | Python regex, deterministic parsers |
| `backend/modules/gnani_stt/`| Gnani Prisma v2.5 Speech-to-Text integration and fallback mock engine. | httpx, multipart form parser |
| `backend/modules/gnani_tts/`| Gnani Timbre v2.5 Text-to-Speech integration and synthetic WAV generator. | httpx, wave, struct audio synthesis |
| `backend/modules/ocr/` | Local Optical Character Recognition without external cloud AI dependencies. | RapidOCR ONNX, numpy |
| `infra/` | Production container definitions and local Docker orchestration. | Dockerfiles, Docker Compose |
| `scripts/` | Standalone maintenance jobs, including expired document cleanup. | Python scripts, cron entry points |
| `services/api/` | FastAPI main application entry point, CORS, routes, and error handling. | FastAPI, Uvicorn, Starlette |
| `tests/` | Comprehensive test suite (unit, integration, security, OCR, translation). | Pytest, pytest-asyncio, PIL fixtures |

---

## 8. Current Local Architecture vs. Production Cloud Run Target

| Architectural Dimension | Current Local Development | Production Target (Google Cloud Run) |
| :--- | :--- | :--- |
| **Backend Runtime** | Python 3.12 Uvicorn process on `127.0.0.1:8000` | Google Cloud Run containerized service (`Dockerfile.api`) |
| **Frontend Runtime** | Node.js Next.js standalone process on `localhost:3000` | Google Cloud Run containerized service (`Dockerfile.web`) |
| **Database** | Local SQLite (`notice_saathi_v2.db`) | Google Cloud SQL for PostgreSQL 16 with private IP connection |
| **File Storage** | Local disk directory (`./data/storage`) | Google Cloud Storage (GCS) private bucket with service account IAM |
| **Secret Management** | Local `.env` file | Google Cloud Secret Manager with IAM secret accessor roles |
| **Data Retention** | On-demand UI purge + standalone script execution | Automated Cloud Run Job invoked every 30 minutes via Cloud Scheduler |
| **Speech APIs** | Gnani Prisma STT & Timbre TTS with offline mock fallbacks | Live Gnani AI production credentials via Secret Manager |
| **CORS Policy** | Permissive local development origins (`localhost:3000`) | Strict production domain origin matching without wildcard |
