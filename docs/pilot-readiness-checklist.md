# NoticeSaathi — Controlled Pilot Readiness Checklist & Comprehensive Status

**Report Date:** 2026-10-30  
**Audit Classification:** **CONTROLLED PILOT CANDIDATE**  
**Core Product Promise:** *Proof before explanation. Never invent what the evidence does not support.*

> [!CAUTION]
> **Honest Operational Disclosures**:
> 1. Passing automated test suites (71 passed, 1 skipped) certifies **code correctness and architectural safety**, but does **NOT** equal completed user pilot testing.
> 2. Live Gnani AI cloud API integration remains **LIVE UNVERIFIED** because `GNANI_API_KEY` is not provisioned in the local environment. Mocks are never reported as live successes.
> 3. Synthetic OCR accuracy (96.1% WRA, 3.0% CER) was measured on programmatically rendered in-memory images. Real-world accuracy on degraded physical court notices remains **PENDING** field collection of the 50-sample benchmark.
> 4. NoticeSaathi classifies documents based on visible contents only and does **NOT** assert that issuing authority, jurisdiction, or authenticity is independently verified.

---

## 1. Readiness Matrix by Priority

| Priority Area | Subsystem | Implemented Components | Verification Status | Operational Blocker for Public Release |
| :--- | :--- | :--- | :--- | :--- |
| **Priority 1: Voice & Data Privacy** | Granular 4-Scope Consent Model | `backend/modules/auth/service.py`, `services/api/main.py`, `docs/voice-privacy-and-consent.md` | **VERIFIED BY CODE & TESTS** (Enforced on upload, voice turns, TTS, and cloud translation) | None. Complete granular consent architecture active. |
| **Priority 2: Live Gnani Integration** | Prisma v2.5 STT & Timbre v2.5 TTS Adapters | `backend/modules/gnani_stt/`, `backend/modules/gnani_tts/`, `tests/integration/test_gnani_contract.py` | **CONTRACT & MOCK VERIFIED** / **LIVE CLOUD UNVERIFIED** | **BLK-01**: `GNANI_API_KEY` must be provisioned and tested with live speech in staging. |
| **Priority 3: Physical Document OCR** | Physical Benchmark Engine & Protocol | `scripts/evaluate_physical_ocr_pilot.py`, `docs/physical-ocr-evaluation-protocol.md` | **PROTOCOL & EVALUATOR READY** / **FIELD BENCHMARK PENDING** | **BLK-02**: Caseworkers must photograph 50 permissioned, redacted real physical notices. |
| **Priority 4: Elderly User Evaluation** | 10-Task Supervised Usability Protocol | `docs/elderly-user-testing-protocol.md`, Next.js accessible frontend | **PROTOCOL & INTERFACE READY** / **HUMAN TESTING PENDING** | **BLK-03**: Supervised sessions with 15–20 older adults across Telangana & Andhra Pradesh. |
| **Priority 5: Staging Infrastructure** | PostgreSQL, Health Probe, Backup & Retention | `infra/docker-compose.yml`, `scripts/cleanup_expired_documents.py`, `scripts/backup_restore.py`, `docs/pilot-deployment-runbook.md` | **IMPLEMENTED & LOCALLY TESTED** / **CLOUD SERVER PROVISIONING PENDING** | **BLK-04**: Deploy Docker containers to staging VM with HTTPS domain. |
| **Priority 6: End-to-End Scenarios** | Pilot Happy Path & Failure Modes | `tests/integration/test_pilot_e2e_scenarios.py` | **VERIFIED** (Happy path, blur, missing dates, conflicts, unverified statutes pass) | None. Regression assertions pass cleanly. |

---

## 2. Test Execution & Verification Evidence

### Automated Test Suite: 71 Passed, 1 Skipped, 0 Failed
Executed with:
```bash
.\venv\Scripts\python.exe -m pytest -v
```

