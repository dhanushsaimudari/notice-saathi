import re
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any

from backend.config import settings
from backend.modules.translation.providers import (
    BaseTranslationProvider,
    ProviderConfig,
    TranslationResult,
    TranslationError,
    GoogleCloudTranslationProvider,
    AzureTranslatorProvider,
    GeminiTranslationProvider,
    GroundedLegalExplanationProvider
)

logger = logging.getLogger("noticesaathi.translation")

# Vetted bilingual UI phrases for accessibility labels and status notices
UI_PHRASES = {
    "te-IN": {
        "what_do_you_want": "ఈ పత్రం గురించి మీరు ఏమి తెలుసుకోవాలనుకుంటున్నారు?",
        "date_unclear": "తేదీ స్పష్టంగా కనిపించడం లేదు. దయచేసి ఆ భాగాన్ని మళ్లీ స్పష్టంగా ఫోటో తీయండి.",
        "cannot_confirm": "ఈ పత్రం ఆధారంగా ఈ విషయాన్ని నేను నిర్ధారించలేకపోతున్నాను.",
        "listen_explanation": "వివరణ వినండి",
        "read_explanation": "వివరణ చదవండి",
        "court_notice_title": "న్యాయస్థాన నోటీసు (కోర్టు నోటీసు)",
        "official_notice_title": "అధికారిక నోటీసు",
        "no_action_stated": "ఈ పత్రంలో నిర్దిష్ట చర్య లేదా గడువు స్పష్టంగా పేర్కొనబడలేదు.",
        "translation_unavailable": "ప్రాంతీయ భాషా వివరణ ప్రస్తుతం అందుబాటులో లేదు. ధ్రువీకరించబడిన అసలు పత్రం ఆంగ్లంలో క్రింద చూపబడింది. మీరు ఆంగ్ల వివరణ వినాలనుకుంటే దయచేసి ఆప్షన్ ఎంచుకోండి.",
        "listen_in_english_prompt": "ఆంగ్ల వివరణ వినండి (Listen in English)",
        "retry_translation": "మళ్లీ ప్రయత్నించండి (Retry)"
    },
    "hi-IN": {
        "what_do_you_want": "इस दस्तावेज़ के बारे में आप क्या जानना चाहते हैं?",
        "date_unclear": "तारीख स्पष्ट रूप से दिखाई नहीं दे रही है। कृपया उस हिस्से की स्पष्ट तस्वीर लें।",
        "cannot_confirm": "इस दस्तावेज़ के आधार पर मैं इसकी पुष्टि नहीं कर सकता।",
        "listen_explanation": "विवरण सुनें",
        "read_explanation": "विवरण पढ़ें",
        "court_notice_title": "न्यायालय नोटिस (कोर्ट नोटिस)",
        "official_notice_title": "आधिकारिक नोटिस",
        "no_action_stated": "इस दस्तावेज़ में कोई स्पष्ट कार्रवाई या समय-सीमा नहीं दी गई है।",
        "translation_unavailable": "क्षेत्रीय भाषा अनुवाद सेवा उपलब्ध नहीं है। सत्यापित मूल दस्तावेज़ विवरण अंग्रेजी में प्रदर्शित हैं।",
        "listen_in_english_prompt": "अंग्रेजी विवरण सुनें (Listen in English)",
        "retry_translation": "पुनः प्रयास करें (Retry)"
    },
    "en-IN": {
        "what_do_you_want": "What would you like to know about this document?",
        "date_unclear": "The date is not clear. Please take another photo of that part.",
        "cannot_confirm": "I cannot confirm this from the document.",
        "listen_explanation": "Listen to the explanation",
        "read_explanation": "Read the explanation",
        "court_notice_title": "Court Notice",
        "official_notice_title": "Official Notice",
        "no_action_stated": "No specific action or deadline was identified in the readable text.",
        "translation_unavailable": "Regional-language translation is currently unavailable. Displaying verified source text in English.",
        "listen_in_english_prompt": "Listen in English",
        "retry_translation": "Retry"
    }
}

def translate_ui_label(key: str, language: str = "te-IN") -> str:
    lang_map = UI_PHRASES.get(language, UI_PHRASES["en-IN"])
    return lang_map.get(key, UI_PHRASES["en-IN"].get(key, ""))

translate_phrase = translate_ui_label

