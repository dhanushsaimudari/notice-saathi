import pytest
from fastapi import HTTPException
from backend.database.session import SessionLocal, init_db
from backend.database.models import Document, DocumentPage, TextBlock, ExtractedFact
from backend.modules.citations.validator import validate_claims_and_evidence, cross_check_user_context
from backend.modules.answers.service import answer_user_question
from backend.modules.legal.safety import verify_statutory_reference
from backend.modules.translation.service import protect_tokens, restore_tokens
from backend.modules.documents.service import process_document_pipeline

@pytest.fixture
def db():
    init_db()
    session = SessionLocal()
    yield session
    session.close()

def test_citation_integrity_blocks_fake_reference(db):
    doc_id = "doc_test_101"
    real_block = TextBlock(
        block_id="tb_real_1",
        page_id="p1",
        document_id=doc_id,
        text_original="Hearing scheduled for 18 November 2026.",
        text_normalized="Hearing scheduled for 18 November 2026."
    )
    
    draft_claims = [
        {
            "claim_id": "c1",
            "claim_text": "The hearing is on 18 November 2026.",
            "evidence": [{"block_id": "tb_FAKE_999"}]
        }
    ]
    
    report = validate_claims_and_evidence(draft_claims, doc_id, [real_block])
    assert report.is_valid is False
    assert len(report.unsupported_claims) == 1
    assert report.unsupported_claims[0]["reason_code"] == "INVALID_BLOCK_REFERENCE"

def test_relevance_validation_rejects_irrelevant_block_citation(db):
    """
    Verifies that citing a real block that has NO semantic overlap with the claim
    is rejected with IRRELEVANT_BLOCK_CITATION rather than being accepted simply
    because the block ID exists in the document.
    """
    doc_id = "doc_test_103"
    address_block = TextBlock(
        block_id="tb_addr_1",
        page_id="p1",
        document_id=doc_id,
        text_original="Flat 402, Shanti Nilayam, Ameerpet, Hyderabad - 500016.",
        text_normalized="Flat 402, Shanti Nilayam, Ameerpet, Hyderabad - 500016."
    )
    
    # Claim asserts payment amount ₹75,000, but falsely cites the address block
    draft_claims = [
        {
            "claim_id": "c_amt",
            "claim_text": "The demanded penalty amount is ₹75,000.",
            "evidence": [{"block_id": "tb_addr_1"}]
        }
    ]
    
    report = validate_claims_and_evidence(draft_claims, doc_id, [address_block])
    assert report.is_valid is False
    assert len(report.unsupported_claims) == 1
    assert report.unsupported_claims[0]["reason_code"] == "IRRELEVANT_BLOCK_CITATION"

def test_user_context_contradiction_detection():
    """
    Verifies that user-provided context is cross-checked against document blocks
    and contradictions are explicitly flagged without merging user claims into proof.
    """
    doc_blocks = [
        TextBlock(
            block_id="tb_1",
            page_id="p1",
            document_id="doc_1",
            text_original="Cheque dishonour penalty amount: Rs. 50,000/-. Scheduled appearance: 18/11/2026.",
            text_normalized="Cheque dishonour penalty amount: Rs. 50,000/-. Scheduled appearance: 18/11/2026."
        )
    ]
    
    # User wrongly believes amount is 10,000 and date is 25/12/2026
    user_notes = "I received this notice. The amount I have to pay is 10,000 rupees and hearing is 25/12/2026."
    report = cross_check_user_context(user_notes, doc_blocks)
    
    assert report["has_context"] is True
    assert len(report["contradicted_by_document"]) >= 1
    contradictions = " ".join(report["contradicted_by_document"])
    assert "10000" in contradictions or "25/12/2026" in contradictions

