# NoticeSaathi — Physical Document OCR Pilot Evaluation Protocol

**Protocol Version:** 1.0 (Pilot Standard)  
**Target Sample Size:** Minimum 50 Permissioned Physical Document Photographs  
**Lead Evaluator:** AI & OCR Integration Lead, Computer Vision Specialist  
**Core Rule:** *Never convert synthetic in-memory OCR benchmarks into claimed real-world accuracy.*

---

## 1. Objective & Scope

This protocol specifies the empirical benchmarking process for evaluating NoticeSaathi's OCR pipeline against real-world photographed court summons, demand notices, and official orders collected from supervised pilot participants.

While automated test suites verify pipeline code against synthetic programmatic fixtures (e.g. PIL rendered images), **this protocol governs the physical benchmark required before public launch**.

---

## 2. Document Collection & Permissioning Process

1. **Informed Consent & Redaction**:
   - Only documents voluntarily provided by consenting participants are accepted.
   - All private personal details (party personal names, phone numbers, Aadhaar numbers, residential street addresses) must be redacted with physical black tape before photography.
2. **Double-Keyed Ground Truth Creation**:
   - Two independent human annotators transcribe the complete text of each photographed document.
   - Discrepancies are reconciled by a third reviewer to produce the canonical reference transcript.
   - Annotators explicitly tag critical fields:
     - `hearing_date` (Canonical `DD/MM/YYYY`)
     - `penalty_amount` (Canonical numeric value in INR)
     - `case_number` (Normalized case or notice identifier)
     - `statutory_section` (Section and Act name)
     - `expected_quality` (`READY` or `NEEDS_RECAPTURE`)

---

## 3. 50-Document Evaluation Test Matrix

The 50 collected physical documents must be distributed across the following real-world environmental conditions:

| Category | Condition Description | Minimum Samples | Expected Pipeline Behaviour |
| :--- | :--- | :--- | :--- |
| **A. Optimal / Baseline** | Flat paper, even indoor overhead lighting, 0° skew, >200 DPI | 10 | Complete text extraction; 0 missed critical fields; `state = "READY"`. |
| **B. Lighting Variations** | Low-light indoor (dim bulb, shadows from smartphone), direct glare on glossy court stamp | 8 | RapidOCR adaptive thresholding should extract text; glare over date must trigger honesty or recapture. |
| **C. Perspective & Skew** | 15° to 30° smartphone tilt angle, keystoning, trapezoidal distortion | 8 | RapidOCR DBNet text detector must correctly isolate rotated text boxes. |
| **D. Folds, Creases & Wrinkles** | Legal notice folded into three segments (envelope folds), creased across text lines | 8 | Text spanning folds must be reconstructed without dropping dates or amounts. |
| **E. Official Seals & Stamps** | Purple/blue rubber ink court stamps overlapping printed notice text | 6 | Must distinguish printed notice text from stamp ink; critical fields must not be corrupted. |
| **F. Low Resolution / Blurry** | Camera shake, out-of-focus phone photography (<120 DPI) | 5 | **Quality Gate Must Intercept**: Must trigger `state = "NEEDS_RECAPTURE"` with constructive guidance. Must NOT hallucinate facts. |
| **G. Partial Cropping** | Document corner or margin clipped outside camera frame | 3 | Must trigger `CROPPED_EDGE` or explain only visible text blocks. |
| **H. Multi-Page Scanned Documents** | 2 to 4 page stapled court petitions with tabular schedules | 2 (8 pages) | Multi-page PDF rasterization; page index preservation; page-level bounding boxes. |

---

## 4. Metrics & Evaluation Methodology

The automated evaluation script [`scripts/evaluate_physical_ocr_pilot.py`](file:///c:/Users/Hi/Desktop/PROJECTS/notice%20saathi/scripts/evaluate_physical_ocr_pilot.py) computes and reports the following distinct metric categories:

### 4.1 Text-Level Recognition Metrics
- **Word Recognition Accuracy (WRA)**:
  $$\text{WRA} = \max\left(0, 1 - \frac{\text{Levenshtein}(\text{words}_{\text{gt}}, \text{words}_{\text{pred}})}{\max(\text{len}(\text{words}_{\text{gt}}), 1)}\right) \times 100\%$$
- **Character Error Rate (CER)**:
  $$\text{CER} = \frac{\text{Levenshtein}(\text{chars}_{\text{gt}}, \text{chars}_{\text{pred}})}{\text{len}(\text{chars}_{\text{gt}})} \times 100\%$$

### 4.2 Critical Legal Field Metrics (Reported Separately)
Critical fields must **never** be averaged into general word accuracy:
1. **Scheduled Hearing Date Exact Match**:
   - *Precision*: $\frac{\text{Correct Dates Extracted}}{\text{Total Dates Extracted}}$
   - *Recall*: $\frac{\text{Correct Dates Extracted}}{\text{Ground Truth Dates Present}}$
2. **Missed Deadlines**: Ground truth specifies a court hearing date, but OCR/regex failed to detect it.
3. **False Extracted Deadlines**: OCR extracted a date when the ground truth had none, or extracted an erroneous date.
4. **Monetary Amounts Exact Match**: Exact numeric value match in INR.
5. **Case Identifiers Exact Match**: Case number and court registry prefix match.
6. **Statutory Provisions Exact Match**: Correct section and statute identification.

### 4.3 Quality Gate Abstention Evaluation
- **Abstention Accuracy**: Percentage of degraded/unreadable photos correctly flagged as `NEEDS_RECAPTURE`.
- **False Rejection Rate**: Clear documents incorrectly rejected by the Laplacian variance filter.
- **Unsafe Acceptance Rate**: Blurry documents accepted that produced corrupted facts. **Must be 0.0%**.

---

## 5. Execution Workflow

```bash
# 1. Place permissioned, redacted photographs in data/benchmarks/physical_pilot/
# 2. Populate ground truth manifest in data/benchmarks/physical_pilot_manifest.json
# 3. Execute automated evaluation engine
python scripts/evaluate_physical_ocr_pilot.py data/benchmarks/physical_pilot_manifest.json > docs/physical-ocr-pilot-results.json
```