class TranslationValidationResult:
    def __init__(
        self,
        is_valid: bool,
        preserved_tokens: List[str],
        missing_tokens: List[str],
        negation_preserved: bool,
        modal_preserved: bool = True,
        conditional_preserved: bool = True,
        warning_preserved: bool = True,
        errors: Optional[List[str]] = None,
        error_message: Optional[str] = None
    ):
        self.is_valid = is_valid
        self.preserved_tokens = preserved_tokens
        self.missing_tokens = missing_tokens
        self.negation_preserved = negation_preserved
        self.modal_preserved = modal_preserved
        self.conditional_preserved = conditional_preserved
        self.warning_preserved = warning_preserved
        self.errors: List[str] = errors or []
        self.error_message = error_message

def protect_tokens(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Masks high-impact legal tokens before translation:
    Dates, amounts, names, case numbers, statutory sections, and negation markers.
    """
    token_map: Dict[str, str] = {}
    counter = 0

    # 1. Dates
    date_regex = re.compile(
        r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{1,2}(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})\b',
        re.IGNORECASE
    )
    for m in date_regex.finditer(text):
        m_str = m.group(0)
        tag = f"__DATE_{counter}__"
        token_map[tag] = m_str
        text = text.replace(m_str, tag, 1)
        counter += 1

    # 2. Currency
    curr_regex = re.compile(r'(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d{1,2})?(?:\s*/-)?', re.IGNORECASE)
    for m in curr_regex.finditer(text):
        m_str = m.group(0)
        tag = f"__CURR_{counter}__"
        token_map[tag] = m_str
        text = text.replace(m_str, tag, 1)
        counter += 1

    # 3. Case numbers
    case_regex = re.compile(r'\b(?:CC|OS|CR|Ref|Notice)(?:\s*(?:No\.?|Number|Case))?[\s/_-]+[A-Za-z0-9/._-]+\b', re.IGNORECASE)
    for m in case_regex.finditer(text):
        m_str = m.group(0).rstrip(".")
        tag = f"__CASE_{counter}__"
        token_map[tag] = m_str
        text = text.replace(m_str, tag, 1)
        counter += 1

    # 4. Legal Names with Honorifics
    name_regex = re.compile(r'\b(?:Sri|Smt|Shri|Mr\.?|Mrs\.?|Ms\.?|Dr\.?)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b')
    for m in name_regex.finditer(text):
        m_str = m.group(0)
        tag = f"__NAME_{counter}__"
        token_map[tag] = m_str
        text = text.replace(m_str, tag, 1)
        counter += 1

    # 5. Statutory sections
    stat_regex = re.compile(r'\b(?:Section|Sec\.?|u/s)\s*\d+[A-Za-z]?(?:\s*\([0-9a-zA-Z]+\))*', re.IGNORECASE)
    for m in stat_regex.finditer(text):
        m_str = m.group(0)
        tag = f"__STAT_{counter}__"
        token_map[tag] = m_str
        text = text.replace(m_str, tag, 1)
        counter += 1

    # 6. Critical Legal Negation Markers
    neg_regex = re.compile(r'\b(?:without\s+fail|failure\s+to\s+appear|not\s+guilty|do\s+not\s+ignore|not\s+later\s+than|shall\s+not)\b', re.IGNORECASE)
    for m in neg_regex.finditer(text):
        m_str = m.group(0)
        tag = f"__NEG_{counter}__"
        token_map[tag] = m_str
        text = text.replace(m_str, tag, 1)
        counter += 1

    return text, token_map

def restore_tokens(text: str, token_map: Dict[str, str]) -> str:
    """Restores the exact original token strings."""
    for tag, val in token_map.items():
        text = text.replace(tag, val)
    return text

def validate_translation_fidelity(
    source_explanation: str,
    translated_text: str,
    token_map: Dict[str, str]
) -> TranslationValidationResult:
    """
    Step 6 in Required Workflow:
    Multi-dimensional Verification:
    1. Confirms all protected values (dates, amounts, case numbers, statutory sections, names) appear intact.
    2. Confirms negation was preserved and not inverted.
    3. Confirms modal veracity (mandatory directives are not softened to optional).
    4. Confirms conditions are not inverted.
    5. Confirms coercive warnings (arrest, warrant) are preserved.
    """
    missing_tokens = []
    preserved_tokens = []
    errors = []
    
    # 1. Token Preservation Check
    for tag, raw_val in token_map.items():
        if tag.startswith("__NEG_"):
            # Negation markers are semantic directives evaluated via target-language negation checks below
            continue
        clean_val = raw_val.strip().replace("/-", "").strip()
        if raw_val in translated_text or clean_val in translated_text or tag in translated_text:
            preserved_tokens.append(raw_val)
        else:
            missing_tokens.append(raw_val)
            if any(c in raw_val for c in ["₹", "Rs", "INR"]):
                errors.append(f"MISSING_AMOUNT: Demanded sum '{raw_val}' missing or corrupted.")
            elif any(char.isdigit() for char in raw_val) and ("/" in raw_val or "-" in raw_val or " " in raw_val):
                errors.append(f"MISSING_DATE: Scheduled date '{raw_val}' missing or corrupted.")
            elif "CC" in raw_val or "Notice" in raw_val:
                errors.append(f"MISSING_CASE_NUMBER: Case identifier '{raw_val}' missing.")
            elif "Section" in raw_val or "Sec" in raw_val:
                errors.append(f"MISSING_STATUTE: Statutory section '{raw_val}' missing.")
            else:
                errors.append(f"MISSING_TOKEN: Protected token '{raw_val}' missing.")

    source_lower = source_explanation.lower()
    trans_lower = translated_text.lower()

    # 2. Negation Check & Negative Action Directive Check (Case B)
    negation_preserved = True
    is_source_negative_action = any(k in source_lower for k in [
        "not required to appear", "need not appear", "do not appear", "shall not appear", "no need to appear", "payment is not required", "waived"
    ])

    if is_source_negative_action:
        has_negative_marker = any(k in trans_lower for k in [
            "అవసరం లేదు", "కాకూడదు", "మినహాయింపు", "not required", "need not", "do not"
        ])
        has_inverted_mandatory = any(k in trans_lower for k in [
            "తప్పకుండా హాజరు కావాలి", "హాజరు కావలెను", "తప్పక హాజరు", "తప్పకుండా చెల్లించాలి"
        ])
        if not has_negative_marker or has_inverted_mandatory:
            negation_preserved = False
            errors.append("NEGATION_MISMATCH: Negative instruction was omitted or inverted into positive obligation.")

    if "without fail" in source_lower:
        has_telugu_neg = "తప్పకుండా" in trans_lower or "తప్పక" in trans_lower or "without fail" in trans_lower
        if not has_telugu_neg:
            negation_preserved = False
            errors.append("NEGATION_MISMATCH: Mandatory 'without fail' directive was omitted or inverted.")

    if "failure to appear" in source_lower or "if you fail to appear" in source_lower:
        has_fail_marker = "హాజరు కాకపోతే" in trans_lower or "విఫలమైతే" in trans_lower or "failure to appear" in trans_lower
        if not has_fail_marker:
            negation_preserved = False
            errors.append("NEGATION_MISMATCH: 'Failure to appear' condition was omitted or inverted.")

    # 3. Modal & Mandatory Gravity Check
    modal_preserved = True
    is_source_mandatory = any(k in source_lower for k in ["must", "shall", "required to", "compulsory", "without fail"]) and not is_source_negative_action
    is_source_optional = any(k in source_lower for k in ["may appear", "optional", "at your discretion", "if you wish"])

    if is_source_mandatory:
        # Mandatory must not be softened to purely permissive without mandatory markers
        if ("కావచ్చు" in trans_lower or "ఐచ్ఛికం" in trans_lower) and not ("చేయాలి" in trans_lower or "తప్పకుండా" in trans_lower or "హాజరు కావాలి" in trans_lower or "హాజరు కాకపోతే" in trans_lower):
            modal_preserved = False
            errors.append("MODAL_DISTORTION: Mandatory directive softened to optional.")

    if is_source_optional and not is_source_mandatory:
        # Optional must not be elevated to mandatory
        if "తప్పకుండా" in trans_lower or "తప్పక" in trans_lower:
            modal_preserved = False
            errors.append("MODAL_DISTORTION: Optional permission elevated to mandatory command.")

    # 4. Conditional Inversion Check
    conditional_preserved = True
    if "failure to appear" in source_lower or "if you fail to appear" in source_lower:
        if "హాజరైనప్పుడు" in trans_lower and not ("కాకపోతే" in trans_lower or "విఫలమైతే" in trans_lower):
            conditional_preserved = False
            errors.append("CONDITIONAL_INVERSION: Negative default condition inverted to affirmative appearance.")

    # 5. Coercive Warning Check
    warning_preserved = True
    if "arrest" in source_lower or "warrant" in source_lower:
        has_warning = "అరెస్ట్" in trans_lower or "వారెంట్" in trans_lower or "arrest" in trans_lower or "warrant" in trans_lower
        if not has_warning:
            warning_preserved = False
            errors.append("WARNING_OMISSION: Coercive consequences (arrest/warrant) omitted in translation.")

    # 6. Inferred Date Check (Case E: no implied date insertion)
    has_date_in_source = bool(re.search(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b|__token_date_', source_lower))
    if not has_date_in_source and "సదరు తేదీన" in trans_lower:
        errors.append("INFERRED_FACT: Inferred appearance date ('సదరు తేదీన') when no date exists in source.")

    is_valid = len(missing_tokens) == 0 and negation_preserved and modal_preserved and conditional_preserved and warning_preserved
    error_msg = "; ".join(errors) if errors else None

    return TranslationValidationResult(
        is_valid=is_valid,
        preserved_tokens=preserved_tokens,
        missing_tokens=missing_tokens,
        negation_preserved=negation_preserved,
        modal_preserved=modal_preserved,
        conditional_preserved=conditional_preserved,
        warning_preserved=warning_preserved,
        errors=errors,
        error_message=error_msg
    )

class DocumentExplanation:
    """
    Six-Field Architectural Information Separation Model:
    1. original_extracted_text: Verbatim raw text extracted from source blocks.
    2. verified_source_facts: Structured entities validated against source blocks.
    3. simplified_explanation: Factual explanation in simple plain English.
    4. regional_translation: Translation produced by a verified external/grounded provider.
       Set to None if provider is unconfigured or translation validation fails.
    5. validation_status: Typed status (SUPPORTED, BLOCKED_TOKEN_MISMATCH, BLOCKED_MODAL_DISTORTION, BLOCKED_CONDITIONAL_INVERSION, PROVIDER_UNAVAILABLE).
    6. approved_spoken_output: Safe text approved for TTS synthesis.
       Safety Rule: When regional translation is unavailable, NoticeSaathi speaks the regional
       limitation announcement. It NEVER speaks English automatically to a user who selected Telugu!
    """
    def __init__(
        self,
        original_extracted_text: str,
        verified_source_facts: List[Dict[str, Any]],
        simplified_explanation: str,
        regional_translation: Optional[str] = None,
        translation_provider_name: str = "none",
        is_translation_verified: bool = False,
        validation_status: str = "SUPPORTED",
        target_language: str = "te-IN",
        allow_english_audio: bool = False
    ):
        self.original_extracted_text = original_extracted_text
        self.verified_source_facts = verified_source_facts
        self.simplified_explanation = simplified_explanation
        self.regional_translation = regional_translation
        self.translation_provider_name = translation_provider_name
        self.is_translation_verified = is_translation_verified
        self.validation_status = validation_status
        self.target_language = target_language
        self.allow_english_audio = allow_english_audio

        # SPEECH SYNTHESIS SAFETY RULE:
        # A user who selected Telugu must NEVER receive English speech automatically.
        if target_language.startswith("en"):
            self.approved_spoken_output = self.simplified_explanation
        elif self.is_translation_verified and self.regional_translation:
            self.approved_spoken_output = self.regional_translation
        elif self.allow_english_audio:
            # User explicitly opted into English audio
            self.approved_spoken_output = self.simplified_explanation
        else:
            # Regional announcement that translation is unavailable; offers English option
            self.approved_spoken_output = translate_ui_label("translation_unavailable", target_language)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_extracted_text": self.original_extracted_text,
            "verified_source_facts": self.verified_source_facts,
            "simplified_explanation": self.simplified_explanation,
            "regional_translation": self.regional_translation,
            "translation_provider_name": self.translation_provider_name,
            "is_translation_verified": self.is_translation_verified,
            "validation_status": self.validation_status,
            "target_language": self.target_language,
            "approved_spoken_output": self.approved_spoken_output,
            "disclaimer": None if self.is_translation_verified else translate_ui_label("translation_unavailable", self.target_language)
        }

class TranslationService:
    def __init__(self):
        # Initialise modular providers: Google, Azure, Gemini, and Local Grounded Legal Grammar
        self.google_provider = GoogleCloudTranslationProvider()
        self.azure_provider = AzureTranslatorProvider()
        self.gemini_provider = GeminiTranslationProvider()
        self.grounded_provider = GroundedLegalExplanationProvider()

        self.cloud_providers: List[BaseTranslationProvider] = [
            self.google_provider,
            self.azure_provider,
            self.gemini_provider
        ]

    def translate_and_validate(
        self,
        simplified_en: str,
        target_language: str = "te-IN",
        has_cloud_consent: bool = False
    ) -> Tuple[Optional[str], str, bool, str]:
        """
        Executes full workflow:
        1. Token Protection
        2. Execution of configured providers with Data Minimization & Consent checks
        3. Token Restoration
        4. Multi-dimensional Semantic & Fidelity Validation
        Returns (translated_text, provider_name, is_valid, validation_status)
        """
        if target_language.startswith("en"):
            return simplified_en, "native_en", True, "SUPPORTED"

        protected_text, token_map = protect_tokens(simplified_en)

        # 1. Try configured cloud providers (only if user consented to cloud translation)
        if has_cloud_consent:
            for provider in self.cloud_providers:
                if not provider.is_configured:
                    continue
                try:
                    result = provider.translate(protected_text, "en", target_language)
                    if result and result.translated_text:
                        restored = restore_tokens(result.translated_text, token_map)
                        v_res = validate_translation_fidelity(simplified_en, restored, token_map)
                        if v_res.is_valid:
                            return restored, provider.provider_name, True, "SUPPORTED"
                        else:
                            # Flag specific violation
                            status_code = v_res.errors[0].split(":")[0] if v_res.errors else "FIDELITY_MISMATCH"
                            return None, provider.provider_name, False, f"BLOCKED_{status_code}"
                except TranslationError as te:
                    logger.warning(f"Provider {provider.provider_name} failed: {te.error_code}")
                    continue

        # 2. Try Local Grounded Legal Grammar Provider
        try:
            res_grounded = self.grounded_provider.translate(protected_text, "en", target_language)
            if res_grounded and res_grounded.translated_text:
                restored = restore_tokens(res_grounded.translated_text, token_map)
                v_res = validate_translation_fidelity(simplified_en, restored, token_map)
                if v_res.is_valid:
                    return restored, self.grounded_provider.provider_name, True, "SUPPORTED"
                else:
                    status_code = v_res.errors[0].split(":")[0] if v_res.errors else "FIDELITY_MISMATCH"
                    return None, self.grounded_provider.provider_name, False, f"BLOCKED_{status_code}"
        except TranslationError:
            pass

        return None, "none", False, "PROVIDER_UNAVAILABLE"

    def generate_explanation(
        self,
        original_text: str,
        facts: List[Dict[str, Any]],
        simplified_en: str,
        target_language: str = "te-IN",
        allow_english_audio: bool = False,
        has_cloud_consent: bool = False
    ) -> DocumentExplanation:
        """
        Full 8-step explanation workflow adhering strictly to pre-pilot release gates.
        """
        translated_text, provider_name, is_valid, val_status = self.translate_and_validate(
            simplified_en,
            target_language,
            has_cloud_consent=has_cloud_consent
        )

        return DocumentExplanation(
            original_extracted_text=original_text,
            verified_source_facts=facts,
            simplified_explanation=simplified_en,
            regional_translation=translated_text,
            translation_provider_name=provider_name,
            is_translation_verified=is_valid,
            validation_status=val_status,
            target_language=target_language,
            allow_english_audio=allow_english_audio
        )

    def explain_in_regional_language(
        self,
        text_en: str,
        target_language: str = "te-IN",
        fact_type: Optional[str] = None,
        fact_value: Optional[str] = None
    ) -> Dict[str, Any]:
        """Backwards compatibility helper for existing API handlers."""
        expl = self.generate_explanation(
            original_text=text_en,
            facts=[],
            simplified_en=text_en,
            target_language=target_language,
            allow_english_audio=False
        )
        return {
            "translated_text": expl.regional_translation or expl.simplified_explanation,
            "is_machine_translated": expl.is_translation_verified,
            "language": target_language,
            "approved_spoken_output": expl.approved_spoken_output
        }

# Backwards compatibility alias for existing code
GroundedRegionalTemplateProvider = GroundedLegalExplanationProvider

translation_service = TranslationService()