| Test File | Total Tests | Passed | Skipped | Failed | Coverage Focus |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `tests/translation/test_regional_explanation.py` | 25 | 25 | 0 | 0 | Token preservation, modals, negations, Cases A–F safety regressions |
| `tests/ai_eval/test_evidence_and_abstention.py` | 9 | 9 | 0 | 0 | Citation integrity, relevance validation, adversarial context, stale jobs |
| `tests/integration/test_api_endpoints.py` | 8 | 8 | 0 | 0 | HTTP upload, OCR QA, prompt injection, granular consent enforcement |
| `tests/integration/test_gnani_contract.py` | 7 | 6 | 1 | 0 | STT & TTS request contracts, timeouts, 401/503; 1 skipped (live external key) |
| `tests/ocr/test_ocr_evaluation.py` | 6 | 6 | 0 | 0 | Synthetic WRA (96.1%), CER (3.0%), field accuracy, blur, multi-page tables, seals |
| `tests/unit/test_validators_and_tokens.py` | 5 | 5 | 0 | 0 | Date/currency normalization, magic bytes, Laplacian blur |
| `tests/integration/test_pilot_e2e_scenarios.py` | 5 | 5 | 0 | 0 | Complete Telugu elderly user journey & failure scenario handling |
| `tests/security/test_security_and_idor.py` | 4 | 4 | 0 | 0 | Cross-user IDOR isolation, path traversal, cascade deletion |
| `tests/integration/test_gnani_adapters.py` | 3 | 3 | 0 | 0 | Audio WAV generator, mock telemetry, latency headers |
| **Total** | **72** | **71** | **1** | **0** | **100% Pass Rate across implemented features** |

### Frontend Production Build
Executed with:
```bash
cd apps/web && npm run build
```
**Result:** **Exit Code 0**, Compiled successfully in 10.1s. All 7 application routes statically and dynamically verified.

---

## 3. What Has Been Implemented vs. What Requires Human Evaluation

### Completed & Implemented
1. **Granular Voice & Multi-Channel Privacy Model**:
   - Backend-enforced checking for `document_processing`, `gnani_stt`, `gnani_tts`, and `external_translation`.
   - Rejection on unconsented requests with actionable text alternatives.
2. **Deterministic Telugu Legal Explanation Engine**:
   - Covers Section 138 NI Act, summons, appearances, amounts, and hearings.
   - Enforces Cases A–F safety regressions: never infers unstated payment demands or deadlines; never flips negative directives; qualifies document authenticity.
3. **Comprehensive ActionCard Domain State Model**:
   - 5 explicit states (`action_identified`, `no_action_found`, `action_not_identified_in_readable_text`, `relevant_page_unreadable`, `conflicting_action`).
   - UI displays non-green amber/rose badges whenever uncertainty exists.
4. **Disaster Recovery, Retention & Readiness Infrastructure**:
   - Automated 48-hour document cleanup worker (`scripts/cleanup_expired_documents.py`).
   - SQLite and PostgreSQL backup/restore tool (`scripts/backup_restore.py`).
   - Comprehensive `/api/v1/health` probe reporting DB, storage, OCR, Gnani, and translation engine status.
5. **Physical OCR Evaluation Framework**:
   - Double-keyed ground truth evaluator (`scripts/evaluate_physical_ocr_pilot.py`).

### Requiring Human & Field Evaluation Before General Public Release
1. **Physical Document Photography**: Collecting and benchmarking 50 real physical court summons across varying lighting, camera angles, folds, and ink stamps.
2. **Supervised Usability Sessions with Older Adults**: Conducting 10-task supervised evaluations with 15–20 participants across diverse vision, hearing, smartphone comfort, and regional Telugu dialect cohorts.
3. **Caseworker & Legal Review**: Systematic review of Telugu explanations by certified legal aid caseworkers to ensure clarity and verify zero unintended legal advice.
4. **Live Gnani Cloud Verification**: Executing end-to-end voice smoke tests with official account credentials once provisioned.

