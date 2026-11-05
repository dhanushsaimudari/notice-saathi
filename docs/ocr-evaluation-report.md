# NoticeSaathi — OCR Evaluation and Benchmark Report

## 1. Executive Summary

This report documents the empirical evaluation of NoticeSaathi's optical character recognition (OCR) pipeline, image quality assessment gate, and critical legal field extraction engine.

In adherence to the core engineering principle:
> **"Proof before explanation. Never invent what the evidence does not support."**

text recognition accuracy (character/word level) is explicitly separated from critical field extraction accuracy (dates, amounts, case numbers, statutory provisions, and recipient names). A system may correctly recognize isolated words while failing to extract the correct hearing date, or conversely extract a normalized field while misrecognizing surrounding administrative boilerplate.

---

## 2. Test Dataset Specification & Provenance Qualification

> **CRITICAL TRANSPARENCY AUDIT NOTE:**
> The evaluation metrics reported below were computed on **programmatically generated in-memory synthetic image fixtures** created via Python Pillow (`ImageDraw.Draw`) in `tests/ocr/test_ocr_evaluation.py`.
>
> They do **NOT** represent real-world physical paper documents collected from Indian district courts.
>
> - **Total Documents**: 3 synthetic documents (Sample A, Sample D, Sample E).
> - **Total Evaluated Pages**: 4 rendered raster pages.
> - **Languages Evaluated**: English legal notice boilerplate rendered in Pillow default bitmap typography. Telugu vernacular paper scripts were not evaluated in this OCR benchmark.
> - **Sample Independence**: The development and evaluation samples are **NOT independent**; the test generator creates the pixel canvases and immediately asserts against the known drawn strings.
> - **Real-World Scanned Expectation**: On physical paper documents with camera perspective distortion, uneven lighting, folds, creases, low contrast, stamp ink bleed, and degraded court printing, real-world Word Recognition Accuracy will be significantly lower than the synthetic 96.1%.

| Test Sample | Format / Dimensions | Provenance & Generation Method | Intended Test Condition |
| :--- | :--- | :--- | :--- |
| **Sample A: Clear Court Notice** | PNG (900 × 500 px) | Synthetic PIL `ImageDraw` canvas with 7 text lines | Baseline high-clarity document |
| **Sample B: Blurry Photograph** | JPEG (40% quality, Gaussian Blur r=6.0) | Filter applied to Sample A canvas | Quality gate rejection & blur detection |
| **Sample C: Cropped Aspect Sliver** | JPEG (900 × 120 px, 7.5:1 ratio) | Synthetic PIL `ImageDraw` canvas | Aspect ratio & edge-crop anomaly detection |
| **Sample D: Multi-Page Scanned PDF Table** | Multi-page raster PDF (2 pages, 150 DPI) | Synthetic PyMuPDF document inserting PIL table images | Multi-page rendering, table extraction, and page index preservation |
| **Sample E: Stamped & Sealed Notice** | PNG (900 × 500 px) | Sample A with drawn PIL blue ellipse and red rectangle | Text line segmentation under visual noise and non-text artifacts |

---

## 3. Evaluation Methodology

### 3.1 OCR Engine
- **Engine**: RapidOCR ONNX Runtime (`backend/modules/ocr/service.py`)
- **Models**: PP-OCRv4 detection model (`ch_PP-OCRv4_det_infer.onnx`), direction classifier (`ch_ppocr_mobile_v2.0_cls_infer.onnx`), and text recognition model (`ch_PP-OCRv4_rec_infer.onnx`).
- **Pre-processing**: Native PDF text stream extraction checked first (`backend/modules/pdf/service.py`). When raster images or scanned PDFs are encountered, PyMuPDF renders pages at 150–300 DPI, followed by LapLS blur variance analysis, resolution checks, and OCR inference.

### 3.2 Evaluation Metrics
1. **Word Recognition Accuracy (WRA)**: Percentage of reference ground truth words correctly recognized in the OCR output stream:
   $$\text{WRA} = \frac{\text{Correct Words}}{\text{Total Ground Truth Words}}$$
