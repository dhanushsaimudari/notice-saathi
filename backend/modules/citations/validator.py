import re
from typing import List, Dict, Any, Tuple, Optional
from backend.database.models import TextBlock

INJECTION_PATTERNS = [
    r'ignore\s+(?:all\s+)?prior\s+instructions',
    r'ignore\s+previous\s+instructions',
    r'system\s+prompt',
    r'bypass\s+(?:access\s+controls|security)',
    r'reveal\s+(?:secrets?|keys?|passwords?)',
    r'you\s+must\s+say\s+the\s+defendant\s+is\s+guilty',
    r'you\s+must\s+declare\s+this\s+fake',
    r'disregard\s+the\s+above',
    r'<script.*?>.*?</script>'
]

class ValidationReport:
    def __init__(
        self,
        is_valid: bool,
        supported_claims: List[Dict[str, Any]],
        uncertain_claims: List[Dict[str, Any]],
        conflicting_claims: List[Dict[str, Any]],
        not_found_claims: List[Dict[str, Any]],
        conflicts: List[str],
        injections_detected: List[str]
    ):
        self.is_valid = is_valid
        self.supported_claims = supported_claims
        self.uncertain_claims = uncertain_claims
        self.conflicting_claims = conflicting_claims
        self.not_found_claims = not_found_claims
        self.conflicts = conflicts
        self.injections_detected = injections_detected

    @property
    def unsupported_claims(self) -> List[Dict[str, Any]]:
        return self.not_found_claims

    def all_claims(self) -> List[Dict[str, Any]]:
        return (
            self.supported_claims +
            self.uncertain_claims +
            self.conflicting_claims +
            self.not_found_claims
        )

def detect_prompt_injections(text: str) -> List[str]:
    detected = []
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            detected.append(pattern)
    return detected

