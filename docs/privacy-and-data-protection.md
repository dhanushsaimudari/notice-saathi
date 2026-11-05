# NoticeSaathi — Privacy, Data Minimization & External Provider Assessment

**Date:** 2026-10-29  
**Security & Privacy Principle:** *Evidence privacy first. Protect vulnerable users from unauthorized data dissemination.*

---

## 1. Data Minimization Architecture

NoticeSaathi is designed to assist elderly, low-vision, and vulnerable citizens with sensitive legal documents (such as court summons, cheque bounce notices, debt recovery demands, and administrative orders).

### Core Data Isolation Rules
1. **Never Transmit Raw Notices**: No raw document files are sent to the translation provider; limited masked text may be transmitted with explicit consent. NoticeSaathi never transmits original document photographs, scanned PDF raster bytes, or full OCR page dumps to third-party cloud translation or AI services.
2. **Local Document Processing**:
   - PDF rasterization is performed locally via PyMuPDF.
   - Text detection and line recognition are performed on-device via RapidOCR (ONNX runtime).
   - Entity extraction (dates, amounts, case numbers, statutory sections) is executed entirely by deterministic local regex and parsing engines.
3. **Minimization of Translated Text**:
   - Only a short plain-language explanation of the verified facts (typically 15 to 30 words) is ever eligible for translation.
   - Sensitive entities (case numbers, monetary figures, dates, recipient names) are replaced with synthetic placeholder tokens (e.g., `__CASE_0__`, `__CURR_1__`, `__NAME_2__`) before any text is dispatched to an external provider.
4. **Local Fallback by Default**:
   - For standard notice elements (hearing schedules, summons to appear, payment demands, statutory sections), NoticeSaathi utilizes the local `GroundedLegalExplanationProvider`.
   - Local translation requires zero external network calls and guarantees zero data leakage.

---

## 2. User Notice & Consent Flow

In compliance with the Digital Personal Data Protection Act (DPDP Act, India) and ethical AI principles:

| Processing Stage | Data Processed | Processing Location | User Notice & Consent Requirement |
| :--- | :--- | :--- | :--- |
| **Document Upload & OCR** | Notice image / PDF | Local server / on-premise storage | Consent granted on session initialization (`purpose="document_reading"`). |
| **Evidence Extraction** | Extracted text blocks & bounding boxes | Local server / SQLite / PostgreSQL | Consent covered by document reading policy. |
| **Local Regional Explanation** | Grounded facts & Action Cards | Local Grounded Grammar Engine | Operates locally without data transmission. |
| **External Cloud Translation** | Token-masked explanation sentence (e.g. 20 words) | Google Cloud Translation / Azure Translator / Gemini | **Requires explicit opt-in consent** (`purpose="external_cloud_translation"`). If unconsented, cloud translation is refused and local fallback is used. |
| **Speech Synthesis (TTS)** | Approved Telugu explanation text | Gnani Timbre API | Audio synthesis of approved text; no document PII transmitted. |

### Consent Revocation
Users can withdraw consent at any time. When consent is withdrawn:
- The `ConsentRecord.withdrawn_at` timestamp is recorded.
- The system immediately suspends external cloud calls for that actor and restricts operations to local grounded processing.

---

## 3. External Translation Provider Assessment

Before integrating any third-party cloud provider, NoticeSaathi conducts a privacy and retention assessment:

| Provider | Transmission Protocol & Endpoint | Data Retention & Training Terms | Compliance & Security Standard | Recommendation for NoticeSaathi |
| :--- | :--- | :--- | :--- | :--- |
| **Google Cloud Translation API (v2 / v3)** | HTTPS (TLS 1.3), `translation.googleapis.com` | Google Cloud Enterprise terms: Google does not store customer data for model training; data in transit is discarded after request processing. | ISO/IEC 27001, SOC 1/2/3, HIPAA-ready | **Approved for enterprise deployment** with API key restricted to server IP. |
| **Microsoft Azure Translator (v3.0)** | HTTPS (TLS 1.3), `api.cognitive.microsofttranslator.com` | "No Trace" policy: Microsoft Translator does not retain, record, or log any text sent for translation. Customer text is not used to train models. | ISO/IEC 27001, SOC 1/2/3, FedRAMP | **Approved for enterprise deployment** with region pinning (`centralindia`). |
| **Google Gemini API (1.5 Flash)** | HTTPS (TLS 1.3), `generativelanguage.googleapis.com` | Google Cloud Vertex AI terms guarantee zero customer data logging. Free-tier consumer keys log prompts for evaluation. | SOC 2 | **Permitted only with Enterprise / Cloud project credentials**; consumer keys restricted. |

---

## 4. Log Scrubbing & Credential Protection

To ensure credentials and sensitive information never appear in system logs:
1. `backend/modules/translation/providers/base.py` implements `scrub_sensitive_info()`:
   - Matches and masks API keys, bearer tokens, passwords, and authorization headers (`***REDACTED***`).
2. Document text blocks and user notes are excluded from standard access logs.
3. System errors output only structured error codes (`AUTH_FAILURE`, `TIMEOUT`, `RATE_LIMIT`) and status codes, never dumping raw user inputs into unencrypted log sinks.