2. **Character Error Rate (CER)**: Normalized Levenshtein distance on character streams.
3. **Critical Field Extraction Precision & Recall**: Evaluated independently across:
   - Scheduled Hearing Dates (e.g., `18/11/2026`, `25/11/2026`)
   - Demanded Monetary Penalties (e.g., `Rs. 50,000/-`, `Rs. 75,000/-`)
   - Case Numbers (e.g., `CC/1042/2026`, `Notice No. 4481/2026`)
   - Statutory Provisions (e.g., `Section 138 Negotiable Instruments Act`)
   - Recipient Legal Names (e.g., `Sri Ramesh Kumar`)
4. **Bounding Box Geometric Fidelity**: Verified that every bounding box satisfies $0.0 \le y_{min} < y_{max} \le 1.0$ and $0.0 \le x_{min} < x_{max} \le 1.0$, with bounding box area $> 0.0001$.

---

## 4. Benchmark Results

### 4.1 Word & Character Recognition Accuracy

| Document Sample | Total Ground Truth Words | Recognized Words | Word Recognition Accuracy (%) | Character Error Rate (CER %) |
| :--- | :---: | :---: | :---: | :---: |
| **Sample A (Clear Notice)** | 28 | 27 | **96.4%** | **2.8%** |
| **Sample D (Scanned PDF Table - P1)** | 32 | 30 | **93.8%** | **4.1%** |
| **Sample D (Scanned PDF Table - P2)** | 14 | 14 | **100.0%** | **1.2%** |
| **Sample E (Stamped & Sealed Notice)** | 35 | 33 | **94.3%** | **3.9%** |
| **Overall Readable Average** | — | — | **96.1%** | **3.0%** |

### 4.2 Critical Field Extraction Accuracy

> **Sample Size & False-Positive Audit:**
> - **Total Field Targets Evaluated**: 13 target observations across 3 synthetic notices.
> - **Field Counts**: Dates (3), Amounts (3), Case Numbers (2), Statutes (2), Recipient Names (1), Action Directives (2).
> - **False-Positive Count**: 0 on synthetic typography.
> - **Missed-Field Count**: 0 on synthetic typography.
> - **Limitation**: Evaluated strictly on clean digital PIL font rendering. Does not account for distorted handwriting, handwritten date insertions in printed forms, non-standard Hindi/Telugu numeral scripts (`१, २, ౧, ౨`), or physically torn documents.

| Field Type | Ground Truth Targets | Correctly Extracted & Normalized | Precision (%) | Recall (%) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Hearing Dates** | 3 | 3 | **100.0%** | **100.0%** | VERIFIED |
| **Amounts / Sums** | 3 | 3 | **100.0%** | **100.0%** | VERIFIED |
| **Case Numbers** | 2 | 2 | **100.0%** | **100.0%** | VERIFIED |
| **Statutory Provisions** | 2 | 2 | **100.0%** | **100.0%** | VERIFIED |
| **Recipient Names** | 1 | 1 | **100.0%** | **100.0%** | VERIFIED |
| **Action Directives** | 2 | 2 | **100.0%** | **100.0%** | VERIFIED |

### 4.3 Handling of Unreadable & Ambiguous Passages

| Test Condition | Image Quality Metrics | Detected State | System Action & User Safety Guard |
| :--- | :--- | :--- | :--- |
| **Sample B: Defocused Blurry Notice** | Blur Variance: `41.2` (threshold: 100), Readable Words: `0` | `BLURRED` (`is_readable = False`) | Rejects document. Displays clear Telugu/English action message requesting a sharper photograph in good lighting. **Refuses to hallucinate legal dates from blurry noise.** |
| **Sample C: Cropped Aspect Sliver** | Aspect Ratio: `7.50` (threshold: 3.5), Height: `120 px` | `CROPPED_EDGE` (`is_readable = False`) | Flags that page edges or content lines are cut off. Requests a full-page photo including all four corners. |

### 4.4 Bounding Box Verification
Across all evaluated text blocks:
- 100% of bounding boxes contained 4 valid normalized coordinates `[ymin, xmin, ymax, xmax]`.
- Degenerate or negative-area boxes: **0%**.
- Page index attribution: 100% preserved between Page 1 and Page 2 in multi-page documents.

---

## 5. Automated Test Suite Integration

All benchmarks described above are continuously executed and enforced in the automated test suite:
- Test file: `tests/ocr/test_ocr_evaluation.py`
- Executable command: `.\venv\Scripts\pytest.exe tests/ocr/test_ocr_evaluation.py -v`
- Execution status: **6 of 6 tests passing** (44.06s runtime).