def test_conflicting_dates_trigger_uncertainty(db):
    doc_id = "doc_test_102"
    b1 = TextBlock(block_id="tb_1", page_id="p1", document_id=doc_id, text_original="Hearing date is 15/11/2026", text_normalized="Hearing date is 15/11/2026")
    b2 = TextBlock(block_id="tb_2", page_id="p1", document_id=doc_id, text_original="Court appearance on 25/11/2026", text_normalized="Court appearance on 25/11/2026")
    
    draft_claims = [
        {"claim_id": "c1", "claim_text": "Hearing date is 15/11/2026", "status": "supported", "evidence": [{"block_id": "tb_1"}]},
        {"claim_id": "c2", "claim_text": "Hearing date is 25/11/2026", "status": "supported", "evidence": [{"block_id": "tb_2"}]}
    ]
    
    report = validate_claims_and_evidence(draft_claims, doc_id, [b1, b2])
    assert len(report.conflicts) > 0
    assert any(c["status"] in ["uncertain", "conflicting"] for c in report.all_claims())

def test_abstention_on_unanswered_question(db):
    doc = Document(
        owner_id="user_test",
        storage_key="test_sample.pdf",
        checksum="chk123",
        original_filename="sample.pdf",
        media_type="application/pdf",
        state="READY"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    import uuid
    tb = TextBlock(
        block_id=f"tb_sample_{uuid.uuid4().hex[:6]}",
        page_id="p_sample",
        document_id=doc.document_id,
        text_original="Notice to appear for routine inquiry. Bring your identification card.",
        text_normalized="Notice to appear for routine inquiry. Bring your identification card."
    )
    db.add(tb)
    db.commit()
    
    res = answer_user_question(db, doc.document_id, "How much money do I have to pay?", language="en-IN")
    assert res["answer_status"] == "unsupported"
    assert "could not find an amount" in res["summary_text"].lower()

def test_legal_advice_query_is_guarded(db):
    doc = Document(
        owner_id="user_test",
        storage_key="test_sample2.pdf",
        checksum="chk456",
        original_filename="sample2.pdf",
        media_type="application/pdf",
        state="READY"
    )
    db.add(doc)
    db.commit()
    
    res = answer_user_question(db, doc.document_id, "Will I go to jail because of this notice?", language="en-IN")
    assert res["answer_status"] == "unsupported"
    assert "not establish guilt" in res["summary_text"].lower()
    assert "advocate" in res["action_advice"].lower()

def test_statutory_verification_and_limitation_disclaimer():
    """
    Verifies that Section 138 returns trusted source and central jurisdiction,
    while unverified statutes return clear limitation disclaimers.
    """
    v_res = verify_statutory_reference("Section 138 Negotiable Instruments Act")
    assert v_res["is_verified"] is True
    assert "Central" in v_res["jurisdiction"]
    assert "Ministry of Law and Justice" in v_res["trusted_source"]

    unv_res = verify_statutory_reference("Section 482 of XYZ Special Regulations")
    assert unv_res["is_verified"] is False
    assert "does not maintain an externally verified legal reference entry" in unv_res["disclaimer"]

def test_token_and_negation_preservation_telugu_cases():
    """
    Tests token protection for critical legal document strings:
    Dates, amounts, names, case numbers, statutory sections, and negation markers
    ('without fail', 'failure to appear') must remain untouched and restorable.
    """
    sample = (
        "Summons in Case No: CC/1042/2026 under Section 138 Negotiable Instruments Act. "
        "The drawer must pay ₹50,000/- on or before 18/11/2026. "
        "You are required to appear in person without fail. "
        "Failure to appear will lead to further proceedings."
    )
    
    protected, token_map = protect_tokens(sample)
    assert "__DATE_" in protected
    assert "__CURR_" in protected
    assert "__CASE_" in protected
    assert "__STAT_" in protected
    assert "__NEG_" in protected  # Both 'without fail' and 'failure to appear'
    
    # Restore tokens
    restored = restore_tokens(protected, token_map)
    assert restored == sample

def test_stale_job_cannot_resurrect_deleted_document(db):
    """
    Ensures that if a document has been marked DELETED, a stale background processing
    worker cannot resurrect it to PROCESSING or READY state.
    """
    doc = Document(
        owner_id="user_del",
        storage_key="deleted.pdf",
        checksum="chk999",
        original_filename="deleted.pdf",
        media_type="application/pdf",
        state="DELETED"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    
    with pytest.raises(HTTPException) as exc:
        process_document_pipeline(db, doc.document_id)
    assert exc.value.status_code == 400
    assert "Cannot process document marked for deletion" in exc.value.detail
