import re
from typing import Dict, Any, Tuple, Optional

# Vetted reference sample of common Indian notice statutes.
# NOTE: This dictionary represents a verified reference sample for demonstration and common notice types.
# It is NOT an exhaustive or authoritative legal reference system.
# Any externally verified entry must explicitly state statute, jurisdiction, version, and trusted source.
EXTERNAL_VERIFIED_STATUTES = {
    "138_ni_act": {
        "pattern": r"(?:section|sec\.?|u/s)?\s*138\b.*?(?:negotiable\s*instruments?\s*act|ni\s*act)",
        "canonical_name": "Section 138, Negotiable Instruments Act, 1881",
        "statute": "Negotiable Instruments Act, 1881 (Act No. 26 of 1881)",
        "jurisdiction": "India (Central Legislation)",
        "version": "As amended by the Negotiable Instruments (Amendment) Act, 2018 (Act 20 of 2018)",
        "trusted_source": "Legislative Department, Ministry of Law and Justice, Government of India",
        "explanation_en": "Statutory provision covering dishonour of cheques for insufficiency of funds under Indian law. Specific allegations, amounts, or payment deadlines depend strictly on what is explicitly written in the notice.",
        "explanation_te": "భారతీయ చట్టం ప్రకారం బ్యాంకు ఖాతాలో తగినంత నిధులు లేకపోవడం వల్ల చెక్కు అనాదరణ (బౌన్స్) అయిన సందర్భాలకు వర్తించే చట్టబద్ధమైన నిబంధన. నిర్దిష్ట ఆరోపణలు లేదా చెల్లింపు గడువులు పత్రంలో పేర్కొన్న వివరాలపై మాత్రమే ఆధారపడి ఉంటాయి.",
        "is_verified": True
    },
    "25_pss_act": {
        "pattern": r"(?:section|sec\.?|u/s)?\s*25\b.*?(?:payment\s*and\s*settlement|pss\s*act)",
        "canonical_name": "Section 25, Payment and Settlement Systems Act, 2007",
        "statute": "Payment and Settlement Systems Act, 2007 (Act No. 51 of 2007)",
        "jurisdiction": "India (Central Legislation)",
        "version": "Current official text",
        "trusted_source": "Reserve Bank of India & Ministry of Law and Justice",
        "explanation_en": "Applies to dishonour of electronic fund transfer instructions (e.g., auto-debits, NACH, or ECS) due to insufficient funds.",
        "explanation_te": "ఎలక్ట్రానిక్ ఫండ్స్ బదిలీ లేదా ఈసీఎస్ ఆటో-డెబిట్ బౌన్స్ అయిన సందర్భాలకు ఈ నిబంధన వర్తిస్తుంది.",
        "is_verified": True
    },
    "91_crpc": {
        "pattern": r"(?:section|sec\.?|u/s)?\s*91\b.*?(?:cr\.?p\.?c|criminal\s*procedure|code\s*of\s*criminal)",
        "canonical_name": "Section 91, Code of Criminal Procedure, 1973",
        "statute": "Code of Criminal Procedure, 1973 (Act No. 2 of 1974) / Corresponding BNSS provisions",
        "jurisdiction": "India (Criminal Jurisdiction)",
        "version": "Central Code",
        "trusted_source": "Ministry of Law and Justice, Government of India",
        "explanation_en": "Authorizes a court or an investigating police officer to issue a written summons or order directing a person to produce a document or thing necessary for an investigation or trial.",
        "explanation_te": "విచారణ కోసం అవసరమైన పత్రాలు లేదా వస్తువులను సమర్పించాలని ఆదేశించే కోర్టు లేదా పోలీసు అధికారిక సమన్లు.",
        "is_verified": True
    },
    "80_cpc": {
        "pattern": r"(?:section|sec\.?|u/s)?\s*80\b.*?(?:c\.?p\.?c|civil\s*procedure|code\s*of\s*civil)",
        "canonical_name": "Section 80, Code of Civil Procedure, 1908",
        "statute": "Code of Civil Procedure, 1908 (Act No. 5 of 1908)",
        "jurisdiction": "India (Civil Jurisdiction)",
        "version": "Central Code",
        "trusted_source": "Ministry of Law and Justice, Government of India",
        "explanation_en": "Mandates a statutory two-month prior written notice before instituting a civil suit against the Government or a public officer in their official capacity.",
        "explanation_te": "ప్రభుత్వం లేదా ప్రభుత్వ అధికారిపై సివిల్ దావా వేయడానికి ముందు ఇవ్వాల్సిన రెండు నెలల ముందస్తు చట్టబద్ధమైన నోటీసు.",
        "is_verified": True
    }
}

