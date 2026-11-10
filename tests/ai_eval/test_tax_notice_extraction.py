import os
import pytest
from pathlib import Path
from sqlalchemy.orm import Session

from backend.database.session import SessionLocal, init_db
from backend.database.models import Document, TextBlock, ExtractedFact, ActionCard
from backend.modules.documents.service import create_document_record, process_document_pipeline
from backend.modules.answers.service import generate_action_cards_for_document, answer_user_question

FIXTURE_PATH = Path("tests/fixtures/gvmc_tax_notice.jpg")

@pytest.fixture(scope="module")
def db_session():
    init_db()
    session = SessionLocal()
    yield session
    session.close()

def test_gvmc_tax_notice_complete_extraction_and_action_card(db_session: Session):
    """
    Validates end-to-end processing of the user's actual GVMC property tax reminder notice.
    Asserts:
    1. OCR captures all text blocks.
    2. Structured facts extracted for all 14 required fields with source evidence.
    3. Action Card status is 'action_identified' with explicit action (never 'no_action_found').
    4. Action Card contains comprehensive proof references (>= 8 blocks).
    5. Q&A answers deadline, total amount due, payment methods, and recipient with proof.
    """
    assert FIXTURE_PATH.exists(), f"Missing fixture: {FIXTURE_PATH}"
    file_bytes = FIXTURE_PATH.read_bytes()

    # 1. Run full document processing pipeline
    doc_initial = create_document_record(
        db=db_session,
        owner_id="test_tax_user",
        file_bytes=file_bytes,
        original_filename="gvmc_tax_notice.jpg",
        declared_media_type="image/jpeg"
    )
    doc = process_document_pipeline(
        db=db_session,
        document_id=doc_initial.document_id
    )

    assert doc.state == "READY"
    assert doc.page_count == 1

    # 2. Verify OCR blocks
    blocks = db_session.query(TextBlock).filter(TextBlock.document_id == doc.document_id).all()
    assert len(blocks) >= 30, f"Expected >= 30 OCR blocks, found {len(blocks)}"
    
    all_text = " ".join(b.text_original for b in blocks)
    assert "Vijayawada" in all_text
    assert "Ramesh" in all_text
    assert "7,000" in all_text
    assert "30 November 2026" in all_text

    # 3. Verify all 14 structured fields in extracted facts
    facts = db_session.query(ExtractedFact).filter(ExtractedFact.document_id == doc.document_id).all()
    facts_by_type = {}
    for f in facts:
        facts_by_type.setdefault(f.field_type, []).append(f)

    # 1. Issuing authority
    assert "issuing_authority" in facts_by_type
    assert "Vijayawada" in facts_by_type["issuing_authority"][0].normalized_value
    assert len(facts_by_type["issuing_authority"][0].evidence_refs) > 0

    # 2. Notice number
    assert "notice_number" in facts_by_type
    assert "GVMC/PT/2026-27/10482" in facts_by_type["notice_number"][0].raw_value

    # 3. Recipient name
    assert "recipient_name" in facts_by_type
    assert "Ramesh Kumar" in facts_by_type["recipient_name"][0].normalized_value

    # 4. Recipient address
    assert "recipient_address" in facts_by_type
    assert "Eluru Road" in facts_by_type["recipient_address"][0].raw_value

    # 5. Property ID
    assert "property_id" in facts_by_type
    assert "VJ-45872" in facts_by_type["property_id"][0].normalized_value

    # 6. Assessment year
    assert "assessment_year" in facts_by_type
    assert "2026-27" in facts_by_type["assessment_year"][0].normalized_value

    # 7. Total amount due
    assert "total_amount_due" in facts_by_type
    assert facts_by_type["total_amount_due"][0].normalized_value == "₹7,000.00"

    # 8. Tax amount
    assert "tax_amount" in facts_by_type
    assert facts_by_type["tax_amount"][0].normalized_value == "₹6,250.00"

    # 9. Additional fees / penalties
    assert "fee_penalty" in facts_by_type
    fee_names = [f.raw_value.lower() for f in facts_by_type["fee_penalty"]]
    assert any("building cess" in name for name in fee_names)
    assert any("swachh" in name for name in fee_names)

    # 10. Issue date
    issue_dates = [f for f in facts if f.field_type == "issue_date" or (f.field_type == "date" and f.reason_code == "issue_date")]
    assert len(issue_dates) > 0
    assert issue_dates[0].normalized_value == "10/10/2026"

    # 11. Payment due date
    due_dates = [f for f in facts if f.field_type == "payment_due_date" or (f.field_type == "date" and f.reason_code == "payment_due_date")]
    assert len(due_dates) > 0
    assert "30/11/2026" in due_dates[0].normalized_value

    # 12. Payment instructions
    assert "payment_instructions" in facts_by_type
    assert "gvmc.ap.gov.in" in facts_by_type["payment_instructions"][0].raw_value

    # 13. Contact details
    assert "contact_details" in facts_by_type
    assert "0866-2477722" in facts_by_type["contact_details"][0].raw_value

    # 14. Consequences / Warning
    assert "warning_consequence" in facts_by_type
    assert "penalty" in facts_by_type["warning_consequence"][0].raw_value.lower()

    # 4. Verify Action Cards
    cards_en = generate_action_cards_for_document(db_session, doc.document_id, language="en-IN")
    assert len(cards_en) >= 1
    c_en = cards_en[0]
    assert c_en.status == "action_identified"
    assert "Property Tax Reminder Notice" in c_en.title
    assert "7,000" in c_en.what_action
    assert "30/11/2026" in c_en.what_action or "30 November 2026" in c_en.what_action
    assert c_en.uncertainty is None
    # Verify rich evidence display (not just 1 or 2 blocks)
    assert len(c_en.proof_refs) >= 8, f"Expected >= 8 proof refs, got {len(c_en.proof_refs)}"

    # Telugu Action Card
    cards_te = generate_action_cards_for_document(db_session, doc.document_id, language="te-IN")
    c_te = cards_te[0]
    assert c_te.status == "action_identified"
    assert "ఆస్తి పన్ను" in c_te.title
    assert "7,000" in c_te.what_action
    assert "30/11/2026" in c_te.what_action or "30 November 2026" in c_te.what_action
    assert len(c_te.proof_refs) >= 8

    # 5. Verify Question Answering
    # Q1: Payment deadline
    ans_deadline = answer_user_question(
        db=db_session,
        document_id=doc.document_id,
        question_text="When is the payment deadline?",
        language="en-IN"
    )
    assert ans_deadline["answer_status"] == "supported"
    assert "30/11/2026" in ans_deadline["summary_text"] or "30 November 2026" in ans_deadline["summary_text"]
    assert len(ans_deadline["claims"]) > 0

    # Q2: Amount due
    ans_amt = answer_user_question(
        db=db_session,
        document_id=doc.document_id,
        question_text="How much is the total amount due?",
        language="en-IN"
    )
    assert ans_amt["answer_status"] == "supported"
    assert "7,000" in ans_amt["summary_text"]
    assert len(ans_amt["claims"]) > 0

    # Q3: How to pay
    ans_pay = answer_user_question(
        db=db_session,
        document_id=doc.document_id,
        question_text="How can I pay this tax?",
        language="en-IN"
    )
    assert ans_pay["answer_status"] == "supported"
    assert "gvmc.ap.gov.in" in ans_pay["summary_text"] or "Online" in ans_pay["summary_text"]

    # Q4: Recipient
    ans_who = answer_user_question(
        db=db_session,
        document_id=doc.document_id,
        question_text="Who is this notice addressed to?",
        language="en-IN"
    )
    assert ans_who["answer_status"] == "supported"
    assert "Ramesh Kumar" in ans_who["summary_text"]

    # Q5: Telugu deadline question
    ans_te_deadline = answer_user_question(
        db=db_session,
        document_id=doc.document_id,
        question_text="చెల్లింపు చివరి తేదీ ఎప్పుడు?",
        language="te-IN"
    )
    assert ans_te_deadline["answer_status"] == "supported"
    assert "30/11/2026" in ans_te_deadline["summary_text"] or "30 November 2026" in ans_te_deadline["summary_text"]
