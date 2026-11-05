import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFilter
from services.api.main import app
from backend.database.session import init_db
from backend.modules.gnani_tts.adapter import generate_mock_wav

@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as test_client:
        yield test_client

def make_test_pdf(text: str) -> bytes:
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((50, 60), text, fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def make_blurred_image() -> bytes:
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((40, 100), "HEARING SCHEDULED ON 15/12/2026", fill=(0, 0, 0))
    # Apply heavy blur to simulate out-of-focus phone camera
    for _ in range(8):
        img = img.filter(ImageFilter.BLUR)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def test_happy_path_telugu_elderly_journey(client):
    """
    Exercises the complete end-to-end journey for a Telugu-speaking elderly user:
    1. Initializes session with consent.
    2. Uploads an English summons notice.
    3. Receives verified Telugu Action Cards with cited evidence blocks.
    4. Asks a spoken voice question via /voice-turns.
    5. Receives verified Telugu plain-language answer with source citations.
    6. Synthesizes speech via Gnani TTS (voice="Lavanya").
    7. Permanently deletes the document upon completion.
    """
    # 1. Initialize session
    sess_res = client.post("/api/v1/auth/session")
    assert sess_res.status_code == 200
    token = sess_res.json()["token"]
    headers = {"X-Session-Token": token}

    # 2. Upload English Court Notice
    notice_text = (
        "IN THE COURT OF THE SENIOR CIVIL JUDGE, HYDERABAD\n"
        "Reference No: CC/9988/2026\n"
        "Notice under Section 138 Negotiable Instruments Act\n"
        "Hearing date scheduled: 12/12/2026 at 10:30 AM.\n"
        "Penalty amount: Rs. 1,00,000/-\n"
        "You must appear in person before this Court without fail."
    )
    pdf_bytes = make_test_pdf(notice_text)
    up_res = client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("court_notice.pdf", pdf_bytes, "application/pdf")},
        data={"consent_document_processing": "true"}
    )
    assert up_res.status_code == 201
    doc_data = up_res.json()
    doc_id = doc_data["document_id"]
    assert doc_data["state"] == "READY"

    # 3. Fetch Action Cards with Telugu Explanations & Cited Proof
    cards_res = client.get(f"/api/v1/documents/{doc_id}/action-cards", headers=headers)
    assert cards_res.status_code == 200
    cards = cards_res.json()["cards"]
    assert len(cards) > 0
    c1 = cards[0]
    assert len(c1["proof_refs"]) > 0
    assert any('\u0c00' <= char <= '\u0c7f' for char in c1["what_means"])
    # Compulsory appearance directive preserved
    assert "తప్పనిసరిగా" in c1["what_action"] or "హాజరు" in c1["what_action"]

    # 4. Spoken Question Turn via Gnani STT
    audio_wav = generate_mock_wav(duration_s=1.2)
    voice_res = client.post(
        f"/api/v1/documents/{doc_id}/voice-turns",
        headers=headers,
        files={"audio_file": ("question.wav", audio_wav, "audio/wav")},
        data={"language_code": "te-IN", "consent_gnani_stt": "true"}
    )
    assert voice_res.status_code == 200
    voice_data = voice_res.json()
    assert voice_data["answer"] is not None
    spoken_text = voice_data["answer"].get("approved_spoken_output") or voice_data["answer"]["summary_text"]
    assert "12/12/2026" in spoken_text or "1,00,000" in spoken_text or any('\u0c00' <= char <= '\u0c7f' for char in spoken_text)

    # 5. Synthesize Spoken Answer via Gnani TTS
    tts_res = client.post(
        "/api/v1/speech/synthesize",
        headers=headers,
        json={"text": spoken_text, "language": "te-IN", "speed": 1.0}
    )
    assert tts_res.status_code == 200
    assert tts_res.headers["content-type"] == "audio/wav"
    assert len(tts_res.content) > 44  # Valid WAV header

    # 6. Delete Document Cascade
    del_res = client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["state"] == "DELETED"