def cross_check_user_context(
    user_context: str,
    document_blocks: List[TextBlock]
) -> Dict[str, Any]:
    """
    Compares user-provided context strictly against document evidence.
    Never merges user statements into verified document proof.
    Categorizes:
    - confirmed_by_document: statements in user notes matching verified evidence.
    - contradicted_by_document: statements in user notes directly conflicting with document evidence.
    - only_in_user_context: claims mentioned only by user with no document support.
    """
    if not user_context or not user_context.strip():
        return {
            "has_context": False,
            "confirmed_by_document": [],
            "contradicted_by_document": [],
            "only_in_user_context": []
        }

    combined_doc_text = " ".join(b.text_original.lower() for b in document_blocks)
    user_sentences = [s.strip() for s in re.split(r'[.!?\n]', user_context) if s.strip()]
    
    confirmed = []
    contradicted = []
    only_user = []

    # 1. Date check
    user_dates = re.findall(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b', user_context)
    doc_dates = re.findall(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b', combined_doc_text)
    
    if user_dates:
        for ud in user_dates:
            if ud in doc_dates:
                confirmed.append(f"Date '{ud}' matches date found in document.")
            elif doc_dates:
                contradicted.append(f"User mentioned date '{ud}', but document specifies '{', '.join(set(doc_dates))}'.")
            else:
                only_user.append(f"Date '{ud}' is only in user notes; not found in document.")

    # 2. Currency check
    user_amounts = re.findall(r'[\d,]{4,}', user_context)
    doc_amounts = re.findall(r'[\d,]{4,}', combined_doc_text)

    if user_amounts:
        for ua in user_amounts:
            clean_ua = ua.replace(',', '')
            matched = any(clean_ua == da.replace(',', '') for da in doc_amounts)
            if matched:
                confirmed.append(f"Amount '{ua}' matches figure found in document.")
            elif doc_amounts:
                contradicted.append(f"User mentioned amount '{ua}', but document specifies '{', '.join(set(doc_amounts))}'.")
            else:
                only_user.append(f"Amount '{ua}' appears only in user notes; not found in document.")

    # 3. Status contradiction check (waiver/payment/cancellation claims vs active notice)
    waiver_terms = ["waived", "cancelled", "already paid", "dismissed", "settled", "not liable", "no penalty"]
    user_lower = user_context.lower()
    for term in waiver_terms:
        if term in user_lower:
            contradicted.append(f"User context claims '{term}', which is not reflected in the active document text.")

    for s in user_sentences:
        s_words = set(re.findall(r'\b\w{4,}\b', s.lower()))
        if s_words:
            overlap = [w for w in s_words if w in combined_doc_text]
            if len(overlap) < 1:
                only_user.append(f"'{s}' is only in user context; not supported by document.")

    return {
        "has_context": True,
        "has_conflicts": len(contradicted) > 0,
        "confirmed_by_document": list(set(confirmed)),
        "contradicted_by_document": list(set(contradicted)),
        "only_in_user_context": list(set(only_user))
    }

def validate_claims_and_evidence(
    draft_claims: List[Dict[str, Any]],
    document_id: str,
    valid_blocks: List[TextBlock]
) -> ValidationReport:
    """
    Evidence-grounded claim validator.
    Rules:
    1. Rejects prompt injection in claims or blocks.
    2. Citing a missing block or block from another document -> 'not_found' (INVALID_BLOCK_REFERENCE).
    3. Citing a real block with NO semantic relevance -> 'not_found' (IRRELEVANT_BLOCK_CITATION).
    4. Citing a real block with partial/weak relevance -> 'uncertain' (WEAK_SEMANTIC_GROUNDING).
    5. Conflicting dates or amounts across claims -> 'conflicting' (CONFLICTING_EVIDENCE).
    6. Only claims backed by relevant, non-conflicting, verified blocks -> 'supported'.
    """
    valid_block_map = {b.block_id: b for b in valid_blocks if b.document_id == document_id}
    
    supported: List[Dict[str, Any]] = []
    uncertain: List[Dict[str, Any]] = []
    conflicting: List[Dict[str, Any]] = []
    not_found: List[Dict[str, Any]] = []
    conflicts: List[str] = []
    injections: List[str] = []
    
    for claim in draft_claims:
        claim_text = claim.get("claim_text") or claim.get("text", "")
        evidence_list = claim.get("evidence", [])
        
        # 1. Prompt Injection
        inj = detect_prompt_injections(claim_text)
        if inj:
            injections.extend(inj)
            claim["status"] = "not_found"
            claim["reason_code"] = "PROMPT_INJECTION_DETECTED"
            not_found.append(claim)
            continue
            
        # 2. Evidence presence
        if not evidence_list:
            claim["status"] = "not_found"
            claim["reason_code"] = "MISSING_EVIDENCE_CITATION"
            not_found.append(claim)
            continue
            
        has_valid_block = False
        semantic_relevance = False
        relevance_score = 0
        
        # Extract critical claim facts: dates and numbers
        claim_dates = re.findall(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b', claim_text)
        claim_numbers = re.findall(r'\b\d+[\d,]*\b', claim_text)
        claim_words = set(re.findall(r'\b\w{3,}\b', claim_text.lower()))

        for ev in evidence_list:
            bid = ev.get("block_id")
            if bid in valid_block_map:
                has_valid_block = True
                block = valid_block_map[bid]
                block_text_lower = block.text_original.lower()
                
                # Check prompt injection inside block itself
                b_inj = detect_prompt_injections(block.text_original)
                if b_inj:
                    injections.extend(b_inj)
                
                # Semantic relevance check:
                # If claim specifically asserts a date, the block MUST contain that date or components
                date_match = True
                if claim_dates:
                    date_match = any(cd in block.text_original for cd in claim_dates)
                
                # Word overlap
                block_words = set(re.findall(r'\b\w{3,}\b', block_text_lower))
                overlap = claim_words.intersection(block_words)
                
                if len(overlap) >= 1 and date_match:
                    semantic_relevance = True
                    relevance_score += len(overlap)
                elif len(overlap) >= 1 and not claim_dates:
                    semantic_relevance = True
                    relevance_score += len(overlap)

        if not has_valid_block:
            claim["status"] = "not_found"
            claim["reason_code"] = "INVALID_BLOCK_REFERENCE"
            not_found.append(claim)
        elif not semantic_relevance:
            claim["status"] = "not_found"
            claim["reason_code"] = "IRRELEVANT_BLOCK_CITATION"
            not_found.append(claim)
        elif claim.get("status") == "uncertain":
            uncertain.append(claim)
        elif claim.get("status") == "conflicting":
            conflicting.append(claim)
        else:
            claim["status"] = "supported"
            supported.append(claim)
            
    # 3. Detect conflicting dates across supported claims
    date_claims = [
        c for c in supported 
        if "date" in c.get("claim_text", "").lower() or re.search(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}', c.get("claim_text", ""))
    ]
    if len(date_claims) > 1:
        extracted_dates = []
        for dc in date_claims:
            m = re.findall(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{1,2}\s+[A-Za-z]+\s+\d{4}', dc.get("claim_text", ""))
            extracted_dates.extend(m)
        if len(set(extracted_dates)) > 1:
            conflict_msg = f"Conflicting dates identified in document: {', '.join(set(extracted_dates))}"
            conflicts.append(conflict_msg)
            for dc in date_claims:
                if dc in supported:
                    supported.remove(dc)
                dc["status"] = "conflicting"
                dc["reason_code"] = "CONFLICTING_DATES_IN_DOCUMENT"
                uncertain.append(dc)
                conflicting.append(dc)

    # 4. Detect conflicting amounts across supported claims
    amount_claims = [
        c for c in supported
        if "amount" in c.get("claim_text", "").lower() or "₹" in c.get("claim_text", "") or "rs" in c.get("claim_text", "").lower()
    ]
    if len(amount_claims) > 1:
        extracted_amounts = []
        for ac in amount_claims:
            m = re.findall(r'[\d,]{4,}', ac.get("claim_text", ""))
            extracted_amounts.extend(m)
        if len(set(extracted_amounts)) > 1:
            conflict_msg = f"Conflicting amounts identified in document: {', '.join(set(extracted_amounts))}"
            conflicts.append(conflict_msg)
            for ac in amount_claims:
                if ac in supported:
                    supported.remove(ac)
                ac["status"] = "conflicting"
                ac["reason_code"] = "CONFLICTING_AMOUNTS_IN_DOCUMENT"
                uncertain.append(ac)
                conflicting.append(ac)

    # 5. Detect conflicting instructions across supported claims (Case F)
    pos_action_claims = [
        c for c in supported
        if any(k in c.get("claim_text", "").lower() for k in ["required to pay", "must pay", "must appear", "appear in person", "penalty of", "demanded", "payment required"])
    ]
    neg_action_claims = [
        c for c in supported
        if any(k in c.get("claim_text", "").lower() for k in ["waived", "not required", "need not", "cancelled", "dismissed", "exempted", "payment waived"])
    ]
    if pos_action_claims and neg_action_claims:
        conflict_msg = "Conflicting instructions identified in document: one passage requires action/payment while another indicates waiver or exemption."
        conflicts.append(conflict_msg)
        for c in (pos_action_claims + neg_action_claims):
            if c in supported:
                supported.remove(c)
            c["status"] = "conflicting"
            c["reason_code"] = "CONFLICTING_INSTRUCTIONS_IN_DOCUMENT"
            uncertain.append(c)
            conflicting.append(c)

    is_valid = len(not_found) == 0 and len(conflicting) == 0 and len(injections) == 0
    return ValidationReport(
        is_valid=is_valid,
        supported_claims=supported,
        uncertain_claims=uncertain,
        conflicting_claims=conflicting,
        not_found_claims=not_found,
        conflicts=conflicts,
        injections_detected=injections
    )
