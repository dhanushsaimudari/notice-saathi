import io
import math
import pytest
from PIL import Image, ImageDraw, ImageFilter
from backend.modules.ocr.service import extract_text_blocks_from_image
from backend.modules.pdf.service import render_pdf_page_to_png
from backend.modules.image_quality.service import assess_image_quality
from backend.modules.extraction.fact_service import extract_facts_from_blocks

def make_clear_notice_image() -> bytes:
    """Clear legal notice document image with critical notice fields."""
    img = Image.new("RGB", (900, 500), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((40, 40), "CITY CIVIL COURT AT HYDERABAD", fill=(0, 0, 0))
    draw.text((40, 90), "Case No: CC/1042/2026", fill=(0, 0, 0))
    draw.text((40, 140), "Notice under Section 138 Negotiable Instruments Act", fill=(0, 0, 0))
    draw.text((40, 190), "Hearing Date: 18/11/2026 at 10:30 AM", fill=(0, 0, 0))
    draw.text((40, 240), "Cheque Penalty Amount: Rs. 50,000/-", fill=(0, 0, 0))
    draw.text((40, 290), "To: Sri Ramesh Kumar, Respondent", fill=(0, 0, 0))
    draw.text((40, 340), "You are hereby required to appear in person without fail.", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def make_blurry_notice_image() -> bytes:
    """Severely blurred document image simulating camera motion or defocus."""
    base_bytes = make_clear_notice_image()
    img = Image.open(io.BytesIO(base_bytes))
    blurred = img.filter(ImageFilter.GaussianBlur(radius=6.0))
    buf = io.BytesIO()
    blurred.save(buf, format="JPEG", quality=40)
    return buf.getvalue()

def make_rotated_notice_image() -> bytes:
    """Notice image rotated 90 degrees."""
    base_bytes = make_clear_notice_image()
    img = Image.open(io.BytesIO(base_bytes))
    rotated = img.rotate(90, expand=True)
    buf = io.BytesIO()
    rotated.save(buf, format="PNG")
    return buf.getvalue()

def make_poor_lighting_image() -> bytes:
    """Notice image with severe non-uniform shadow / lighting falloff."""
    base_bytes = make_clear_notice_image()
    img = Image.open(io.BytesIO(base_bytes)).convert("L")
    w, h = img.size
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            factor = (x / w) * 0.4 + 0.1  # Heavy shadow on left side
            pixels[x, y] = int(pixels[x, y] * factor)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=75)
    return buf.getvalue()

def make_cropped_sliver_image() -> bytes:
    """Extreme cropped aspect ratio sliver."""
    img = Image.new("RGB", (900, 120), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 40), "Partial text line cut off at bottom edge...", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def make_scanned_pdf_with_table() -> bytes:
    """Multi-page scanned PDF with tabular facts (raster image only, no text stream)."""
    import pymupdf
    doc = pymupdf.open()
    
    # Page 1: Scanned table
    page1 = doc.new_page(width=600, height=800)
    table_img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    draw = ImageDraw.Draw(table_img)
    draw.text((30, 30), "SCHEDULE OF COURT HEARINGS - OFFICIAL NOTICE", fill=(0, 0, 0))
    draw.line([(30, 70), (750, 70)], fill=(0, 0, 0), width=2)
    draw.text((40, 90), "Notice Reference: Notice No. 4481/2026", fill=(0, 0, 0))
    draw.text((40, 140), "Statutory Reference: Section 138 Negotiable Instruments Act", fill=(0, 0, 0))
    draw.text((40, 190), "Scheduled Hearing Date: 25/11/2026", fill=(0, 0, 0))
    draw.text((40, 240), "Demanded Claim Amount: Rs. 75,000/-", fill=(0, 0, 0))
    draw.text((40, 290), "Action Required: The recipient must appear in person before this Court.", fill=(0, 0, 0))
    draw.line([(30, 340), (750, 340)], fill=(0, 0, 0), width=2)

    buf1 = io.BytesIO()
    table_img.save(buf1, format="PNG")
    page1.insert_image(page1.rect, stream=buf1.getvalue())

    # Page 2: Second page instructions
    page2 = doc.new_page(width=600, height=800)
    p2_img = Image.new("RGB", (800, 600), color=(255, 255, 255))
    draw2 = ImageDraw.Draw(p2_img)
    draw2.text((40, 50), "PAGE 2: INSTRUCTIONS AND LEGAL DISCLOSURES", fill=(0, 0, 0))
    draw2.text((40, 100), "Failure to appear may result in ex-parte proceedings.", fill=(0, 0, 0))
    buf2 = io.BytesIO()
    p2_img.save(buf2, format="PNG")
    page2.insert_image(page2.rect, stream=buf2.getvalue())

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def test_ocr_evaluation_clear_document():
    """Evaluates text accuracy, bounding boxes, and field extraction on clear notice."""
    img_bytes = make_clear_notice_image()
    blocks = extract_text_blocks_from_image(img_bytes, page_index=1)
    
    assert len(blocks) >= 4
    combined = " ".join(b.text_original.upper() for b in blocks)
    
    # Assert critical fields are recognized
    assert "CASE" in combined or "1042" in combined
    assert "138" in combined
    assert "18/11/2026" in combined or "18" in combined
    assert "50,000" in combined or "50000" in combined
    
    # Assert bounding boxes point to valid real regions [ymin, xmin, ymax, xmax]
    for b in blocks:
        assert len(b.bbox) == 4
        ymin, xmin, ymax, xmax = b.bbox
        assert 0.0 <= ymin <= ymax <= 1.0
        assert 0.0 <= xmin <= xmax <= 1.0
        assert b.confidence > 0.6

    # Assert fact extraction from real OCR blocks
    facts = extract_facts_from_blocks(blocks)
    field_types = {f.field_type for f in facts}
    assert "date" in field_types or "amount" in field_types or "case_number" in field_types

def test_ocr_evaluation_blurry_document_fails_quality_gate():
    """Evaluates that severely blurred documents are rejected and marked uncertain."""
    blurry_bytes = make_blurry_notice_image()
    blocks = extract_text_blocks_from_image(blurry_bytes, page_index=1)
    combined = " ".join(b.text_original for b in blocks)
    
    # Quality gate assessment
    quality = assess_image_quality(blurry_bytes, extracted_text_sample=combined)
    assert quality.is_readable is False
    assert quality.quality_state == "BLURRED"
    assert "blurry" in quality.action_message.lower()

def test_ocr_evaluation_cropped_sliver():
    """Evaluates that extreme aspect cropped documents trigger CROPPED_EDGE."""
    cropped_bytes = make_cropped_sliver_image()
    blocks = extract_text_blocks_from_image(cropped_bytes, page_index=1)
    combined = " ".join(b.text_original for b in blocks)
    
    quality = assess_image_quality(cropped_bytes, extracted_text_sample=combined)
    assert quality.is_readable is False
    assert quality.quality_state in ["CROPPED_EDGE", "LOW_RESOLUTION"]

def test_ocr_evaluation_multi_page_scanned_pdf():
    """Evaluates multi-page scanned PDF rendering, table extraction, and page index preservation."""
    pdf_bytes = make_scanned_pdf_with_table()
    
    # Page 1 rendering and OCR
    p1_png = render_pdf_page_to_png(pdf_bytes, page_index=1, dpi=150)
    assert p1_png is not None
    p1_blocks = extract_text_blocks_from_image(p1_png, page_index=1)
    assert len(p1_blocks) >= 3
    assert all(b.page_index == 1 for b in p1_blocks)

    # Extract facts from scanned table
    facts = extract_facts_from_blocks(p1_blocks)
    fact_dict = {f.field_type: f.normalized_value for f in facts}
    
    # Check that date, amount, or action were extracted
    assert any(k in fact_dict for k in ["date", "amount", "statutory_provision", "required_action"])

    # Page 2 rendering and OCR
    p2_png = render_pdf_page_to_png(pdf_bytes, page_index=2, dpi=150)
    assert p2_png is not None
    p2_blocks = extract_text_blocks_from_image(p2_png, page_index=2)
    assert len(p2_blocks) >= 1
    assert all(b.page_index == 2 for b in p2_blocks)

def make_notice_with_stamps_and_seals() -> bytes:
    """Document image with simulated circular official seal and endorsement stamp."""
    base_bytes = make_clear_notice_image()
    img = Image.open(io.BytesIO(base_bytes))
    draw = ImageDraw.Draw(img)
    # Circular official seal in blue ink
    draw.ellipse([(650, 60), (820, 230)], outline=(30, 60, 180), width=3)
    draw.text((680, 120), "SEAL OF COURT", fill=(30, 60, 180))
    draw.text((670, 150), "METROPOLITAN", fill=(30, 60, 180))
    # Red urgent stamp
    draw.rectangle([(620, 270), (850, 320)], outline=(200, 20, 20), width=2)
    draw.text((640, 285), "URGENT SUMMONS", fill=(200, 20, 20))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_ocr_evaluation_stamped_and_sealed_document():
    """Evaluates OCR extraction when documents have official court seals and stamps."""
    stamped_bytes = make_notice_with_stamps_and_seals()
    blocks = extract_text_blocks_from_image(stamped_bytes, page_index=1)
    
    assert len(blocks) >= 5
    combined = " ".join(b.text_original.upper() for b in blocks)
    
    # Core text is still extracted reliably despite the seal
    assert "138" in combined
    assert "18/11/2026" in combined or "18" in combined
    assert "50,000" in combined or "50000" in combined
    
    # Stamp / seal text is detected as discrete blocks
    assert any("SEAL" in b.text_original.upper() or "URGENT" in b.text_original.upper() for b in blocks)

def test_ocr_character_vs_field_accuracy_metrics():
    """
    Evaluates and separates:
    1. Word & Character Recognition Accuracy
    2. Critical Field Extraction Accuracy (Dates, Amounts, Statutes, Case Nos, Names)
    3. Bounding Box Geometric Integrity
    """
    ground_truth = {
        "court": "CITY CIVIL COURT AT HYDERABAD",
        "case_no": "CC/1042/2026",
        "statute": "Section 138 Negotiable Instruments Act",
        "date": "18/11/2026",
        "amount": "Rs. 50,000/-",
        "recipient": "Sri Ramesh Kumar",
        "action": "appear in person without fail"
    }
    
    img_bytes = make_clear_notice_image()
    blocks = extract_text_blocks_from_image(img_bytes, page_index=1)
    ocr_text = " ".join(b.text_original for b in blocks)
    
    # 1. Word Recognition Accuracy: Ground truth words found in OCR text
    gt_words = [w.lower() for w in "CITY CIVIL COURT HYDERABAD CC/1042/2026 Section 138 18/11/2026 50,000 Sri Ramesh Kumar appear person".split()]
    found_words = [w for w in gt_words if w in ocr_text.lower()]
    word_recognition_rate = len(found_words) / len(gt_words)
    assert word_recognition_rate >= 0.85, f"Word recognition rate was {word_recognition_rate:.2f}"
    
    # 2. Critical Field Extraction Accuracy
    facts = extract_facts_from_blocks(blocks)
    extracted_fields = {f.field_type: f for f in facts}
    
    # Field 1: Date
    assert "date" in extracted_fields
    assert "18/11/2026" in extracted_fields["date"].raw_value or "18" in extracted_fields["date"].raw_value
    
    # Field 2: Amount
    assert "amount" in extracted_fields
    assert "50,000" in extracted_fields["amount"].raw_value or "50000" in extracted_fields["amount"].raw_value
    
    # Field 3: Case Number or Statute
    assert "statutory_provision" in extracted_fields or "case_number" in extracted_fields
    
    # 3. Bounding box verification: bounding boxes must have area > 0 and be within normalized [0, 1] bounds
    for b in blocks:
        ymin, xmin, ymax, xmax = b.bbox
        assert 0.0 <= ymin < ymax <= 1.0
        assert 0.0 <= xmin < xmax <= 1.0
        box_area = (ymax - ymin) * (xmax - xmin)
        assert box_area > 0.0001, f"Block {b.block_id} has degenerate bbox: {b.bbox}"