def test_failure_scenario_blurry_photograph(client):
    """Asserts that out-of-focus phone photographs fail quality gate with constructive advice."""
    sess_res = client.post("/api/v1/auth/session")
    headers = {"X-Session-Token": sess_res.json()["token"]}

    blurred_jpg = make_blurred_image()
    up_res = client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("blurry_photo.jpg", blurred_jpg, "image/jpeg")},
        data={"consent_document_processing": "true"}
    )
    assert up_res.status_code == 201
    doc_id = up_res.json()["document_id"]

    st_res = client.get(f"/api/v1/documents/{doc_id}/status", headers=headers)
    assert st_res.status_code == 200
    st_data = st_res.json()
    assert st_data["state"] == "NEEDS_RECAPTURE"
    assert "blurry" in st_data["message"].lower() or "recapture" in st_data["message"].lower()

def test_failure_scenario_missing_date_abstention(client):
    """Asserts that notices with no date trigger honest uncertainty and never invent attendance dates."""
    sess_res = client.post("/api/v1/auth/session")
    headers = {"X-Session-Token": sess_res.json()["token"]}

    text_without_date = (
        "CITY CIVIL COURT HYDERABAD\n"
        "Reference No: CC/1122/2026\n"
        "The respondent is summoned to appear before this Court.\n"
        "Penalty amount: Rs. 25,000/-"
    )
    pdf_bytes = make_test_pdf(text_without_date)
    up_res = client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("notice.pdf", pdf_bytes, "application/pdf")},
        data={"consent_document_processing": "true"}
    )
    doc_id = up_res.json()["document_id"]

    # Ask for date
    q_res = client.post(
        f"/api/v1/documents/{doc_id}/questions",
        headers=headers,
        json={"question_text": "What is the scheduled appearance date?", "response_language": "en-IN"}
    )
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["answer_status"] in ["uncertain", "not_found"]
    assert q_data.get("supported_by_evidence", False) is False
    assert "cannot confirm" in q_data["summary_text"].lower() or "not" in q_data["summary_text"].lower() or "could not find" in q_data["summary_text"].lower()

def test_failure_scenario_conflicting_instructions(client):
    """Asserts that contradictory instructions trigger conflicting_action and abstain from choosing."""
    sess_res = client.post("/api/v1/auth/session")
    headers = {"X-Session-Token": sess_res.json()["token"]}

    conflicting_text = (
        "OFFICIAL DEMAND NOTICE\n"
        "Block A: You are required to pay the fine of Rs. 50,000 within 15 days.\n"
        "Block B: All penalties and payments have been waived by administrative order."
    )
    pdf_bytes = make_test_pdf(conflicting_text)
    up_res = client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("conflict.pdf", pdf_bytes, "application/pdf")},
        data={"consent_document_processing": "true"}
    )
    doc_id = up_res.json()["document_id"]

    cards_res = client.get(f"/api/v1/documents/{doc_id}/action-cards", headers=headers)
    assert cards_res.status_code == 200
    cards = cards_res.json()["cards"]
    assert any(c["status"] == "conflicting_action" for c in cards)

def test_failure_scenario_unverified_statute_disclaimer(client):
    """Asserts that unknown statutory citations provide limitation disclaimers and disclose jurisdiction."""
    sess_res = client.post("/api/v1/auth/session")
    headers = {"X-Session-Token": sess_res.json()["token"]}

    unknown_statute_text = (
        "ADMINISTRATIVE ORDER\n"
        "Notice under Section 999 of the Fantasy Code Act of 1888.\n"
        "Scheduled date: 20/12/2026."
    )
    pdf_bytes = make_test_pdf(unknown_statute_text)
    up_res = client.post(
        "/api/v1/documents",
        headers=headers,
        files={"file": ("unknown.pdf", pdf_bytes, "application/pdf")},
        data={"consent_document_processing": "true"}
    )
    doc_id = up_res.json()["document_id"]

    q_res = client.post(
        f"/api/v1/documents/{doc_id}/questions",
        headers=headers,
        json={"question_text": "What does Section 999 mean and what are the penalties?", "response_language": "en-IN"}
    )
    assert q_res.status_code == 200
    q_data = q_res.json()
    assert q_data["disclaimer"] is not None
    assert "legal professional" in q_data["disclaimer"].lower() or "counsel" in q_data["disclaimer"].lower()
