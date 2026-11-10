import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.database.models import Document, TextBlock, ExtractedFact, ActionCard, DocumentPage
from backend.modules.citations.validator import validate_claims_and_evidence, cross_check_user_context
from backend.modules.translation.service import translate_phrase, translate_ui_label, translation_service
from backend.modules.legal.safety import check_out_of_bounds_legal_question, verify_statutory_reference

def generate_action_cards_for_document(db: Session, document_id: str, language: str = "te-IN") -> List[ActionCard]:
    """
    Generates evidence-backed Action Cards with Proof from document text blocks and facts.
    Strictly follows: 'Proof before explanation. Never invent what the evidence does not support.'
    Supports regional language (Telugu) generation with verified fact templates.
    """
    blocks = db.query(TextBlock).filter(TextBlock.document_id == document_id).all()
    facts = db.query(ExtractedFact).filter(ExtractedFact.document_id == document_id).all()
    pages = db.query(DocumentPage).filter(DocumentPage.document_id == document_id).all()
    unreadable_pages = [p for p in pages if p.quality_state in ["BLURRED", "CROPPED", "CROPPED_EDGE", "LOW_RES", "LOW_RESOLUTION", "UNREADABLE"]]

    cards: List[ActionCard] = []
    first_block = blocks[0] if blocks else None

    # Check document category
    is_court = any("court" in b.text_original.lower() or "summons" in b.text_original.lower() or "case no" in b.text_original.lower() for b in blocks)
    is_tax = (
        any(f.field_type in ["property_id", "assessment_year", "tax_amount", "total_amount_due"] for f in facts) or
        any(k in b.text_original.lower() for b in blocks for k in ["property tax", "tax reminder", "municipal corporation", "assessment year", "building cess", "swachh bharat cess", "gvmc"])
    )

    is_te = language.startswith("te")
    if is_tax:
        title_str = "ఆస్తి పన్ను రిమైండర్ నోటీసు (Property Tax Reminder Notice)" if is_te else "Property Tax Reminder Notice"
    elif is_court:
        title_str = translate_phrase("court_notice_title", language)
    else:
        title_str = translate_phrase("official_notice_title", language)

    # Categorize facts
    authority_facts = [f for f in facts if f.field_type == "issuing_authority"]
    notice_facts = [f for f in facts if f.field_type == "notice_number"]
    recipient_facts = [f for f in facts if f.field_type == "recipient_name"]
    address_facts = [f for f in facts if f.field_type == "recipient_address"]
    property_facts = [f for f in facts if f.field_type == "property_id"]
    ay_facts = [f for f in facts if f.field_type == "assessment_year"]
    total_due_facts = [f for f in facts if f.field_type == "total_amount_due"]
    tax_amt_facts = [f for f in facts if f.field_type == "tax_amount"]
    fee_facts = [f for f in facts if f.field_type == "fee_penalty"]
    date_facts = [f for f in facts if f.field_type == "date"]
    due_date_facts = [f for f in facts if f.field_type == "payment_due_date" or (f.field_type == "date" and f.reason_code == "payment_due_date")]
    issue_date_facts = [f for f in facts if f.field_type == "issue_date" or (f.field_type == "date" and f.reason_code == "issue_date")]
    amount_facts = [f for f in facts if f.field_type == "amount"]
    action_facts = [f for f in facts if f.field_type == "required_action"]
    statute_facts = [f for f in facts if f.field_type in ["statutory_provision", "statutory_reference"]]
    case_facts = [f for f in facts if f.field_type == "case_number"]
    instr_facts = [f for f in facts if f.field_type == "payment_instructions"]
    warn_facts = [f for f in facts if f.field_type == "warning_consequence"]
    contact_facts = [f for f in facts if f.field_type == "contact_details"]

    # Detect conflicting instructions in blocks (Case F)
    pos_blocks = [b for b in blocks if any(k in b.text_original.lower() for k in ["required to pay", "must pay", "must appear", "appear in person without fail", "appear in person", "penalty of", "demanded", "payment required"])]
    neg_blocks = [b for b in blocks if any(k in b.text_original.lower() for k in ["waived", "not required", "need not", "cancelled", "dismissed", "exempted", "payment is waived", "penalty is cancelled"])]
    has_conflicting_action = bool(pos_blocks and neg_blocks)

    # Card 1: What is this document & Key Details
    if is_tax:
        # Formulate rich tax notice description
        if is_te:
            parts = ["నోటీసు వివరాలు:"]
            if authority_facts:
                parts.append(f"అధికారం: {authority_facts[0].normalized_value}.")
            if notice_facts:
                parts.append(f"నోటీసు నం: {notice_facts[0].normalized_value}.")
            if recipient_facts:
                rec_str = recipient_facts[0].normalized_value
                if address_facts:
                    rec_str += f", {address_facts[0].raw_value}"
                parts.append(f"గ్రహీత: {rec_str}.")
            if property_facts:
                parts.append(f"ప్రాపర్టీ ఐడీ: {property_facts[0].normalized_value}.")
            if ay_facts:
                parts.append(f"అసెస్మెంట్ సంవత్సరం: {ay_facts[0].normalized_value}.")
            if total_due_facts:
                parts.append(f"మొత్తం బకాయి: {total_due_facts[0].normalized_value}.")
            elif amount_facts:
                parts.append(f"మొత్తం: {amount_facts[0].normalized_value}.")
            if due_date_facts:
                parts.append(f"చెల్లింపు గడువు: {due_date_facts[0].normalized_value}.")
            elif date_facts:
                parts.append(f"తేదీ: {date_facts[0].normalized_value}.")
            what_says = " ".join(parts)

            what_means = (
                "పత్రంలో ఉన్న సమాచారం ప్రకారం, ఇది మునిసిపల్ కార్పొరేషన్ నుండి వచ్చిన ఆస్తి పన్ను చెల్లింపు రిమైండర్ నోటీసు "
                "(జారీ చేసిన అధికారాన్ని స్వతంత్రంగా ధ్రువీకరించలేదు). నిర్దేశిత గడువు లోపు పన్ను మొత్తాన్ని చెల్లించవలసి ఉంటుంది."
            )
        else:
            parts = ["Document details:"]
            if authority_facts:
                parts.append(f"Issuing Authority: {authority_facts[0].normalized_value}.")
            if notice_facts:
                parts.append(f"Notice No: {notice_facts[0].normalized_value}.")
            if recipient_facts:
                rec_str = recipient_facts[0].normalized_value
                if address_facts:
                    rec_str += f", {address_facts[0].raw_value}"
                parts.append(f"Recipient: {rec_str}.")
            if property_facts:
                parts.append(f"Property ID: {property_facts[0].normalized_value}.")
            if ay_facts:
                parts.append(f"Assessment Year: {ay_facts[0].normalized_value}.")
            if total_due_facts:
                parts.append(f"Total Amount Due: {total_due_facts[0].normalized_value}.")
            elif amount_facts:
                parts.append(f"Amount: {amount_facts[0].normalized_value}.")
            if due_date_facts:
                parts.append(f"Payment Deadline: {due_date_facts[0].normalized_value}.")
            elif date_facts:
                parts.append(f"Date: {date_facts[0].normalized_value}.")
            what_says = " ".join(parts)

            what_means = (
                "Based on visible text, this document appears to be a property tax reminder notice from the municipal corporation "
                "(issuing authority has not been independently verified), indicating that property tax is due for the specified assessment year."
            )

        # Tax Action Resolution
        if has_conflicting_action:
            card1_status = "conflicting_action"
            action_str = (
                "పరస్పర విరుద్ధమైన ఆదేశాలు: ఒక భాగంలో చర్య/చెల్లింపు తప్పనిసరి అని, మరో భాగంలో మినహాయింపు ఉందని పేర్కొనబడింది."
                if is_te else
                "Conflicting instructions: one passage states payment is required, while another indicates it is waived or not required."
            )
            card1_uncertainty = (
                "పత్రంలో పరస్పర విరుద్ధమైన ఆదేశాలు ఉన్నాయి. న్యాయ సలహా లేకుండా వీటిలో ఏది వర్తిస్తుందో నిర్ధారించలేము."
                if is_te else
                "The document contains contradictory instructions. The system cannot determine which instruction governs without legal review."
            )
        elif unreadable_pages and not due_date_facts and not total_due_facts:
            unreadable_nums = ", ".join(str(p.page_index) for p in unreadable_pages)
            card1_status = "relevant_page_unreadable"
            action_str = (
                f"పత్రంలోని పేజీ {unreadable_nums} అస్పష్టంగా ఉండడం వల్ల చర్య లేదా గడువును నిర్ధారించలేము."
                if is_te else
                f"Action could not be reliably identified because page {unreadable_nums} is unreadable."
            )
            card1_uncertainty = (
                f"పేజీ {unreadable_nums} అస్పష్టంగా ఉంది. దయచేసి స్పష్టమైన ఫోటో తీయండి."
                if is_te else
                f"Page {unreadable_nums} is low quality or blurred. Relevant instructions or deadlines may be missing. Please recapture."
            )
        elif due_date_facts or total_due_facts or instr_facts or action_facts:
            card1_status = "action_identified"
            card1_uncertainty = None
            due_str = due_date_facts[0].normalized_value if due_date_facts else "గడువు తేదీ"
            due_str_en = due_date_facts[0].normalized_value if due_date_facts else "the due date"
            tot_str = total_due_facts[0].normalized_value if total_due_facts else (amount_facts[0].normalized_value if amount_facts else "మొత్తం")
            tot_str_en = total_due_facts[0].normalized_value if total_due_facts else (amount_facts[0].normalized_value if amount_facts else "amount")

            if is_te:
                action_str = f"నోటీసులో కోరిన చర్య: పెనాల్టీ పడకుండా ఉండటానికి {due_str} లోపు మొత్తం {tot_str} చెల్లించాలి."
                if instr_facts:
                    action_str += f" చెల్లింపు విధానం: {instr_facts[0].normalized_value}."
            else:
                action_str = f"Pay property tax of {tot_str_en} on or before {due_str_en} to avoid penalty."
                if instr_facts:
                    action_str += f" Payment instructions: {instr_facts[0].normalized_value}."
        elif blocks:
            card1_status = "action_not_identified_in_readable_text"
            card1_uncertainty = None
            action_str = (
                "చదవగలిగిన పూర్తి పత్రంలో ఎటువంటి నిర్దిష్ట చర్య లేదా గడువు పేర్కొనబడలేదు."
                if is_te else
                "No required action or deadline was identified in the readable text of the document."
            )
        else:
            card1_status = "no_action_found"
            card1_uncertainty = None
            action_str = "ఎటువంటి చర్య కనుగొనబడలేదు." if is_te else "No action found."

    elif is_te:
        what_says = "పత్రంలో పేర్కొన్న వివరాలు: "
        if case_facts:
            what_says += f"కేసు నంబర్ {case_facts[0].raw_value}. "
        if date_facts:
            what_says += f"తేదీ: {date_facts[0].raw_value}. "
        if amount_facts:
            what_says += f"మొత్తం: {amount_facts[0].raw_value}. "
        if not date_facts and not amount_facts:
            what_says += f"'{first_block.text_original[:150]}' " if first_block else "అధికారిక నోటీసు."

        # Case C: Document Authenticity (Never claim issuing authority is verified)
        what_means = (
            "పత్రంలో ఉన్న సమాచారం ప్రకారం, ఇది న్యాయస్థాన నోటీసులా కనిపిస్తోంది (జారీ చేసిన అధికారాన్ని ప్రత్యేకంగా ధ్రువీకరించలేదు). "
            if is_court else "పత్రంలో ఉన్న సమాచారం ప్రకారం, ఇది అధికారిక నోటీసులా కనిపిస్తోంది (జారీ చేసిన అధికారాన్ని ప్రత్యేకంగా ధ్రువీకరించలేదు). "
        )
        if date_facts:
            what_means += f"ఇందులో తేదీ ({date_facts[0].normalized_value}) ప్రస్తావించబడింది. "
        if amount_facts:
            what_means += f"ఇందులో పేర్కొన్న మొత్తం ({amount_facts[0].normalized_value}) ప్రస్తావించబడింది. "

        # Action resolution (Cases B, D, E, F)
        if has_conflicting_action:
            card1_status = "conflicting_action"
            action_str = "పరస్పర విరుద్ధమైన ఆదేశాలు: ఒక భాగంలో చర్య/చెల్లింపు తప్పనిసరి అని, మరో భాగంలో మినహాయింపు ఉందని పేర్కొనబడింది."
            card1_uncertainty = "పత్రంలో పరస్పర విరుద్ధమైన ఆదేశాలు ఉన్నాయి. న్యాయ సలహా లేకుండా వీటిలో ఏది వర్తిస్తుందో నిర్ధారించలేము."
        elif unreadable_pages and not action_facts:
            unreadable_nums = ", ".join(str(p.page_index) for p in unreadable_pages)
            card1_status = "relevant_page_unreadable"
            action_str = f"పత్రంలోని పేజీ {unreadable_nums} అస్పష్టంగా ఉండడం వల్ల చర్య లేదా గడువును నిర్ధారించలేము."
            card1_uncertainty = f"పేజీ {unreadable_nums} అస్పష్టంగా ఉంది. ముఖ్యమైన చర్యలు ఆ పేజీలో ఉండే అవకాశం ఉంది. దయచేసి స్పష్టమైన ఫోటో తీయండి."
        elif not action_facts:
            card1_status = "action_not_identified_in_readable_text" if blocks else "no_action_found"
            action_str = "చదవగలిగిన పూర్తి పత్రంలో ఎటువంటి నిర్దిష్ట చర్య లేదా గడువు పేర్కొనబడలేదు." if blocks else "ఎటువంటి చర్య కనుగొనబడలేదు."
            card1_uncertainty = None
        else:
            act_raw = action_facts[0].normalized_value
            act_lower = act_raw.lower()
            if any(k in act_lower for k in ["not required to appear", "need not appear", "do not appear", "shall not appear", "no need to appear"]):
                card1_status = "action_identified"
                action_str = "నోటీసులో పేర్కొన్న సమాచారం: వ్యక్తిగతంగా హాజరు కావాల్సిన అవసరం లేదు."
                card1_uncertainty = None
            elif "may appear" in act_lower or "optional" in act_lower:
                card1_status = "action_identified"
                action_str = "నోటీసులో పేర్కొన్న సమాచారం: వ్యక్తిగతంగా హాజరు కావచ్చు (ఇది తప్పనిసరి కాదు, ఐచ్ఛికం)."
                card1_uncertainty = None
            elif "failure to appear" in act_lower or "if you fail to appear" in act_lower:
                card1_status = "action_identified"
                action_str = "హెచ్చరిక: విచారణకు హాజరు కాకపోతే తదుపరి చట్టపరమైన చర్యలు తీసుకునే అవకాశం ఉంది."
                card1_uncertainty = "ఇది హాజరు కాకపోతే ఎదురయ్యే హెచ్చరిక మాత్రమే, ప్రత్యక్ష ఆదేశం కాదు."
            else:
                card1_status = "action_identified"
                if date_facts:
                    action_str = f"నోటీసులో కోరిన చర్య: పేర్కొన్న తేదీన ({date_facts[0].normalized_value}) వ్యక్తిగతంగా న్యాయస్థానం ముందు హాజరు కావాలి."
                    card1_uncertainty = None
                else:
                    action_str = "నోటీసులో కోరిన చర్య: వ్యక్తిగతంగా హాజరు కావాలని ఉంది (నిర్దిష్ట తేదీ పేర్కొనబడలేదు)."
                    card1_uncertainty = "నోటీసులో హాజరు గురించి పేర్కొన్నప్పటికీ, నిర్దిష్ట విచారణ తేదీ స్పష్టంగా కనిపించడం లేదు."
    else:
        what_says = "Document mentions: "
        if case_facts:
            what_says += f"Case {case_facts[0].raw_value}. "
        if date_facts:
            what_says += f"Date: {date_facts[0].raw_value}. "
        if amount_facts:
            what_says += f"Amount: {amount_facts[0].raw_value}. "
        if not date_facts and not amount_facts:
            what_says += f"'{first_block.text_original[:150]}' " if first_block else "Official notice."

        # Case C: Document Authenticity
        what_means = (
            "Based on visible text, this document appears to be a court notice (issuing authority has not been independently verified). "
            if is_court else
            "Based on visible text, this document appears to be an official notice (issuing authority has not been independently verified). "
        )
        if date_facts:
            what_means += f"It lists a date ({date_facts[0].normalized_value}). "
        if amount_facts:
            what_means += f"It references an amount ({amount_facts[0].normalized_value}). "

        if has_conflicting_action:
            card1_status = "conflicting_action"
            action_str = "Conflicting instructions: one passage states action is required, while another passage indicates it is waived or not required."
            card1_uncertainty = "The document contains contradictory instructions. The system cannot determine which instruction governs without legal review."
        elif unreadable_pages and not action_facts:
            unreadable_nums = ", ".join(str(p.page_index) for p in unreadable_pages)
            card1_status = "relevant_page_unreadable"
            action_str = f"Action could not be reliably identified because page {unreadable_nums} is unreadable."
            card1_uncertainty = f"Page {unreadable_nums} is low quality or blurred. Relevant instructions or deadlines may be missing. Please recapture."
        elif not action_facts:
            card1_status = "action_not_identified_in_readable_text" if blocks else "no_action_found"
            action_str = "No action or deadline was identified in the readable text of the document." if blocks else "No action found."
            card1_uncertainty = None
        else:
            act_raw = action_facts[0].normalized_value
            act_lower = act_raw.lower()
            if any(k in act_lower for k in ["not required to appear", "need not appear", "do not appear", "shall not appear", "no need to appear"]):
                card1_status = "action_identified"
                action_str = f"Notice states: {act_raw}"
                card1_uncertainty = None
            elif "may appear" in act_lower or "optional" in act_lower:
                card1_status = "action_identified"
                action_str = f"Notice states optional: {act_raw}"
                card1_uncertainty = None
            elif "failure to appear" in act_lower or "if you fail to appear" in act_lower:
                card1_status = "action_identified"
                action_str = f"Conditional warning: {act_raw}"
                card1_uncertainty = "This is a conditional warning if attendance fails, not a direct command."
            else:
                card1_status = "action_identified"
                if date_facts:
                    action_str = f"{act_raw} (Scheduled for {date_facts[0].normalized_value})"
                    card1_uncertainty = None
                else:
                    action_str = f"{act_raw} (No specific date or deadline identified in text)"
                    card1_uncertainty = "The notice requests appearance, but does not specify a clear date or deadline."

    # Comprehensive Evidence Display: Collect all relevant evidence blocks linking each fact to source text
    proof_refs = []
    seen_block_ids = set()

    if first_block:
        p_num = getattr(first_block, 'page_number', getattr(first_block, 'page_index', 1))
        proof_refs.append({
            "page_number": p_num,
            "block_id": first_block.block_id,
            "bbox": first_block.bbox,
            "text": first_block.text_original
        })
        seen_block_ids.add(first_block.block_id)

    fact_groups_in_priority = [
        total_due_facts,
        due_date_facts,
        action_facts,
        tax_amt_facts,
        fee_facts,
        authority_facts,
        notice_facts,
        recipient_facts,
        address_facts,
        property_facts,
        ay_facts,
        date_facts,
        amount_facts,
        instr_facts,
        warn_facts,
        contact_facts,
        statute_facts,
        case_facts,
    ]
    for grp in fact_groups_in_priority:
        for f in grp:
            if f.evidence_refs:
                for ref in f.evidence_refs:
                    b_id = ref.get("block_id")
                    if b_id and b_id not in seen_block_ids:
                        proof_refs.append(ref)
                        seen_block_ids.add(b_id)

    if has_conflicting_action:
        for b in (pos_blocks + neg_blocks):
            if b.block_id not in seen_block_ids:
                proof_refs.append({
                    "page_number": getattr(b, 'page_number', getattr(b, 'page_index', 1)),
                    "block_id": b.block_id,
                    "bbox": b.bbox,
                    "text": b.text_original
                })
                seen_block_ids.add(b.block_id)

    card1 = ActionCard(
        document_id=document_id,
        title=title_str,
        what_says=what_says.strip(),
        what_means=what_means.strip(),
        what_action=action_str,
        uncertainty=card1_uncertainty,
        proof_refs=proof_refs,
        status=card1_status
    )
    cards.append(card1)

    # Card 2: If Statutory Reference exists
    if statute_facts:
        sf = statute_facts[0]
        verified_info = verify_statutory_reference(sf.raw_value)

        stat_status = "supported" if verified_info["is_verified"] else "uncertain"
        stat_uncertainty = verified_info["disclaimer"]

        if is_te:
            stat_title = f"చట్టపరమైన నిబంధన: {verified_info['canonical_name']}"
            stat_says = f"నోటీసులో పేర్కొన్న సెక్షన్: '{sf.raw_value}'"
            stat_means = verified_info.get("explanation_te", verified_info["explanation_en"])
            stat_action = "చర్య తీసుకునే ముందు అర్హత కలిగిన న్యాయవాదిని సంప్రదించండి."
        else:
            stat_title = f"Legal Reference: {verified_info['canonical_name']}"
            stat_says = f"Notice states: '{sf.raw_value}'"
            stat_means = verified_info["explanation_en"]
            stat_action = "Check the full citation with a qualified legal professional before acting."

        card2 = ActionCard(
            document_id=document_id,
            title=stat_title,
            what_says=stat_says,
            what_means=stat_means,
            what_action=stat_action,
            uncertainty=stat_uncertainty,
            proof_refs=sf.evidence_refs,
            status=stat_status
        )
        cards.append(card2)

    return cards

