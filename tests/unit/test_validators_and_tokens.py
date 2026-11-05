import pytest
from fastapi import HTTPException
from backend.modules.normalization.service import normalize_date, normalize_currency, normalize_whitespace
from backend.modules.uploads.security import validate_upload_bytes
from backend.modules.image_quality.service import assess_image_quality
from PIL import Image, ImageDraw
import io

def test_date_normalization():
    assert normalize_date("18/11/2026") == "18/11/2026"
    assert normalize_date("2026-11-18") == "18/11/2026"
    assert normalize_date("18 Nov 2026") == "18/11/2026"

def test_currency_normalization():
    assert normalize_currency("Rs. 50,000/-") == "₹50,000"
    assert normalize_currency("INR 75,000") == "₹75,000"
    assert normalize_currency("₹ 1,00,000") == "₹1,00,000"

def test_magic_byte_validation_rejection():
    # Attempt to upload plain text disguised as PDF
    fake_pdf = b"Hello, this is just plain text, not a real PDF document!"
    with pytest.raises(HTTPException) as exc:
        validate_upload_bytes(fake_pdf, "notice.pdf", "application/pdf")
    assert exc.value.status_code == 400
    assert exc.value.detail["code"] == "INVALID_FILE_SIGNATURE"

def test_magic_byte_validation_success():
    valid_pdf_header = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    res = validate_upload_bytes(valid_pdf_header, "summons.pdf", "application/pdf")
    assert res["verified_media_type"] == "application/pdf"
    assert len(res["storage_key"]) > 10

def test_image_quality_blur_detection():
    # Create sharp synthetic image with high contrast text/lines
    img = Image.new("RGB", (600, 800), color="white")
    draw = ImageDraw.Draw(img)
    for i in range(10, 750, 20):
        draw.line([(50, i), (550, i)], fill="black", width=3)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    sharp_bytes = buf.getvalue()
    
    res_sharp = assess_image_quality(sharp_bytes)
    assert res_sharp.is_readable is True
    assert res_sharp.quality_state == "READABLE"
    
    # Create low resolution / blurred image
    tiny_img = Image.new("RGB", (100, 100), color="gray")
    tiny_buf = io.BytesIO()
    tiny_img.save(tiny_buf, format="JPEG")
    res_low_res = assess_image_quality(tiny_buf.getvalue())
    assert res_low_res.is_readable is False

