import httpx
from typing import Optional
from backend.config import settings
from backend.modules.translation.providers.base import (
    BaseTranslationProvider,
    ProviderConfig,
    TranslationError
)

class GeminiTranslationProvider(BaseTranslationProvider):
    """
    Adapter for Google Gemini Multilingual API (Gemini 1.5 Flash).
    Authoritative Spec:
      Endpoint: POST https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=<API_KEY>
      Payload:
        {
          "contents": [ { "parts": [ { "text": "<prompt>" } ] } ],
          "generationConfig": { "temperature": 0.0, "topK": 1 }
        }
      Response:
        { "candidates": [ { "content": { "parts": [ { "text": "<text>" } ] } } ] }
    """
    def __init__(
        self,
        api_key: str = settings.GEMINI_API_KEY,
        endpoint: str = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        timeout_seconds: float = 20.0,
        max_retries: int = settings.TRANSLATION_MAX_RETRIES
    ):
        config = ProviderConfig(
            provider_name="gemini_multilingual",
            api_key=api_key.strip() if api_key else "",
            endpoint=endpoint,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries
        )
        super().__init__(config)

    def _execute_request(self, text: str, source_lang: str, target_lang: str) -> str:
        url = f"{self.config.endpoint}?key={self.config.api_key}"
        prompt = (
            f"You are a certified legal translator for Indian regional languages.\n"
            f"Translate the following plain-language legal notice explanation into {target_lang} (native script).\n"
            f"Rules:\n"
            f"- Preserve all placeholder tags (e.g. __DATE_0__, __CURR_1__, __CASE_2__, __NAME_3__, __STAT_4__, __NEG_5__) exactly as given without modifying capitalization, punctuation, or spelling.\n"
            f"- Do NOT soften or eliminate mandatory directives ('must', 'shall', 'required').\n"
            f"- Return ONLY the translated string in native script. No preamble, no quotes, no markdown, no notes.\n\n"
            f"Source text:\n{text}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "topK": 1}
        }

        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                res = client.post(url, json=payload)
                
                if res.status_code == 200:
                    data = res.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"].strip()
                    raise TranslationError(
                        error_code="MALFORMED_RESPONSE",
                        message="Missing candidate text in Gemini response.",
                        status_code=200,
                        retryable=False
                    )

                elif res.status_code in [401, 403]:
                    raise TranslationError(
                        error_code="AUTH_FAILURE",
                        message=f"Gemini API key rejected: {res.text}",
                        status_code=res.status_code,
                        retryable=False
                    )

                elif res.status_code == 429:
                    raise TranslationError(
                        error_code="RATE_LIMIT",
                        message="Gemini API rate limit exceeded.",
                        status_code=429,
                        retryable=True
                    )

                elif res.status_code >= 500:
                    raise TranslationError(
                        error_code="SERVER_ERROR",
                        message=f"Gemini server error: {res.status_code}",
                        status_code=res.status_code,
                        retryable=True
                    )

                else:
                    raise TranslationError(
                        error_code="HTTP_ERROR",
                        message=f"HTTP {res.status_code}: {res.text}",
                        status_code=res.status_code,
                        retryable=False
                    )

        except httpx.TimeoutException as e:
            raise TranslationError(
                error_code="TIMEOUT",
                message=f"Gemini request timed out after {self.config.timeout_seconds}s",
                retryable=True
            ) from e
        except httpx.RequestError as e:
            raise TranslationError(
                error_code="NETWORK_ERROR",
                message=f"Network error during Gemini request: {str(e)}",
                retryable=True
            ) from e