def answer_user_question(
    db: Session,
    document_id: str,
    question_text: str,
    user_context: Optional[str] = None,
    language: str = "te-IN",
    allow_english_audio: bool = False,
    has_cloud_consent: bool = False
) -> Dict[str, Any]:
    """
    Context Cross-Check Question Answering Engine:
    - Rejects prompt injections and out-of-bounds legal advice requests
    - Retrieves verified text blocks belonging strictly to document_id
    - Evaluates user context separately without treating it as document evidence
    - Categorizes answers into typed statuses: supported, uncertain, conflicting, not_found
    - Provides 8-step regional translations with protected tokens
    - Strictly adheres to Monoglot Safety: Telugu users NEVER receive unprompted English speech!
    """
    from backend.modules.retrieval.service import retrieve_relevant_blocks

    all_blocks = db.query(TextBlock).filter(TextBlock.document_id == document_id).all()
    facts = db.query(ExtractedFact).filter(ExtractedFact.document_id == document_id).all()
    is_te = language.startswith("te")

    # 1. Out-of-bounds legal advice check
    oob_check = check_out_of_bounds_legal_question(question_text)
    if oob_check:
        abstain_text = oob_check["summary_te"] if is_te else oob_check["summary_en"]
        advice_text = "చట్టపరమైన సలహా కోసం అర్హత కలిగిన న్యాయవాదిని లేదా న్యాయ సేవాధికార సంస్థను సంప్రదించండి." if is_te else "Consult an advocate or legal aid service for legal advice."
        disclaimer_text = oob_check.get("disclaimer_te", oob_check["summary_te"]) if is_te else oob_check.get("disclaimer_en", oob_check["summary_en"])
        return {
            "answer_status": "unsupported",
            "summary_text": abstain_text,
            "approved_spoken_output": abstain_text,
            "is_translation_verified": True,
            "translation_provider": "grounded_legal_safety",
            "disclaimer": disclaimer_text,
            "claims": [
                {
                    "claim_id": "c_oob",
                    "claim_text": abstain_text,
                    "status": "supported",
                    "evidence": []
                }
            ],
            "action_advice": advice_text,
            "uncertainties": ["Legal outcome cannot be predicted from notice text."],
            "user_context_check": None,
            "original_extracted_text": ""
        }

    # 2. Context Cross-Check (isolated user notes)
    context_report = None
    if user_context:
        context_report = cross_check_user_context(user_context, all_blocks)

    q_lower = question_text.lower()
    is_amount_q = any(k in q_lower for k in ["amount", "money", "fee", "rupee", "how much", "cost", "మొత్తం", "రూపాయలు", "ఎంత"])

    # 2.5 Obligation, Waiver, Cancellation & Contradictory Instruction Interception (Case F & Semantics)
    neg_blocks = [
        b for b in all_blocks
        if any(k in b.text_original.lower() for k in [
            "waived", "waiver", "not required", "need not", "cancelled", "canceled",
            "dismissed", "exempted", "exemption", "withdrawn", "withdrawal", "rescinded",
            "payment is waived", "penalty is cancelled", "demand is withdrawn",
            "hereby waived", "endorsement:"
        ])
    ]
    pos_blocks = [
        b for b in all_blocks
        if b not in neg_blocks and any(k in b.text_original.lower() for k in [
            "required to pay", "must pay", "must appear", "appear in person without fail",
            "appear in person", "penalty of", "payment required", "pay the penalty",
            "amount due", "demand:", "summons to appear", "directed to pay", "ordered to pay",
            "payment is due", "you are required", "demand notice", "tax is due", "tax for the",
            "total amount due", "please make the payment"
        ])
    ]
    has_conflict = bool(pos_blocks and neg_blocks)

    is_waiver_content_q = any(phrase in q_lower for phrase in [
        "what does the waiver", "what does the endorsement say", "what does the endorsement state",
        "waiver endorsement say", "waiver passage say", "endorsement say", "cancellation clause say",
        "what does the waiver say", "what does the cancellation say",
        "ఎండార్స్‌మెంట్ ఏమి చెబుతోంది", "మినహాయింపు ఏమి చెబుతోంది"
    ])

    is_enforceability_or_waiver_q = (
        any(phrase in q_lower for phrase in [
            "waived", "waiver", "cancelled", "canceled", "withdrawn", "withdrawal",
            "dismissed", "rescinded", "remitted",
            "still have to pay", "still pay", "still due", "amount still due",
            "do i have to pay", "do i still have to pay", "must i pay", "have to pay",
            "still need to pay", "do i need to pay", "need to pay", "penalty cancelled",
            "demand been withdrawn", "is the penalty cancelled", "demand withdrawn",
            "is the demand withdrawn", "is the amount still due", "payment been waived",
            "has the payment been waived", "has payment been waived",
            "రద్దు చేయబడిందా", "మినహాయింపు ఉందా", "చెల్లించాలా", "ఇంకా చెల్లించాలా"
        ]) or (
            any(act in q_lower for act in ["action should i take", "action regarding payment", "action to take", "what action", "what should i do", "what to do", "ఏమి చేయాలి", "చర్య"])
            and any(pay in q_lower for pay in ["pay", "payment", "penalty", "demand", "చెల్లింపు", "రుసుము"])
        )
    )

    if is_waiver_content_q:
        if has_conflict:
            w_b = neg_blocks[0]
            d_b = pos_blocks[0]
            w_p = getattr(w_b, 'page_number', getattr(w_b, 'page_index', 1))
            d_p = getattr(d_b, 'page_number', getattr(d_b, 'page_index', 1))
            msg_en = (
                f"The endorsement states: '{w_b.text_original[:140]}'. "
                f"However, the document also contains a contradictory demand: '{d_b.text_original[:140]}'. "
                "Because these instructions conflict, neither command can be confirmed as superseding the other without legal verification."
            )
            msg_te = (
                f"ఎండార్స్‌మెంట్‌లో పేర్కొనబడింది: '{w_b.text_original[:140]}'. "
                f"అయితే, పత్రంలో పరస్పర విరుద్ధమైన డిమాండ్ కూడా ఉంది: '{d_b.text_original[:140]}'. "
                "ఈ రెండు ఆదేశాల మధ్య వైరుధ్యం ఉన్నందున, న్యాయ సలహా లేకుండా ఒకదానిని ఖరారు చేయలేము."
            )
            claims = [
                {
                    "claim_id": "c_waiver_passage",
                    "claim_text": f"The endorsement states: {w_b.text_original[:140]}",
                    "status": "supported",
                    "evidence": [{"page_number": w_p, "block_id": w_b.block_id, "bbox": w_b.bbox, "text": w_b.text_original[:140]}]
                },
                {
                    "claim_id": "c_demand_passage",
                    "claim_text": f"Contradictory demand noted: {d_b.text_original[:140]}",
                    "status": "conflicting",
                    "evidence": [{"page_number": d_p, "block_id": d_b.block_id, "bbox": d_b.bbox, "text": d_b.text_original[:140]}]
                }
            ]
            return {
                "answer_status": "supported",
                "summary_text": msg_te if is_te else msg_en,
                "approved_spoken_output": msg_te if is_te else msg_en,
                "is_translation_verified": True,
                "translation_provider": "grounded_conflict_resolver",
                "claims": claims,
                "uncertainties": ["Document contains both a demand and a contradictory waiver endorsement."],
                "user_context_check": context_report,
                "original_extracted_text": f"Endorsement: {w_b.text_original[:100]}; Demand: {d_b.text_original[:100]}"
            }
        elif neg_blocks:
            w_b = neg_blocks[0]
            w_p = getattr(w_b, 'page_number', getattr(w_b, 'page_index', 1))
            msg_en = f"The waiver endorsement states: '{w_b.text_original[:160]}'."
            msg_te = f"మినహాయింపు ఎండార్స్‌మెంట్‌లో ఇలా పేర్కొనబడింది: '{w_b.text_original[:160]}'."
            claims = [
                {
                    "claim_id": "c_waiver_passage",
                    "claim_text": msg_en,
                    "status": "supported",
                    "evidence": [{"page_number": w_p, "block_id": w_b.block_id, "bbox": w_b.bbox, "text": w_b.text_original[:160]}]
                }
            ]
            return {
                "answer_status": "supported",
                "summary_text": msg_te if is_te else msg_en,
                "approved_spoken_output": msg_te if is_te else msg_en,
                "is_translation_verified": True,
                "translation_provider": "grounded_legal_facts",
                "claims": claims,
                "uncertainties": [],
                "user_context_check": context_report,
                "original_extracted_text": w_b.text_original[:160]
            }
        else:
            msg_en = "I could not find a waiver endorsement or cancellation clause in the readable text of this document."
            msg_te = "ఈ పత్రంలో మినహాయింపు ఎండార్స్‌మెంట్ లేదా రద్దు నిబంధన కనిపించలేదు."
            return {
                "answer_status": "not_found",
                "summary_text": msg_te if is_te else msg_en,
                "approved_spoken_output": msg_te if is_te else msg_en,
                "is_translation_verified": True,
                "translation_provider": "grounded_template",
                "claims": [],
                "uncertainties": ["No waiver or endorsement clause found in document blocks."],
                "user_context_check": context_report,
                "original_extracted_text": ""
            }

    if is_enforceability_or_waiver_q:
        if has_conflict:
            msg_en = "The document contains conflicting instructions: one passage states action/payment is required, while another passage indicates it is waived or not required."
            msg_te = "పత్రంలో పరస్పర విరుద్ధమైన ఆదేశాలు ఉన్నాయి: ఒక భాగంలో చర్య లేదా చెల్లింపు తప్పనిసరి అని, మరో భాగంలో మినహాయింపు లేదా రద్దు ఉందని పేర్కొనబడింది. న్యాయ సలహా లేకుండా నిర్ధారించలేము."
            claims = [
                {
                    "claim_id": f"c_conflict_{idx}",
                    "claim_text": b.text_original[:120],
                    "status": "conflicting",
                    "evidence": [{"page_number": getattr(b, 'page_number', getattr(b, 'page_index', 1)), "block_id": b.block_id, "bbox": b.bbox, "text": b.text_original[:120]}]
                }
                for idx, b in enumerate((pos_blocks + neg_blocks)[:4])
            ]
            return {
                "answer_status": "conflicting",
                "summary_text": msg_te if is_te else msg_en,
                "approved_spoken_output": msg_te if is_te else msg_en,
                "is_translation_verified": True,
                "translation_provider": "grounded_conflict_resolver",
                "claims": claims,
                "uncertainties": ["Conflicting instructions identified between document passages."],
                "user_context_check": context_report,
                "original_extracted_text": "; ".join([b.text_original[:100] for b in (pos_blocks + neg_blocks)[:2]])
            }
        elif pos_blocks:
            d_b = pos_blocks[0]
            d_p = getattr(d_b, 'page_number', getattr(d_b, 'page_index', 1))
            if any(w in q_lower for w in ["waived", "waiver", "cancelled", "canceled", "withdrawn", "withdrawal", "dismissed"]):
                msg_en = f"The document requires payment: '{d_b.text_original[:140]}'. No waiver, cancellation, or withdrawal endorsement was identified in the readable text."
                msg_te = f"పత్రం ప్రకారం చెల్లింపు తప్పనిసరి: '{d_b.text_original[:140]}'. ఎటువంటి మినహాయింపు లేదా రద్దు పేర్కొనబడలేదు."
            else:
                msg_en = f"The document indicates that payment is required: '{d_b.text_original[:140]}'. No waiver or cancellation was identified."
                msg_te = f"పత్రం ప్రకారం చెల్లింపు చేయవలసి ఉంటుంది: '{d_b.text_original[:140]}'. ఎటువంటి మినహాయింపు లేదు."
            claims = [
                {
                    "claim_id": "c_demand_only",
                    "claim_text": msg_en,
                    "status": "supported",
                    "evidence": [{"page_number": d_p, "block_id": d_b.block_id, "bbox": d_b.bbox, "text": d_b.text_original[:140]}]
                }
            ]
            return {
                "answer_status": "supported",
                "summary_text": msg_te if is_te else msg_en,
                "approved_spoken_output": msg_te if is_te else msg_en,
                "is_translation_verified": True,
                "translation_provider": "grounded_legal_facts",
                "claims": claims,
                "uncertainties": [],
                "user_context_check": context_report,
                "original_extracted_text": d_b.text_original[:140]
            }
        elif neg_blocks:
            w_b = neg_blocks[0]
            w_p = getattr(w_b, 'page_number', getattr(w_b, 'page_index', 1))
            if any(w in q_lower for w in ["waived", "waiver", "cancelled", "canceled", "withdrawn", "withdrawal", "dismissed"]):
                msg_en = f"The document indicates that payment is waived/cancelled: '{w_b.text_original[:140]}'."
                msg_te = f"పత్రం ప్రకారం చెల్లింపు మినహాయించబడింది/రద్దు చేయబడింది: '{w_b.text_original[:140]}'."
            else:
                msg_en = f"The document indicates that payment is not required: '{w_b.text_original[:140]}'."
                msg_te = f"పత్రం ప్రకారం చెల్లింపు చేయవలసిన అవసరం లేదు: '{w_b.text_original[:140]}'."
            claims = [
                {
                    "claim_id": "c_waiver_only",
                    "claim_text": msg_en,
                    "status": "supported",
                    "evidence": [{"page_number": w_p, "block_id": w_b.block_id, "bbox": w_b.bbox, "text": w_b.text_original[:140]}]
                }
            ]
            return {
                "answer_status": "supported",
                "summary_text": msg_te if is_te else msg_en,
                "approved_spoken_output": msg_te if is_te else msg_en,
                "is_translation_verified": True,
                "translation_provider": "grounded_legal_facts",
                "claims": claims,
                "uncertainties": [],
                "user_context_check": context_report,
                "original_extracted_text": w_b.text_original[:140]
            }
        else:
            if any(w in q_lower for w in ["waived", "waiver", "cancelled", "canceled", "withdrawn", "withdrawal"]):
                msg_en = "I could not find information regarding a payment waiver or cancellation in the readable text of this document."
                msg_te = "ఈ పత్రంలో చెల్లింపు మినహాయింపు లేదా రద్దు గురించిన వివరాలు కనిపించలేదు."
                return {
                    "answer_status": "unsupported",
                    "summary_text": msg_te if is_te else msg_en,
                    "approved_spoken_output": msg_te if is_te else msg_en,
                    "is_translation_verified": True,
                    "translation_provider": "grounded_template",
                    "claims": [],
                    "uncertainties": ["No waiver or demand instructions identified in document text."],
                    "user_context_check": context_report,
                    "original_extracted_text": ""
                }

    # 3. Targeted Fact Retrieval: Date questions
    if not is_amount_q and any(k in q_lower for k in ["date", "when", "time", "deadline", "due date", "last date", "తేదీ", "ఎప్పుడు", "గడువు", "చివరి తేదీ"]):
        due_date_facts = [f for f in facts if f.field_type == "payment_due_date" or (f.field_type == "date" and f.reason_code == "payment_due_date")]
        issue_date_facts = [f for f in facts if f.field_type == "issue_date" or (f.field_type == "date" and f.reason_code == "issue_date")]
        other_date_facts = [f for f in facts if f.field_type == "date" and f.reason_code not in ["payment_due_date", "issue_date"]]
        all_date_facts = [f for f in facts if f.field_type in ["date", "payment_due_date", "issue_date"]]

        if due_date_facts and any(k in q_lower for k in ["deadline", "due date", "last date", "when to pay", "pay by", "గడువు", "చివరి", "ఎప్పటిలోగా", "ఎప్పుడు"]):
            # Specific deadline question
            df = due_date_facts[0]
            claim_text = f"The payment deadline mentioned in the document is {df.normalized_value}."
            expl = translation_service.generate_explanation(
                original_text=df.raw_value,
                facts=[{"date": df.normalized_value}],
                simplified_en=claim_text,
                target_language=language,
                allow_english_audio=allow_english_audio,
                has_cloud_consent=has_cloud_consent
            )
            if is_te and not expl.is_translation_verified:
                expl.regional_translation = f"నోటీసులో పేర్కొన్న చెల్లింపు చివరి గడువు {df.normalized_value}."
                expl.is_translation_verified = True
                expl.approved_spoken_output = expl.regional_translation

            draft_claims = [
                {
                    "claim_id": "c_due_date_1",
                    "claim_text": claim_text,
                    "status": df.status,
                    "evidence": df.evidence_refs
                }
            ]
            report = validate_claims_and_evidence(draft_claims, document_id, all_blocks)
            return {
                "answer_status": "supported" if report.is_valid else "uncertain",
                "summary_text": expl.regional_translation if expl.is_translation_verified else expl.simplified_explanation,
                "approved_spoken_output": expl.approved_spoken_output,
                "is_translation_verified": expl.is_translation_verified,
                "translation_provider": expl.translation_provider_name,
                "disclaimer": expl.to_dict().get("disclaimer"),
                "claims": report.all_claims(),
                "uncertainties": report.conflicts,
                "user_context_check": context_report,
                "original_extracted_text": df.raw_value
            }

        elif issue_date_facts and any(k in q_lower for k in ["issued", "issue date", "notice date", "జారీ"]):
            # Specific notice date question
            df = issue_date_facts[0]
            claim_text = f"The document was issued on {df.normalized_value}."
            expl = translation_service.generate_explanation(
                original_text=df.raw_value,
                facts=[{"date": df.normalized_value}],
                simplified_en=claim_text,
                target_language=language,
                allow_english_audio=allow_english_audio,
                has_cloud_consent=has_cloud_consent
            )
            if is_te and not expl.is_translation_verified:
                expl.regional_translation = f"నోటీసు జారీ చేసిన తేదీ {df.normalized_value}."
                expl.is_translation_verified = True
                expl.approved_spoken_output = expl.regional_translation

            draft_claims = [
                {
                    "claim_id": "c_issue_date_1",
                    "claim_text": claim_text,
                    "status": df.status,
                    "evidence": df.evidence_refs
                }
            ]
            report = validate_claims_and_evidence(draft_claims, document_id, all_blocks)
            return {
                "answer_status": "supported" if report.is_valid else "uncertain",
                "summary_text": expl.regional_translation if expl.is_translation_verified else expl.simplified_explanation,
                "approved_spoken_output": expl.approved_spoken_output,
                "is_translation_verified": expl.is_translation_verified,
                "translation_provider": expl.translation_provider_name,
                "disclaimer": expl.to_dict().get("disclaimer"),
                "claims": report.all_claims(),
                "uncertainties": report.conflicts,
                "user_context_check": context_report,
                "original_extracted_text": df.raw_value
            }

        elif issue_date_facts and due_date_facts:
            # Both issue date and due date exist
            idf = issue_date_facts[0]
            ddf = due_date_facts[0]
            claim_text = f"The document was issued on {idf.normalized_value} and specifies a payment deadline of {ddf.normalized_value}."
            summary_te = f"నోటీసు తేదీ {idf.normalized_value}, మరియు చెల్లింపు చివరి గడువు {ddf.normalized_value}."
            combined_evidence = idf.evidence_refs + ddf.evidence_refs

            draft_claims = [
                {
                    "claim_id": "c_dates_both",
                    "claim_text": claim_text,
                    "status": "supported",
                    "evidence": combined_evidence
                }
            ]
            report = validate_claims_and_evidence(draft_claims, document_id, all_blocks)
            return {
                "answer_status": "supported" if report.is_valid else "uncertain",
                "summary_text": summary_te if is_te else claim_text,
                "approved_spoken_output": summary_te if is_te else claim_text,
                "is_translation_verified": True,
                "translation_provider": "grounded_legal_facts",
                "claims": report.all_claims(),
                "uncertainties": [],
                "user_context_check": context_report,
                "original_extracted_text": f"Date: {idf.raw_value}; Deadline: {ddf.raw_value}"
            }

        elif all_date_facts:
            # Check for multiple conflicting dates with the same role
            unique_dates = list({df.normalized_value for df in all_date_facts})
            if len(unique_dates) > 1 and not (issue_date_facts or due_date_facts):
                summary_en = f"The document mentions multiple conflicting dates: {', '.join(unique_dates)}."
                claims = [
                    {
                        "claim_id": f"c_date_{idx}",
                        "claim_text": f"Date noted: {df.normalized_value}",
                        "status": "conflicting",
                        "evidence": df.evidence_refs
                    }
                    for idx, df in enumerate(all_date_facts)
                ]

                expl = translation_service.generate_explanation(
                    original_text=", ".join([df.raw_value for df in all_date_facts]),
                    facts=[{"date": df.normalized_value} for df in all_date_facts],
                    simplified_en=summary_en,
                    target_language=language,
                    allow_english_audio=allow_english_audio,
                    has_cloud_consent=has_cloud_consent
                )

                if is_te and not expl.is_translation_verified:
                    expl.regional_translation = f"పత్రంలో వేర్వేరు తేదీలు ప్రస్తావించబడ్డాయి: {', '.join(unique_dates)}. వీటిలో వైరుధ్యం ఉంది."
                    expl.is_translation_verified = True
                    expl.approved_spoken_output = expl.regional_translation

                return {
                    "answer_status": "conflicting",
                    "summary_text": expl.regional_translation if expl.is_translation_verified else expl.simplified_explanation,
                    "approved_spoken_output": expl.approved_spoken_output,
                    "is_translation_verified": expl.is_translation_verified,
                    "translation_provider": expl.translation_provider_name,
                    "disclaimer": expl.to_dict().get("disclaimer"),
                    "claims": claims,
                    "uncertainties": [f"Conflicting dates: {', '.join(unique_dates)}"],
                    "user_context_check": context_report,
                    "original_extracted_text": ", ".join([df.raw_value for df in all_date_facts])
                }

            df = all_date_facts[0]
            claim_text = f"The date mentioned in the document is {df.normalized_value}."
            expl = translation_service.generate_explanation(
                original_text=df.raw_value,
                facts=[{"date": df.normalized_value}],
                simplified_en=claim_text,
                target_language=language,
                allow_english_audio=allow_english_audio,
                has_cloud_consent=has_cloud_consent
            )

            draft_claims = [
                {
                    "claim_id": "c_date_1",
                    "claim_text": claim_text,
                    "status": df.status,
                    "evidence": df.evidence_refs
                }
            ]
            report = validate_claims_and_evidence(draft_claims, document_id, all_blocks)
            return {
                "answer_status": "supported" if report.is_valid else "uncertain",
                "summary_text": expl.regional_translation if expl.is_translation_verified else expl.simplified_explanation,
                "approved_spoken_output": expl.approved_spoken_output,
                "is_translation_verified": expl.is_translation_verified,
                "translation_provider": expl.translation_provider_name,
                "disclaimer": expl.to_dict().get("disclaimer"),
                "claims": report.all_claims(),
                "uncertainties": report.conflicts,
                "user_context_check": context_report,
                "original_extracted_text": df.raw_value
            }
        else:
            msg_en = "I could not find a specific date or deadline in the readable text of this document."
            msg_te = translate_phrase("date_unclear", "te-IN")
            return {
                "answer_status": "not_found",
                "summary_text": msg_te if is_te else msg_en,
                "approved_spoken_output": msg_te if is_te else msg_en,
                "is_translation_verified": True,
                "translation_provider": "grounded_template",
                "claims": [],
                "uncertainties": ["No date found in extracted document blocks."],
                "user_context_check": context_report,
                "original_extracted_text": ""
            }

    # 4. Targeted Fact Retrieval: Required Action & Conflicting Instructions (Cases B, D, E, F)
    is_action_q = any(k in q_lower for k in ["action", "what to do", "ask me", "should i do", "should i take", "take regarding", "ఏమి చేయాలి", "చర్య"])
    if is_action_q:
        # Check conflicting action instructions (Case F)
        pos_blocks = [b for b in all_blocks if any(k in b.text_original.lower() for k in ["required to pay", "must pay", "must appear", "appear in person without fail", "appear in person", "penalty of", "demanded", "payment required"])]
        neg_blocks = [b for b in all_blocks if any(k in b.text_original.lower() for k in ["waived", "not required", "need not", "cancelled", "dismissed", "exempted", "payment is waived", "penalty is cancelled"])]
        if pos_blocks and neg_blocks:
            msg_en = "The document contains conflicting instructions: one passage states action/payment is required, while another passage indicates it is waived or not required."
            msg_te = "పత్రంలో పరస్పర విరుద్ధమైన ఆదేశాలు ఉన్నాయి: ఒక భాగంలో చర్య లేదా చెల్లింపు తప్పనిసరి అని, మరో భాగంలో మినహాయింపు ఉందని పేర్కొనబడింది. న్యాయ సలహా లేకుండా నిర్ధారించలేము."
            claims = [
                {
                    "claim_id": f"c_conflict_{idx}",
                    "claim_text": b.text_original[:120],
                    "status": "conflicting",
                    "evidence": [{"page_number": getattr(b, 'page_number', getattr(b, 'page_index', 1)), "block_id": b.block_id, "bbox": b.bbox, "text": b.text_original[:120]}]
                }
                for idx, b in enumerate((pos_blocks + neg_blocks)[:4])
            ]
            return {
                "answer_status": "conflicting",
                "summary_text": msg_te if is_te else msg_en,
                "approved_spoken_output": msg_te if is_te else msg_en,
                "is_translation_verified": True,
                "translation_provider": "grounded_conflict_resolver",
                "claims": claims,
                "uncertainties": ["Conflicting instructions identified between document passages."],
                "user_context_check": context_report,
                "original_extracted_text": "; ".join([b.text_original[:100] for b in (pos_blocks + neg_blocks)[:2]])
            }

        # Check incomplete OCR / unreadable page (Case D)
        pages = db.query(DocumentPage).filter(DocumentPage.document_id == document_id).all()
        unreadable_pages = [p for p in pages if p.quality_state in ["BLURRED", "CROPPED", "CROPPED_EDGE", "LOW_RES", "LOW_RESOLUTION", "UNREADABLE"]]

        action_facts = [f for f in facts if f.field_type == "required_action"]
        if unreadable_pages and not action_facts:
            unreadable_nums = ", ".join(str(p.page_index) for p in unreadable_pages)
            msg_en = f"An action or deadline could not be reliably identified because page {unreadable_nums} of the document is unreadable. Please take a clearer photo."
            msg_te = f"పత్రంలోని పేజీ {unreadable_nums} అస్పష్టంగా ఉండడం వల్ల చర్య లేదా గడువును నిర్ధారించలేము. దయచేసి స్పష్టమైన ఫోటో తీయండి."
            return {
                "answer_status": "uncertain",
                "summary_text": msg_te if is_te else msg_en,
                "approved_spoken_output": msg_te if is_te else msg_en,
                "is_translation_verified": True,
                "translation_provider": "grounded_quality_safeguard",
                "claims": [],
                "uncertainties": [f"Page {unreadable_nums} is unreadable; action completeness cannot be established."],
                "user_context_check": context_report,
                "original_extracted_text": ""
            }

        if action_facts:
            act_text = f"The document states: {action_facts[0].normalized_value}"
            expl = translation_service.generate_explanation(
                original_text=action_facts[0].raw_value,
                facts=[{"action": action_facts[0].normalized_value}],
                simplified_en=act_text,
                target_language=language,
                allow_english_audio=allow_english_audio,
                has_cloud_consent=has_cloud_consent
            )

            draft_claims = [
                {
                    "claim_id": "c_act_1",
                    "claim_text": act_text,
                    "status": "supported",
                    "evidence": action_facts[0].evidence_refs
                }
            ]
            report = validate_claims_and_evidence(draft_claims, document_id, all_blocks)
            return {
                "answer_status": "supported" if report.is_valid else "uncertain",
                "summary_text": expl.regional_translation if expl.is_translation_verified else expl.simplified_explanation,
                "approved_spoken_output": expl.approved_spoken_output,
                "is_translation_verified": expl.is_translation_verified,
                "translation_provider": expl.translation_provider_name,
                "disclaimer": expl.to_dict().get("disclaimer"),
                "claims": report.all_claims(),
                "uncertainties": [],
                "user_context_check": context_report,
                "original_extracted_text": action_facts[0].raw_value
            }
        else:
            msg_en = "No required action or deadline was identified in the readable text of this document."
            msg_te = "చదవగలిగిన పూర్తి పత్రంలో ఎటువంటి నిర్దిష్ట చర్య లేదా గడువు పేర్కొనబడలేదు."
            return {
                "answer_status": "no_action_found",
                "summary_text": msg_te if is_te else msg_en,
                "approved_spoken_output": msg_te if is_te else msg_en,
                "is_translation_verified": True,
                "translation_provider": "grounded_template",
                "claims": [],
                "uncertainties": [],
                "user_context_check": context_report,
                "original_extracted_text": ""
            }

    # 5. Targeted Fact Retrieval: Payment Instructions ("How to pay")
    if any(k in q_lower for k in [
        "how to pay", "how can i pay", "how do i pay", "payment method", "payment instruction",
        "where to pay", "pay online", "how pay", "ఎలా చెల్లించాలి", "చెల్లింపు మార్గాలు", "ఎక్కడ చెల్లించాలి"
    ]):
        instr_facts = [f for f in facts if f.field_type == "payment_instructions"]
        if instr_facts:
            inf = instr_facts[0]
            claim_text = f"Payment can be made through: {inf.normalized_value}."
            summary_te = f"చెల్లింపు విధానం: {inf.normalized_value}."
            draft_claims = [
                {
                    "claim_id": "c_pay_instr_1",
                    "claim_text": claim_text,
                    "status": "supported",
                    "evidence": inf.evidence_refs
                }
            ]
            report = validate_claims_and_evidence(draft_claims, document_id, all_blocks)
            return {
                "answer_status": "supported" if report.is_valid else "uncertain",
                "summary_text": summary_te if is_te else claim_text,
                "approved_spoken_output": summary_te if is_te else claim_text,
                "is_translation_verified": True,
                "translation_provider": "grounded_legal_facts",
                "claims": report.all_claims(),
                "uncertainties": [],
                "user_context_check": context_report,
                "original_extracted_text": inf.raw_value
            }

    # 6. Targeted Fact Retrieval: Amount questions
    if not is_action_q and (
        any(k in q_lower for k in ["amount", "money", "fee", "rupee", "how much", "మొత్తం", "రూపాయలు", "ఎంత"]) or (
            ("pay" in q_lower or "చెల్లించ" in q_lower) and not any(m in q_lower for m in ["how", "where", "method", "online", "mode", "action", "should", "take", "ఏమి", "ఎలా", "ఎక్కడ", "చర్య"])
        )
    ):
        total_due_facts = [f for f in facts if f.field_type == "total_amount_due"]
        tax_amt_facts = [f for f in facts if f.field_type == "tax_amount"]
        fee_facts = [f for f in facts if f.field_type == "fee_penalty"]
        amount_facts = [f for f in facts if f.field_type == "amount"]

        if total_due_facts:
            tdf = total_due_facts[0]
            claim_text = f"The total amount due is {tdf.normalized_value}."
            summary_te = f"పత్రంలో పేర్కొన్న మొత్తం చెల్లించవలసిన బకాయి {tdf.normalized_value}."

            # Add breakdown if available
            if tax_amt_facts:
                claim_text += f" (Property Tax: {tax_amt_facts[0].normalized_value}"
                summary_te += f" (ఆస్తి పన్ను: {tax_amt_facts[0].normalized_value}"
                if fee_facts:
                    fees_str = ", ".join([f"{f.raw_value}: {f.normalized_value}" for f in fee_facts[:3]])
                    claim_text += f", Cesses/Fees: {fees_str}"
                claim_text += ")"
                summary_te += ")"

            all_amount_evidence = tdf.evidence_refs.copy()
            for extra in (tax_amt_facts + fee_facts):
                if extra.evidence_refs:
                    all_amount_evidence.extend(extra.evidence_refs)

            draft_claims = [
                {
                    "claim_id": "c_total_due_1",
                    "claim_text": claim_text,
                    "status": "supported",
                    "evidence": all_amount_evidence
                }
            ]
            report = validate_claims_and_evidence(draft_claims, document_id, all_blocks)
            return {
                "answer_status": "supported" if report.is_valid else "uncertain",
                "summary_text": summary_te if is_te else claim_text,
                "approved_spoken_output": summary_te if is_te else claim_text,
                "is_translation_verified": True,
                "translation_provider": "grounded_legal_facts",
                "claims": report.all_claims(),
                "uncertainties": [],
                "user_context_check": context_report,
                "original_extracted_text": tdf.raw_value
            }

        elif amount_facts:
            af = amount_facts[0]
            claim_text = f"The document specifies an amount of {af.normalized_value}."
            expl = translation_service.generate_explanation(
                original_text=af.raw_value,
                facts=[{"amount": af.normalized_value}],
                simplified_en=claim_text,
                target_language=language,
                allow_english_audio=allow_english_audio,
                has_cloud_consent=has_cloud_consent
            )

            draft_claims = [
                {
                    "claim_id": "c_amt_1",
                    "claim_text": claim_text,
                    "status": af.status,
                    "evidence": af.evidence_refs
                }
            ]
            report = validate_claims_and_evidence(draft_claims, document_id, all_blocks)
            return {
                "answer_status": "supported" if report.is_valid else "uncertain",
                "summary_text": expl.regional_translation if expl.is_translation_verified else expl.simplified_explanation,
                "approved_spoken_output": expl.approved_spoken_output,
                "is_translation_verified": expl.is_translation_verified,
                "translation_provider": expl.translation_provider_name,
                "disclaimer": expl.to_dict().get("disclaimer"),
                "claims": report.all_claims(),
                "uncertainties": [],
                "user_context_check": context_report,
                "original_extracted_text": af.raw_value
            }
        else:
            msg_en = "I could not find an amount or payment sum in the readable text of this document."
            msg_te = "ఈ పత్రంలో నిర్దిష్ట మొత్తం లేదా నగదు వివరాలు కనిపించలేదు."
            return {
                "answer_status": "unsupported",
                "summary_text": msg_te if is_te else msg_en,
                "approved_spoken_output": msg_te if is_te else msg_en,
                "is_translation_verified": True,
                "translation_provider": "grounded_template",
                "claims": [],
                "uncertainties": ["No currency amount found in document."],
                "user_context_check": context_report,
                "original_extracted_text": ""
            }

    # 6. Targeted Fact Retrieval: Recipient & Property details
    if any(k in q_lower for k in ["recipient", "who is", "property id", "account", "address", "whom", "owner", "ఎవరికి", "పేరు", "ప్రాపర్టీ"]):
        rec_facts = [f for f in facts if f.field_type == "recipient_name"]
        prop_facts = [f for f in facts if f.field_type == "property_id"]
        ay_facts = [f for f in facts if f.field_type == "assessment_year"]
        addr_facts = [f for f in facts if f.field_type == "recipient_address"]
        if rec_facts or prop_facts:
            parts_en = []
            parts_te = []
            ev_list = []
            if rec_facts:
                parts_en.append(f"Recipient: {rec_facts[0].normalized_value}")
                parts_te.append(f"గ్రహీత: {rec_facts[0].normalized_value}")
                if rec_facts[0].evidence_refs:
                    ev_list.extend(rec_facts[0].evidence_refs)
            if addr_facts:
                parts_en.append(f"Address: {addr_facts[0].raw_value}")
                parts_te.append(f"చిరునామా: {addr_facts[0].raw_value}")
                if addr_facts[0].evidence_refs:
                    ev_list.extend(addr_facts[0].evidence_refs)
            if prop_facts:
                parts_en.append(f"Property ID: {prop_facts[0].normalized_value}")
                parts_te.append(f"ప్రాపర్టీ ఐడీ: {prop_facts[0].normalized_value}")
                if prop_facts[0].evidence_refs:
                    ev_list.extend(prop_facts[0].evidence_refs)
            if ay_facts:
                parts_en.append(f"Assessment Year: {ay_facts[0].normalized_value}")
                parts_te.append(f"అసెస్మెంట్ సంవత్సరం: {ay_facts[0].normalized_value}")
                if ay_facts[0].evidence_refs:
                    ev_list.extend(ay_facts[0].evidence_refs)

            claim_text = ". ".join(parts_en) + "."
            summary_te = ". ".join(parts_te) + "."
            draft_claims = [
                {
                    "claim_id": "c_rec_prop_1",
                    "claim_text": claim_text,
                    "status": "supported",
                    "evidence": ev_list
                }
            ]
            report = validate_claims_and_evidence(draft_claims, document_id, all_blocks)
            return {
                "answer_status": "supported" if report.is_valid else "uncertain",
                "summary_text": summary_te if is_te else claim_text,
                "approved_spoken_output": summary_te if is_te else claim_text,
                "is_translation_verified": True,
                "translation_provider": "grounded_legal_facts",
                "claims": report.all_claims(),
                "uncertainties": [],
                "user_context_check": context_report,
                "original_extracted_text": rec_facts[0].raw_value if rec_facts else prop_facts[0].raw_value
            }

    # 8. Targeted Fact Retrieval: Statutory reference & Section questions
    if any(k in q_lower for k in ["section", "statute", "act", "law", "సెక్షన్", "చట్టం"]):
        statute_facts = [f for f in facts if f.field_type in ["statutory_provision", "statutory_reference"]]
        if statute_facts:
            sf = statute_facts[0]
            stat_check = verify_statutory_reference(sf.raw_value)

            if stat_check["is_verified"]:
                summary_en = f"The notice references {stat_check['canonical_name']} under {stat_check['jurisdiction']}. {stat_check['explanation_en']}"
                summary_te = f"ఈ పత్రం {stat_check['canonical_name']}ను ప్రస్తావిస్తుంది. {stat_check['explanation_te']}"
            else:
                summary_en = f"The notice mentions '{sf.raw_value}'. NoticeSaathi reports visible notice text only."
                summary_te = f"పత్రంలో '{sf.raw_value}' అని పేర్కొనబడింది. పత్రంలో కనిపించే సమాచారం మాత్రమే నివేదించబడుతుంది."

            disclaimer_text = stat_check.get("disclaimer") or (
                "NoticeSaathi explains readable document contents only and does not provide legal advice or statutory interpretation. Consult an advocate."
            )

            draft_claims = [
                {
                    "claim_id": "c_stat_1",
                    "claim_text": sf.raw_value,
                    "status": "supported",
                    "evidence": sf.evidence_refs
                }
            ]
            report = validate_claims_and_evidence(draft_claims, document_id, all_blocks)
            return {
                "answer_status": "supported" if report.is_valid else "uncertain",
                "summary_text": summary_te if is_te else summary_en,
                "approved_spoken_output": summary_te if is_te else summary_en,
                "is_translation_verified": True,
                "translation_provider": "grounded_statutory_registry",
                "disclaimer": disclaimer_text,
                "claims": report.all_claims(),
                "uncertainties": [stat_check["disclaimer"]] if stat_check.get("disclaimer") else [],
                "user_context_check": context_report,
                "original_extracted_text": sf.raw_value
            }

    # 6. General / Contextual Retrieval
    blocks = retrieve_relevant_blocks(db, document_id, query=question_text, limit=3)
    if blocks:
        best_block = blocks[0]
        p_num = getattr(best_block, 'page_number', getattr(best_block, 'page_index', 1))
        summary = f"Based on the readable text: '{best_block.text_original[:160]}...'"

        expl = translation_service.generate_explanation(
            original_text=best_block.text_original[:160],
            facts=[],
            simplified_en=summary,
            target_language=language,
            allow_english_audio=allow_english_audio,
            has_cloud_consent=has_cloud_consent
        )

        draft_claims = [
            {
                "claim_id": "c_gen",
                "claim_text": summary,
                "status": "supported",
                "evidence": [
                    {
                        "page_number": p_num,
                        "block_id": best_block.block_id,
                        "bbox": best_block.bbox,
                        "text": best_block.text_original[:120]
                    }
                ]
            }
        ]
        report = validate_claims_and_evidence(draft_claims, document_id, all_blocks)
        return {
            "answer_status": "supported" if report.is_valid else "uncertain",
            "summary_text": expl.regional_translation if expl.is_translation_verified else expl.simplified_explanation,
            "approved_spoken_output": expl.approved_spoken_output,
            "is_translation_verified": expl.is_translation_verified,
            "translation_provider": expl.translation_provider_name,
            "disclaimer": expl.to_dict().get("disclaimer"),
            "claims": report.all_claims(),
            "uncertainties": report.conflicts,
            "user_context_check": context_report,
            "original_extracted_text": best_block.text_original[:160]
        }
    else:
        msg_en = "The document does not contain readable information to answer this question."
        msg_te = translate_phrase("cannot_confirm", "te-IN")
        return {
            "answer_status": "unsupported",
            "summary_text": msg_te if is_te else msg_en,
            "approved_spoken_output": msg_te if is_te else msg_en,
            "is_translation_verified": True,
            "translation_provider": "grounded_template",
            "claims": [],
            "uncertainties": ["Insufficient readable document evidence."],
            "user_context_check": context_report,
            "original_extracted_text": ""
        }
