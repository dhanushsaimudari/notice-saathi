import re
from typing import List, Dict, Any, Optional
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

def make_ref_obj(block: Any) -> Dict[str, Any]:
    page_index = getattr(block, 'page_number', getattr(block, 'page_index', 1))
    return {
        "page_index": page_index,
        "page_number": page_index,
        "block_id": getattr(block, 'block_id', 'tb_unknown'),
        "bbox": getattr(block, 'bbox', None),
        "text_snippet": getattr(block, 'text_original', '')[:140]
    }

def clean_ocr_concatenated_name(text: str) -> str:
    """Fixes common OCR word-fusion in names (e.g., 'SriD.RameshKumar' -> 'Sri D. Ramesh Kumar')."""
    cleaned = re.sub(r'^(Sri|Smt|Mr|Mrs|Shri|Dr|M/s)\.?([A-Za-z])', r'\1 \2', text, flags=re.IGNORECASE)
    cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cleaned)
    cleaned = re.sub(r'\.([A-Z])', r'. \1', cleaned)
    return re.sub(r'\s+', ' ', cleaned).strip()

def extract_facts_from_blocks(blocks: List[Any]) -> List[ExtractedCandidateFact]:
    facts: List[ExtractedCandidateFact] = []

    # Pre-build full text for multi-line regex context
    all_text = " \n ".join(b.text_original for b in blocks)

    # -------------------------------------------------------------
    # 1. Issuing Authority
    # -------------------------------------------------------------
    auth_val = None
    auth_refs = []
    for i, b in enumerate(blocks[:12]):
        t = b.text_original.strip()
        t_low = t.lower()
        if any(k in t_low for k in [
            'municipal corporation', 'department', 'high court', 'civil court',
            'district court', 'panchayat', 'board', 'directorate', 'commission'
        ]):
            # Check if preceding block has city/adjective (e.g. 'Greater Vijayawada' + 'Municipal Corporation')
            if i > 0 and any(adj in blocks[i-1].text_original.lower() for adj in ['greater', 'city', 'high', 'district', 'state', 'central', 'revenue']):
                auth_val = f"{blocks[i-1].text_original.strip()} {t}"
                auth_refs = [make_ref_obj(blocks[i-1]), make_ref_obj(b)]
            else:
                auth_val = t
                auth_refs = [make_ref_obj(b)]
            break

    # Fallback to signatory title if authority header wasn't caught
    if not auth_val:
        for b in blocks:
            if any(k in b.text_original.lower() for k in ['commissioner', 'tahsildar', 'assessing officer', 'registrar']):
                auth_val = b.text_original.strip()
                auth_refs = [make_ref_obj(b)]
                break

    if auth_val:
        facts.append(
            ExtractedCandidateFact(
                field_type="issuing_authority",
                raw_value=auth_val,
                normalized_value=auth_val,
                status="supported",
                evidence_refs=auth_refs
            )
        )

    # -------------------------------------------------------------
    # 2. Notice Number & Case Number
    # -------------------------------------------------------------
    for b in blocks:
        m = re.search(r'(?:Notice\s*No\.?|Ref\s*No\.?|File\s*No\.?)\s*[:.-]?\s*([A-Za-z0-9/_-]+(?:\s*/\s*\d{2,4})?)', b.text_original, re.IGNORECASE)
        if m:
            n_raw = b.text_original.strip()
            n_val = m.group(1).strip()
            facts.append(
                ExtractedCandidateFact(
                    field_type="notice_number",
                    raw_value=n_raw,
                    normalized_value=n_val,
                    status="supported",
                    evidence_refs=[make_ref_obj(b)]
                )
            )
            # Also register as case_number for backward compatibility with legal indexers
            facts.append(
                ExtractedCandidateFact(
                    field_type="case_number",
                    raw_value=n_raw,
                    normalized_value=n_val,
                    status="supported",
                    evidence_refs=[make_ref_obj(b)]
                )
            )
            break

    # Standard court case number regex
    case_num_regex = re.compile(
        r'\b(?:case\s*no\.?|c\.?c\.?\s*no\.?|os\s*no\.?|petition\s*no\.?|cr(?:iminal)?\.?\s*no\.?)\s*[:.-]?\s*([A-Za-z0-9/_-]+(?:\s*/\s*\d{2,4})?)',
        re.IGNORECASE
    )
    for b in blocks:
        m = case_num_regex.search(b.text_original)
        if m:
            facts.append(
                ExtractedCandidateFact(
                    field_type="case_number",
                    raw_value=m.group(0).strip(),
                    normalized_value=m.group(1).strip(),
                    status="supported",
                    evidence_refs=[make_ref_obj(b)]
                )
            )
            break

    # -------------------------------------------------------------
    # 3. Recipient Name & Address
    # -------------------------------------------------------------
    recip_found = False
    for i, b in enumerate(blocks):
        t = b.text_original.strip()
        # Avoid false matches on property/date/amount headers
        if re.search(r'\b(?:Property\s*ID|Assessment|Notice|Date|Amount|Dear)\b', t, re.IGNORECASE):
            continue

        # Match person prefixes: Sri, Smt, Shri, Mr, Mrs, Dr, M/s
        is_name_prefix = bool(re.match(r'^(?:Sri|Smt|Mr|Mrs|Shri|Dr|M/s)[. ]*([A-Za-z])', t, re.IGNORECASE))
        is_after_to = bool(i > 0 and blocks[i-1].text_original.strip().lower() in ['to,', 'to:'])

        if is_name_prefix or is_after_to:
            cleaned_name = clean_ocr_concatenated_name(t)
            facts.append(
                ExtractedCandidateFact(
                    field_type="recipient_name",
                    raw_value=t,
                    normalized_value=cleaned_name,
                    status="supported",
                    evidence_refs=[make_ref_obj(b)]
                )
            )
            recip_found = True

            # Look for address in subsequent blocks
            addr_parts = []
            addr_refs = []
            for k in range(i+1, min(i+6, len(blocks))):
                cand = blocks[k].text_original.strip()
                if re.search(r'\b(?:Property\s*ID|Assessment|Dear|Amount|Notice\s*No)\b', cand, re.IGNORECASE):
                    continue
                if any(kwd in cand.lower() for kwd in ['flat', 'plot', 'road', 'residency', 'street', 'nagar', 'colony', 'enclave', 'door', 'h.no', 'lane', 'cross']) or re.search(r'\b\d{6}\b', cand):
                    cand_cleaned = re.sub(r'([a-z])([A-Z])', r'\1 \2', cand)
                    addr_parts.append(cand_cleaned)
                    addr_refs.append(make_ref_obj(blocks[k]))
            if addr_parts:
                full_addr = ", ".join(addr_parts)
                facts.append(
                    ExtractedCandidateFact(
                        field_type="recipient_address",
                        raw_value=" ".join(addr_parts),
                        normalized_value=full_addr,
                        status="supported",
                        evidence_refs=addr_refs
                    )
                )
            break

    # -------------------------------------------------------------
    # 4. Property ID & Assessment Year
    # -------------------------------------------------------------
    for b in blocks:
        m_pid = re.search(r'(?:Property\s*ID|PID|Assessment\s*No\.?|Account\s*No\.?|Consumer\s*No\.?)\s*[:.-]?\s*([A-Za-z0-9/_-]+)', b.text_original, re.IGNORECASE)
        if m_pid:
            facts.append(
                ExtractedCandidateFact(
                    field_type="property_id",
                    raw_value=b.text_original.strip(),
                    normalized_value=m_pid.group(1).strip(),
                    status="supported",
                    evidence_refs=[make_ref_obj(b)]
                )
            )
            break

    for b in blocks:
        m_ay = re.search(r'(?:Assessment\s*Year|AY|Financial\s*Year|FY)\s*[:.-]?\s*(\d{4}[-/]\d{2,4})', b.text_original, re.IGNORECASE)
        if m_ay:
            facts.append(
                ExtractedCandidateFact(
                    field_type="assessment_year",
                    raw_value=b.text_original.strip(),
                    normalized_value=m_ay.group(1).strip(),
                    status="supported",
                    evidence_refs=[make_ref_obj(b)]
                )
            )
            break

    # -------------------------------------------------------------
    # 5. Issue Date vs. Payment Due Date / Hearing Date
    # -------------------------------------------------------------
    date_regex = re.compile(
        r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})\b',
        re.IGNORECASE
    )

    issue_date_found = False
    due_date_found = False

    for b in blocks:
        t = b.text_original.strip()

        # Check explicit payment deadline / due date
        m_due = re.search(r'(?:Payment\s*Deadline|Due\s*Date|Pay\s+on\s+or\s+before|Last\s+Date|Valid\s+Till)\s*[:.-]?\s*([0-9A-Za-z\s/-]+)', t, re.IGNORECASE)
        if m_due:
            val_cand = m_due.group(1).strip()
            dm = date_regex.search(val_cand)
            if dm:
                raw_due = dm.group(1).strip()
                norm_due = normalize_date(raw_due)
                facts.append(
                    ExtractedCandidateFact(
                        field_type="payment_due_date",
                        raw_value=t,
                        normalized_value=norm_due,
                        status="supported",
                        evidence_refs=[make_ref_obj(b)]
                    )
                )
                facts.append(
                    ExtractedCandidateFact(
                        field_type="date",
                        raw_value=raw_due,
                        normalized_value=norm_due,
                        status="supported",
                        evidence_refs=[make_ref_obj(b)]
                    )
                )
                due_date_found = True
                continue

        # Check explicit notice / issue date
        m_issue = re.search(r'(?:^Date|Notice\s*Date|Dated)\s*[:.-]?\s*([0-9A-Za-z\s/-]+)', t, re.IGNORECASE)
        if m_issue and not issue_date_found:
            val_cand = m_issue.group(1).strip()
            dm = date_regex.search(val_cand)
            if dm:
                raw_iss = dm.group(1).strip()
                norm_iss = normalize_date(raw_iss)
                facts.append(
                    ExtractedCandidateFact(
                        field_type="issue_date",
                        raw_value=t,
                        normalized_value=norm_iss,
                        status="supported",
                        evidence_refs=[make_ref_obj(b)]
                    )
                )
                facts.append(
                    ExtractedCandidateFact(
                        field_type="date",
                        raw_value=raw_iss,
                        normalized_value=norm_iss,
                        status="supported",
                        evidence_refs=[make_ref_obj(b)]
                    )
                )
                issue_date_found = True
                continue

        # General date fallback
        for dm in date_regex.finditer(t):
            raw_d = dm.group(1).strip()
            norm_d = normalize_date(raw_d)
            # Avoid re-adding if already identified as issue_date or due_date
            if not any(f.field_type == "date" and f.normalized_value == norm_d for f in facts):
                facts.append(
                    ExtractedCandidateFact(
                        field_type="date",
                        raw_value=raw_d,
                        normalized_value=norm_d,
                        status="supported",
                        evidence_refs=[make_ref_obj(b)]
                    )
                )

    # -------------------------------------------------------------
    # 6. Table Amounts & Currency Detection
    # -------------------------------------------------------------
    # Collect all numeric blocks for geometric table row matching
    numeric_blocks = []
    for b in blocks:
        txt = b.text_original.strip().replace('₹', '').replace(',', '')
        try:
            val = float(txt)
            # Filter out S.No column on the left (single digits xmin < 0.2 without decimal)
            if (b.bbox and b.bbox[1] > 0.35) or '.' in txt:
                numeric_blocks.append((b, val))
        except ValueError:
            pass

    # Map table item descriptions to their corresponding amounts
    table_items = [
        ('property tax', 'tax_amount'),
        ('building cess', 'fee_penalty'),
        ('swachhbharatcess', 'fee_penalty'),
        ('swachh bharat cess', 'fee_penalty'),
        ('late fee', 'fee_penalty'),
        ('penalty', 'fee_penalty'),
        ('interest', 'fee_penalty'),
        ('total amount due', 'total_amount_due'),
        ('net payable', 'total_amount_due'),
        ('total due', 'total_amount_due'),
        ('amount payable', 'total_amount_due')
    ]

    for b in blocks:
        t_low = b.text_original.lower().strip()
        if t_low in ['property tax reminder notice', 'property tax notice']:
            continue
        # Skip sentences (table rows are brief labels <= 5 words without sentential verbs like 'avoid' or 'please')
        if len(t_low.split()) > 5 or any(w in t_low for w in ['avoid', 'please', 'deadline', 'inform you']):
            continue

        for key, field in table_items:
            if key in t_low:
                b_cy = (b.bbox[0] + b.bbox[2]) / 2 if b.bbox else 0.5
                # Match numeric candidates positioned to the right of the description
                right_cands = [nb for nb in numeric_blocks if nb[0].bbox and nb[0].bbox[1] >= (b.bbox[1] if b.bbox else 0) - 0.05]
                if right_cands:
                    best_nb = min(right_cands, key=lambda nb: abs(((nb[0].bbox[0] + nb[0].bbox[2]) / 2) - b_cy))
                    val_str = best_nb[0].text_original.strip()
                    norm_val = normalize_currency(val_str)
                    raw_str = f"{b.text_original.strip()}: {val_str}"
                    refs = [make_ref_obj(b), make_ref_obj(best_nb[0])]

                    facts.append(
                        ExtractedCandidateFact(
                            field_type=field,
                            raw_value=raw_str,
                            normalized_value=norm_val,
                            status="supported",
                            evidence_refs=refs
                        )
                    )
                    facts.append(
                        ExtractedCandidateFact(
                            field_type="amount",
                            raw_value=raw_str,
                            normalized_value=norm_val,
                            status="supported",
                            evidence_refs=refs
                        )
                    )
                break

    # General currency pattern regex for text sentences
    amount_regex = re.compile(
        r'(?:(?:sum\s+of\s+)?(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d{1,2})?(?:\s*/-)?|\b\d+[\d,]*\s*(?:lakh|crore)s?\s*(?:rupees|rs)?\b)',
        re.IGNORECASE
    )
    for b in blocks:
        for m in amount_regex.finditer(b.text_original):
            raw_a = m.group(0).strip()
            norm_a = normalize_currency(raw_a)
            if not any(f.field_type == "amount" and f.normalized_value == norm_a for f in facts):
                facts.append(
                    ExtractedCandidateFact(
                        field_type="amount",
                        raw_value=raw_a,
                        normalized_value=norm_a,
                        status="supported",
                        evidence_refs=[make_ref_obj(b)]
                    )
                )

    # -------------------------------------------------------------
    # 7. Payment Instructions & Payment Channels
    # -------------------------------------------------------------
    instr_parts = []
    instr_refs = []
    for b in blocks:
        t = b.text_original.strip()
        t_low = t.lower()
        if any(k in t_low for k in [
            'how to pay', 'visit:www', 'visit: www', 'citizen app', 'citizenapp',
            'payment centers', 'payment center', 'service centers', 'scan to pay',
            'online', 'mobile app', 'net banking', 'rtgs', 'neft', 'upi'
        ]):
            instr_parts.append(t)
            instr_refs.append(make_ref_obj(b))

    if instr_parts:
        facts.append(
            ExtractedCandidateFact(
                field_type="payment_instructions",
                raw_value=" | ".join(instr_parts),
                normalized_value=" | ".join(instr_parts),
                status="supported",
                evidence_refs=instr_refs
            )
        )

    # -------------------------------------------------------------
    # 8. Contact Details & Citizen Assistance
    # -------------------------------------------------------------
    contact_parts = []
    contact_refs = []
    for b in blocks:
        t = b.text_original.strip()
        t_low = t.lower()
        has_phone = bool(re.search(r'\b(?:\+91[- ]?)?[0-9]{3,5}[- ]?[0-9]{6,8}\b', t))
        has_email = '@' in t and '.' in t
        has_help = any(k in t_low for k in ['for assistance', 'helpline', 'contact:', 'toll free', 'mon - sat', 'mon-sat'])

        if has_phone or has_email or has_help:
            contact_parts.append(t)
            contact_refs.append(make_ref_obj(b))

    if contact_parts:
        facts.append(
            ExtractedCandidateFact(
                field_type="contact_details",
                raw_value=" | ".join(contact_parts),
                normalized_value=" | ".join(contact_parts),
                status="supported",
                evidence_refs=contact_refs
            )
        )

    # -------------------------------------------------------------
    # 9. Explicit Warnings & Legal Consequences
    # -------------------------------------------------------------
    for b in blocks:
        t = b.text_original.strip()
        t_low = t.lower()
        if any(k in t_low for k in [
            'avoid penalty', 'failure to appear', 'distraint', 'prosecution',
            'penalty will be', 'penalty shall', 'interest will be', 'attachment of property',
            'warrant', 'coercive'
        ]):
            facts.append(
                ExtractedCandidateFact(
                    field_type="warning_consequence",
                    raw_value=t,
                    normalized_value=t,
                    status="supported",
                    evidence_refs=[make_ref_obj(b)]
                )
            )
            facts.append(
                ExtractedCandidateFact(
                    field_type="consequences_or_warnings",
                    raw_value=t,
                    normalized_value=t,
                    status="supported",
                    evidence_refs=[make_ref_obj(b)]
                )
            )
            break

    # -------------------------------------------------------------
    # 10. Statutory Provisions
    # -------------------------------------------------------------
    statute_regex = re.compile(
        r'\b(?:section|sec\.?|u/s)\s*(\d+[A-Za-z]?(?:\s*\([0-9a-zA-Z]+\))*)\s*(?:of\s*(?:the\s*)?)?([A-Za-z\s]+(?:Act|Code|Rules))?',
        re.IGNORECASE
    )
    for b in blocks:
        for m in statute_regex.finditer(b.text_original):
            full_statute = m.group(0).strip()
            sec_num = m.group(1).strip()
            act_name = m.group(2).strip() if m.group(2) else ""
            status = "supported" if act_name else "uncertain"
            reason = None if act_name else "UNVERIFIED_STATUTE_NAME"
            facts.append(
                ExtractedCandidateFact(
                    field_type="statutory_provision",
                    raw_value=full_statute,
                    normalized_value=f"Section {sec_num} {act_name}".strip(),
                    status=status,
                    evidence_refs=[make_ref_obj(b)],
                    reason_code=reason
                )
            )

    # -------------------------------------------------------------
    # 11. Required Action Synthesis
    # -------------------------------------------------------------
    # Priority A: Tax / Payment Action
    dl_fact = next((f for f in facts if f.field_type == "payment_due_date"), None)
    tot_fact = next((f for f in facts if f.field_type == "total_amount_due"), None)
    warn_fact = next((f for f in facts if f.field_type == "consequences_or_warnings"), None)

    if tot_fact and dl_fact:
        act_text = f"Pay property tax of {tot_fact.normalized_value} on or before {dl_fact.normalized_value} to avoid penalty."
        act_refs = tot_fact.evidence_refs + dl_fact.evidence_refs
        if warn_fact:
            act_refs += warn_fact.evidence_refs
        facts.append(
            ExtractedCandidateFact(
                field_type="required_action",
                raw_value=act_text,
                normalized_value=act_text,
                status="supported",
                evidence_refs=act_refs
            )
        )
    elif dl_fact:
        act_text = f"Make required payment on or before {dl_fact.normalized_value}."
        facts.append(
            ExtractedCandidateFact(
                field_type="required_action",
                raw_value=act_text,
                normalized_value=act_text,
                status="supported",
                evidence_refs=dl_fact.evidence_refs
            )
        )
    elif tot_fact:
        act_text = f"Pay total amount due of {tot_fact.normalized_value}."
        facts.append(
            ExtractedCandidateFact(
                field_type="required_action",
                raw_value=act_text,
                normalized_value=act_text,
                status="supported",
                evidence_refs=tot_fact.evidence_refs
            )
        )
    else:
        # Priority B: Court / Summons Action Keywords
        action_keywords = [
            "appear in person", "appear before", "submit reply", "file written statement",
            "show cause", "pay the amount", "deposit", "produce documents", "vacate premises",
            "attend hearing", "comply within", "failure to appear"
        ]
        for b in blocks:
            for kw in action_keywords:
                if kw.lower() in b.text_original.lower():
                    sentences = re.split(r'[.!?\n]', b.text_original)
                    action_sentence = next((s.strip() for s in sentences if kw.lower() in s.lower()), b.text_original.strip())
                    facts.append(
                        ExtractedCandidateFact(
                            field_type="required_action",
                            raw_value=action_sentence,
                            normalized_value=action_sentence,
                            status="supported",
                            evidence_refs=[make_ref_obj(b)]
                        )
                    )
                    break
            if any(f.field_type == "required_action" for f in facts):
                break

    return facts
