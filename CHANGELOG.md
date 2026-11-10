# Changelog

All notable changes to NoticeSaathi will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-10

### Fixed
- **Bilingual Voice Input & Real-Time Speech Recognition (`apps/web/app/documents/[id]/ask/page.tsx`)**:
  - Integrated native browser streaming Web Speech Recognition (`webkitSpeechRecognition` / `SpeechRecognition`) supporting real-time interim transcription and automatic Voice Activity Detection (VAD).
  - Added dedicated Voice Language Selector supporting both **Telugu (`te-IN`)** and **English (`en-IN`)** voice queries.
  - Added an 8-second auto-stop guard to prevent the microphone from remaining stuck in an indefinite listening state.
  - Resolved HTTP 403 `CONSENT_REQUIRED_GNANI_STT` backend rejection by explicitly attaching `consent_gnani_stt=true` in `api.submitVoiceTurn` ([apps/web/lib/api.ts](file:///c:/Users/Hi/Desktop/PROJECTS/notice%20saathi/apps/web/lib/api.ts)).
- **Upload File Selection & Accessibility (`apps/web/app/upload/page.tsx`, `apps/web/app/page.tsx`)**:
  - Replaced hidden file input trigger button with native accessible HTML `<label htmlFor="file-upload">` and `sr-only` input, ensuring reliable file picker invocation across all desktop, tablet, and mobile browsers.
  - Reset file input `.value = ""` on click to guarantee `onChange` triggers every time, even if the same file is selected repeatedly.
  - Automated immediate upload and document processing upon file selection, eliminating unnecessary second confirmation step while providing live document preview and processing progress.
  - Implemented URL query parameter routing (`/upload?pick=file` and `/upload?pick=camera`) so clicking "Take Photo" or "Upload Notice" on the home page opens the camera viewfinder or file chooser immediately.

### Added
- Complete Google Cloud Run production deployment documentation ([docs/deployment-google-cloud.md](file:///c:/Users/Hi/Desktop/PROJECTS/notice%20saathi/docs/deployment-google-cloud.md)) covering Cloud Run services, Cloud SQL PostgreSQL 16, Google Cloud Storage, Secret Manager, and Cloud Scheduler retention sweep.
- Clean `.env.example` template with comprehensive environment variable documentation and zero active secrets.
- 22-section forensic engineering report ([docs/final-engineering-report.md](file:///c:/Users/Hi/Desktop/PROJECTS/notice%20saathi/docs/final-engineering-report.md)) detailing code audits, root cause analyses, and demo readiness.

---

## [1.0.0-rc2] - 2026-11-09

### Fixed
- **Upload Polling Failure ("The Stale Token Trap")**:
  - Propagated active guest session tokens (`X-Session-Token`) in response headers on `/documents` and `/documents/{id}/status`.
  - Added frontend localStorage session token synchronization in `apps/web/lib/api.ts` to prevent session drift and false 403 authorization rejections.
  - Updated `apps/web/app/upload/page.tsx` to transition immediately to `/documents/{id}` when upload status returns `READY`, eliminating polling race conditions.
  - Added bounded retry logic (up to 3 attempts) and a dedicated `status_error` state with "Check Status Again" and "Go to Document" controls to prevent duplicate file uploads.
  - Implemented unmount timer cleanup preventing memory leaks.
- **Async Socket Hang in Integration Test Runner**:
  - Identified and resolved Windows Proactor loopback TCP socket connection hang during offline test execution.
  - Added non-blocking connect timeouts (`httpx.Timeout(connect=4.0, read=25.0)`) across `GnaniSTTAdapter` and `GnaniTTSAdapter`.
  - Separately gated `test_voice_question_turn_http` with `RUN_LIVE_GNANI_TESTS` to prevent test suite deadlocks when external internet access is disabled.
- **Privacy Disclosures**:
  - Corrected unverified claims regarding DPDP legal certification and automated retention in the footer and privacy policy (`apps/web/app/layout.tsx`, `apps/web/app/privacy/page.tsx`).

### Added
- Comprehensive test coverage: 87 passing tests, 1 skipped test in the automated backend test suite.
- Root `.dockerignore` for containerized deployments.
- Detailed architecture and Google Cloud Run deployment documentation (`docs/architecture.md`, `docs/deployment-google-cloud.md`).

---

## [1.0.0-rc1] - 2026-11-08

### Added
- Case F conflict detection regression tests across 7 semantic query variants.
- Strict citation validation rejecting ungrounded or mismatched bounding boxes.
- Quality gate triggering `NEEDS_RECAPTURE` on blurry or severely cropped photographs.
- Full Telugu voice synthesis with speed controls (0.85x, 1.0x, 1.15x).
- Granular consent tracking for document processing, cloud translation, and Gnani voice integrations.

### Changed
- Refactored `backend/modules/answers/service.py` to prioritize conflict detection before amount and date extractions.
- Strengthened production configuration safeguards rejecting weak secret keys and wildcard CORS in production environments.
