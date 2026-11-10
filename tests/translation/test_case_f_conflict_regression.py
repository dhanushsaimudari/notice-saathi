import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.models import Base, Document, DocumentPage, TextBlock
from backend.modules.answers.service import answer_user_question

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()

def test_case_f_seven_semantic_variants_conflict(test_db):
    """
    Task 1: If a document contains both a demand and an explicit waiver/cancellation/withdrawal,
    questions about the current obligation must return 'conflicting' and cite both contradictory passages.
    A question specifically asking what the waiver passage says must explain that passage,
    disclose the contradictory demand, and cite both passages.
    """
    doc = Document(
        document_id="doc_cf_vars",
        owner_id="user_cf",
        storage_key="test/case_f.pdf",
        checksum="chk_cf",
        original_filename="case_f_notice.pdf",
        media_type="application/pdf",
        state="COMPLETED",
        page_count=1
    )
    page = DocumentPage(page_id="p_cf_1", document_id="doc_cf_vars", page_index=1, quality_state="READABLE")
    b_demand = TextBlock(
        block_id="b_dem_1",
        document_id="doc_cf_vars",
        page_id="p_cf_1",
        page_number=1,
        text_original="Demand: You are required to pay the penalty of Rs. 50,000.",
        text_normalized="demand: you are required to pay the penalty of rs. 50,000.",
        bbox=[0.1, 0.1, 0.3, 0.9],
        confidence=0.98
    )
    b_waiver = TextBlock(
        block_id="b_waiv_1",
        document_id="doc_cf_vars",
        page_id="p_cf_1",
        page_number=1,
        text_original="Endorsement: The demanded payment is hereby waived per office order.",
        text_normalized="endorsement: the demanded payment is hereby waived per office order.",
        bbox=[0.4, 0.1, 0.6, 0.9],
        confidence=0.98
    )
    test_db.add_all([doc, page, b_demand, b_waiver])
    test_db.commit()

    obligation_questions = [
        "Has payment been waived?",
        "Do I still have to pay?",
        "Is the penalty cancelled?",
        "Has the demand been withdrawn?",
        "Is the amount still due?",
        "What action should I take regarding payment?"
    ]

    for q in obligation_questions:
        res = answer_user_question(db=test_db, document_id="doc_cf_vars", question_text=q, language="en-IN")
        assert res["answer_status"] == "conflicting", f"Expected 'conflicting' for query: '{q}', got '{res['answer_status']}'"
        assert "conflicting instructions" in res["summary_text"].lower() or "వైరుధ్యం" in res["summary_text"]
        
        # Verify both contradictory passages are cited
        cited_ids = {ref["block_id"] for claim in res.get("claims", []) for ref in claim.get("evidence", [])}
        assert "b_dem_1" in cited_ids, f"Demand passage not cited for '{q}'"
        assert "b_waiv_1" in cited_ids, f"Waiver passage not cited for '{q}'"

    # Specific waiver content question
    q_content = "What does the waiver endorsement say?"
    res_content = answer_user_question(db=test_db, document_id="doc_cf_vars", question_text=q_content, language="en-IN")
    assert res_content["answer_status"] == "supported"
    assert "waived per office order" in res_content["summary_text"].lower()
    assert "contradictory demand" in res_content["summary_text"].lower()
    cited_ids_content = {ref["block_id"] for claim in res_content.get("claims", []) for ref in claim.get("evidence", [])}
    assert "b_dem_1" in cited_ids_content, "Contradictory demand passage must be cited in evidence"
    assert "b_waiv_1" in cited_ids_content, "Waiver endorsement passage must be cited in evidence"