LEGAL_ADVICE_TRIGGERS = [
    "will i go to jail",
    "will i be arrested",
    "am i guilty",
    "how to win",
    "legal strategy",
    "guilty or not",
    "should i ignore",
    "can i ignore",
    "is this legal advice",
    "what are my chances"
]

def check_out_of_bounds_legal_question(question: str) -> Optional[Dict[str, Any]]:
    q_lower = question.lower()
    for trigger in LEGAL_ADVICE_TRIGGERS:
        if trigger in q_lower:
            disclaimer_en = (
                "This document does not establish guilt, penalties, or court outcomes. "
                "NoticeSaathi provides plain-language document reading and evidence citations only, "
                "not legal representation or outcome predictions. Please consult an advocate."
            )
            disclaimer_te = (
                "ఈ పత్రం ద్వారా మీ నేరం లేదా న్యాయస్థాన తీర్పును నిర్ధారించలేము. "
                "నోటీసుసాథీ కేవలం పత్రంలోని సమాచారాన్ని అర్థమయ్యేలా వివరిస్తుంది తప్ప న్యాయ సలహా ఇవ్వదు. "
                "దయచేసి అర్హత కలిగిన న్యాయవాదిని సంప్రదించండి."
            )
            return {
                "is_out_of_bounds": True,
                "answer_status": "unsupported",
                "summary_en": disclaimer_en,
                "summary_te": disclaimer_te,
                "trigger_matched": trigger
            }
    return None

def verify_statutory_reference(statute_text: str) -> Dict[str, Any]:
    """
    Checks if statutory reference matches vetted sample registry.
    If matched, provides verified statute details with jurisdiction and trusted source.
    If not matched, strictly explains only what the document text says and states limitation.
    Never speculates or invents statutory interpretations.
    """
    clean_stat = statute_text.strip()
    for key, data in EXTERNAL_VERIFIED_STATUTES.items():
        if re.search(data["pattern"], clean_stat, re.IGNORECASE):
            return {
                "is_verified": True,
                "canonical_name": data["canonical_name"],
                "statute": data["statute"],
                "jurisdiction": data["jurisdiction"],
                "version": data["version"],
                "trusted_source": data["trusted_source"],
                "explanation_en": data["explanation_en"],
                "explanation_te": data["explanation_te"],
                "disclaimer": None
            }

    # Unverified / Unregistered Section: Strict evidence-only limitation
    disclaimer_en = (
        f"NoticeSaathi does not maintain an externally verified legal reference entry for '{clean_stat}'. "
        "The application explains only the text explicitly written in this uploaded notice. "
        "Consult a qualified legal professional for statutory interpretation and counsel."
    )
    disclaimer_te = (
        f"ఈ చట్ట నిబంధన '{clean_stat}' కోసం అధికారిక చట్టబద్ధ ధ్రువీకరణ డేటాబేస్ అందుబాటులో లేదు. "
        "కేవలం పత్రంలో పేర్కొన్న సమాచారం మాత్రమే ఇక్కడ చూపబడుతోంది. న్యాయ సలహా కోసం న్యాయవాదిని సంప్రదించండి."
    )

    return {
        "is_verified": False,
        "canonical_name": clean_stat,
        "statute": "Unverified Statute",
        "jurisdiction": "Unverified Jurisdiction",
        "version": "Unverified Version",
        "trusted_source": "Source Document Only",
        "explanation_en": disclaimer_en,
        "explanation_te": disclaimer_te,
        "disclaimer": disclaimer_en
    }
