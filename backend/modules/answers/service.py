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
    
    # Primary headline identification
    first_block = blocks[0] if blocks else None
    
    # Check if court notice or official communication
    is_court = any("court" in b.text_original.lower() or "summons" in b.text_original.lower() or "case no" in b.text_original.lower() for b in blocks)
    title_key = "court_notice_title" if is_court else "official_notice_title"
    title_str = translate_phrase(title_key, language)
    
    # Categorize facts
    date_facts = [f for f in facts if f.field_type == "date"]
    amount_facts = [f for f in facts if f.field_type == "amount"]
    action_facts = [f for f in facts if f.field_type == "required_action"]
    statute_facts = [f for f in facts if f.field_type == "statutory_provision"]
    case_facts = [f for f in facts if f.field_type == "case_number"]
    
    is_te = language.startswith("te")

    # Detect conflicting instructions in blocks (Case F)
    pos_blocks = [b for b in blocks if any(k in b.text_original.lower() for k in ["required to pay", "must pay", "must appear", "appear in person without fail", "appear in person", "penalty of", "demanded", "payment required"])]
    neg_blocks = [b for b in blocks if any(k in b.text_original.lower() for k in ["waived", "not required", "need not", "cancelled", "dismissed", "exempted", "payment is waived", "penalty is cancelled"])]
    has_conflicting_action = bool(pos_blocks and neg_blocks)
    
    # Card 1: What is this document & Key Details
    if is_te:
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
            card1_status = "no_action_found"
            action_str = "చదవగలిగిన పూర్తి పత్రంలో ఎటువంటి నిర్దిష్ట చర్య లేదా గడువు పేర్కొనబడలేదు."
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
            card1_status = "no_action_found"
            action_str = "No action or deadline was identified in the readable text of the document."
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
    
    proof_refs = []
    if first_block:
        p_num = getattr(first_block, 'page_number', getattr(first_block, 'page_index', 1))
        proof_refs.append({
            "page_number": p_num,
            "block_id": first_block.block_id,
            "bbox": first_block.bbox,
            "text": first_block.text_original[:140]
        })
    if date_facts and date_facts[0].evidence_refs:
        proof_refs.append(date_facts[0].evidence_refs[0])
    if has_conflicting_action:
        for b in (pos_blocks + neg_blocks)[:4]:
            proof_refs.append({
                "page_number": getattr(b, 'page_number', getattr(b, 'page_index', 1)),
                "block_id": b.block_id,
                "bbox": b.bbox,
                "text": b.text_original[:140]
            })

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
    
    # 3. Targeted Fact Retrieval: Date questions
    if any(k in q_lower for k in ["date", "when", "time", "deadline", "తేదీ", "ఎప్పుడు"]):
        date_facts = [f for f in facts if f.field_type == "date"]
        if date_facts:
            # Check for multiple conflicting dates
            unique_dates = list({df.normalized_value for df in date_facts})
            if len(unique_dates) > 1:
                summary_en = f"The document mentions multiple conflicting dates: {', '.join(unique_dates)}."
                claims = [
                    {
                        "claim_id": f"c_date_{idx}",
                        "claim_text": f"Date noted: {df.normalized_value}",
                        "status": "conflicting",
                        "evidence": df.evidence_refs
                    }
                    for idx, df in enumerate(date_facts)
                ]
                
                expl = translation_service.generate_explanation(
                    original_text=", ".join([df.raw_value for df in date_facts]),
                    facts=[{"date": df.normalized_value} for df in date_facts],
                    simplified_en=summary_en,
                    target_language=language,
                    allow_english_audio=allow_english_audio,
                    has_cloud_consent=has_cloud_consent
                )
                
                # If template didn't match the complex conflicting dates string, provide clear grounded Telugu
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
                    "original_extracted_text": ", ".join([df.raw_value for df in date_facts])
                }

            df = date_facts[0]
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

    # 4. Targeted Fact Retrieval: Amount questions
    if any(k in q_lower for k in ["amount", "money", "fee", "rupee", "how much", "మొత్తం", "రూపాయలు"]):
        amount_facts = [f for f in facts if f.field_type == "amount"]
        if amount_facts:
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

    # 5. Targeted Fact Retrieval: Required Action (Cases B, D, E, F)
    if any(k in q_lower for k in ["action", "what to do", "ask me", "should i do", "ఏమి చేయాలి", "చర్య"]):
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

    # 6. Targeted Fact Retrieval: Statutory reference & Section questions
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
            "answer_status": "not_found",
            "summary_text": msg_te if is_te else msg_en,
            "approved_spoken_output": msg_te if is_te else msg_en,
            "is_translation_verified": True,
            "translation_provider": "grounded_template",
            "claims": [],
            "uncertainties": ["Insufficient readable document evidence."],
            "user_context_check": context_report,
            "original_extracted_text": ""
        }
