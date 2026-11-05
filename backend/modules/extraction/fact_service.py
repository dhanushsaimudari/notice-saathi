import re
from typing import List, Dict, Any
from backend.modules.normalization.service import normalize_currency, normalize_date, normalize_whitespace

class ExtractedCandidateFact:
    def __init__(
        self,
        field_type: str,
        raw_value: str,
        normalized_value: str,
        status: str,
        evidence_refs: List[Dict[str, Any]],
        reason_code: str | None = None
    ):
        self.field_type = field_type
        self.raw_value = raw_value
        self.normalized_value = normalized_value
        self.status = status
        self.evidence_refs = evidence_refs
        self.reason_code = reason_code

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_type": self.field_type,
            "raw_value": self.raw_value,
            "normalized_value": self.normalized_value,
            "status": self.status,
            "evidence_refs": self.evidence_refs,
            "reason_code": self.reason_code
        }

def extract_facts_from_blocks(blocks: List[Any]) -> List[ExtractedCandidateFact]:
    facts: List[ExtractedCandidateFact] = []
    
    # Regular expressions for high-impact legal & official notice fields
    date_regex = re.compile(
        r'\b(?:on|before|dated?|by|hearing\s+date|next\s+date)?\s*'
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})\b',
        re.IGNORECASE
    )
    
    amount_regex = re.compile(
        r'(?:(?:sum\s+of\s+)?(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d{1,2})?(?:\s*/-)?|\b\d+[\d,]*\s*(?:lakh|crore)s?\s*(?:rupees|rs)?\b)',
        re.IGNORECASE
    )
    
    case_num_regex = re.compile(
        r'\b(?:case\s*no\.?|c\.?c\.?\s*no\.?|os\s*no\.?|petition\s*no\.?|cr(?:iminal)?\.?\s*no\.?|notice\s*no\.?|ref\s*no\.?)\s*[:.-]?\s*([A-Za-z0-9/_-]+(?:\s*/\s*\d{2,4})?)',
        re.IGNORECASE
    )
    
    statute_regex = re.compile(
        r'\b(?:section|sec\.?|u/s)\s*(\d+[A-Za-z]?(?:\s*\([0-9a-zA-Z]+\))*)\s*(?:of\s*(?:the\s*)?)?([A-Za-z\s]+(?:Act|Code|Rules))?',
        re.IGNORECASE
    )
    
    action_keywords = [
        "appear in person", "appear before", "submit reply", "file written statement",
        "show cause", "pay the amount", "deposit", "produce documents", "vacate premises",
        "attend hearing", "comply within", "failure to appear"
    ]
    
    for block in blocks:
        text = block.text_original
        block_id = block.block_id
        page_index = getattr(block, 'page_number', getattr(block, 'page_index', 1))
        ref_obj = {
            "page_index": page_index,
            "block_id": block_id,
            "text_snippet": text[:120]
        }
        
        # 1. Dates
        for match in date_regex.finditer(text):
            raw_d = match.group(1).strip()
            norm_d = normalize_date(raw_d)
            facts.append(
                ExtractedCandidateFact(
                    field_type="date",
                    raw_value=raw_d,
                    normalized_value=norm_d,
                    status="supported",
                    evidence_refs=[ref_obj]
                )
            )
            
        # 2. Amounts
        for match in amount_regex.finditer(text):
            raw_a = match.group(0).strip()
            norm_a = normalize_currency(raw_a)
            facts.append(
                ExtractedCandidateFact(
                    field_type="amount",
                    raw_value=raw_a,
                    normalized_value=norm_a,
                    status="supported",
                    evidence_refs=[ref_obj]
                )
            )
            
        # 3. Case Numbers
        for match in case_num_regex.finditer(text):
            raw_c = match.group(0).strip()
            num_part = match.group(1).strip()
            facts.append(
                ExtractedCandidateFact(
                    field_type="case_number",
                    raw_value=raw_c,
                    normalized_value=num_part,
                    status="supported",
                    evidence_refs=[ref_obj]
                )
            )
            
        # 4. Statutory Provisions
        for match in statute_regex.finditer(text):
            full_statute = match.group(0).strip()
            sec_num = match.group(1).strip()
            act_name = match.group(2).strip() if match.group(2) else ""
            
            # Rule: If section number appears without act name, mark uncertain
            status = "supported" if act_name else "uncertain"
            reason = None if act_name else "UNVERIFIED_STATUTE_NAME"
            
            facts.append(
                ExtractedCandidateFact(
                    field_type="statutory_provision",
                    raw_value=full_statute,
                    normalized_value=f"Section {sec_num} {act_name}".strip(),
                    status=status,
                    evidence_refs=[ref_obj],
                    reason_code=reason
                )
            )
            
        # 5. Required Actions
        for kw in action_keywords:
            if kw.lower() in text.lower():
                # Extract sentence containing the action
                sentences = re.split(r'[.!?\n]', text)
                action_sentence = next((s.strip() for s in sentences if kw.lower() in s.lower()), text)
                facts.append(
                    ExtractedCandidateFact(
                        field_type="required_action",
                        raw_value=action_sentence,
                        normalized_value=action_sentence,
                        status="supported",
                        evidence_refs=[ref_obj]
                    )
                )
                break
                
    return facts