def test_case_f_generalization_equivalent_wording(test_db):
    """
    Tests that conflict detection generalizes to varied legal terminology (summons, arrears, dismissed).
    """
    doc = Document(
        document_id="doc_gen_cf",
        owner_id="user_gen",
        storage_key="test/gen.pdf",
        checksum="chk_gen",
        original_filename="gen.pdf",
        media_type="application/pdf",
        state="COMPLETED",
        page_count=1
    )
    p = DocumentPage(page_id="p_gen_1", document_id="doc_gen_cf", page_index=1, quality_state="READABLE")
    b1 = TextBlock(
        block_id="b_summons",
        document_id="doc_gen_cf",
        page_id="p_gen_1",
        page_number=1,
        text_original="Order: Directed to pay outstanding tax arrears of Rs. 25,000 immediately.",
        text_normalized="order: directed to pay outstanding tax arrears of rs. 25,000 immediately.",
        bbox=[0.1, 0.1, 0.3, 0.9],
        confidence=0.98
    )
    b2 = TextBlock(
        block_id="b_dismissed",
        document_id="doc_gen_cf",
        page_id="p_gen_1",
        page_number=1,
        text_original="Notice: Proceedings have been dismissed and penalty is cancelled under amnesty scheme.",
        text_normalized="notice: proceedings have been dismissed and penalty is cancelled under amnesty scheme.",
        bbox=[0.4, 0.1, 0.6, 0.9],
        confidence=0.98
    )
    test_db.add_all([doc, p, b1, b2])
    test_db.commit()

    res = answer_user_question(db=test_db, document_id="doc_gen_cf", question_text="Do I still have to pay?", language="en-IN")
    assert res["answer_status"] == "conflicting"
    cited = {ref["block_id"] for claim in res.get("claims", []) for ref in claim.get("evidence", [])}
    assert "b_summons" in cited and "b_dismissed" in cited

def test_control_demand_only_no_waiver(test_db):
    """Control: When only demand exists, system should not invent a waiver."""
    doc = Document(document_id="doc_ctrl_dem", owner_id="u_dem", storage_key="k_dem", checksum="c_dem", original_filename="dem.pdf", media_type="application/pdf", state="COMPLETED", page_count=1)
    p = DocumentPage(page_id="p_ctrl_dem", document_id="doc_ctrl_dem", page_index=1, quality_state="READABLE")
    b = TextBlock(block_id="b_ctrl_dem", document_id="doc_ctrl_dem", page_id="p_ctrl_dem", page_number=1, text_original="Demand: You are required to pay the penalty of Rs. 50,000.", text_normalized="demand: you are required to pay the penalty of rs. 50,000.", bbox=[0.1, 0.1, 0.3, 0.9], confidence=0.98)
    test_db.add_all([doc, p, b])
    test_db.commit()

    res_waiver = answer_user_question(db=test_db, document_id="doc_ctrl_dem", question_text="Has payment been waived?", language="en-IN")
    assert res_waiver["answer_status"] == "supported"
    assert "no waiver" in res_waiver["summary_text"].lower()

    res_pay = answer_user_question(db=test_db, document_id="doc_ctrl_dem", question_text="Do I still have to pay?", language="en-IN")
    assert res_pay["answer_status"] == "supported"
    assert "payment is required" in res_pay["summary_text"].lower()

    res_say = answer_user_question(db=test_db, document_id="doc_ctrl_dem", question_text="What does the waiver endorsement say?", language="en-IN")
    assert res_say["answer_status"] == "not_found"

def test_control_waiver_only_no_demand(test_db):
    """Control: When only waiver exists, system should not invent a demand."""
    doc = Document(document_id="doc_ctrl_waiv", owner_id="u_w", storage_key="k_w", checksum="c_w", original_filename="w.pdf", media_type="application/pdf", state="COMPLETED", page_count=1)
    p = DocumentPage(page_id="p_ctrl_w", document_id="doc_ctrl_waiv", page_index=1, quality_state="READABLE")
    b = TextBlock(block_id="b_ctrl_w", document_id="doc_ctrl_waiv", page_id="p_ctrl_w", page_number=1, text_original="Endorsement: The demanded payment is hereby waived per office order.", text_normalized="endorsement: the demanded payment is hereby waived per office order.", bbox=[0.4, 0.1, 0.6, 0.9], confidence=0.98)
    test_db.add_all([doc, p, b])
    test_db.commit()

    res_waiver = answer_user_question(db=test_db, document_id="doc_ctrl_waiv", question_text="Has payment been waived?", language="en-IN")
    assert res_waiver["answer_status"] == "supported"
    assert "waived" in res_waiver["summary_text"].lower()

    res_pay = answer_user_question(db=test_db, document_id="doc_ctrl_waiv", question_text="Do I still have to pay?", language="en-IN")
    assert res_pay["answer_status"] == "supported"
    assert "not required" in res_pay["summary_text"].lower()

    res_say = answer_user_question(db=test_db, document_id="doc_ctrl_waiv", question_text="What does the waiver endorsement say?", language="en-IN")
    assert res_say["answer_status"] == "supported"
    assert "waived per office order" in res_say["summary_text"].lower()

