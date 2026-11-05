import httpx
from typing import Optional
from backend.config import settings
from backend.modules.translation.providers.base import (
    BaseTranslationProvider,
    ProviderConfig,
    TranslationError
)

class GoogleCloudTranslationProvider(BaseTranslationProvider):
    """
    Adapter for Google Cloud Translation v2/v3 REST API.
    Authoritative Spec:
      Endpoint: POST https://translation.googleapis.com/language/translate/v2?key=<API_KEY>
      Request Payload:
        {
          "q": "<text>",
          "source": "en",
          "target": "te",
          "format": "text"
        }
      Response:
        {
          "data": {
            "translations": [
              { "translatedText": "<text>" }
            ]
          }
        }
    """
    def __init__(
        self,
        api_key: str = settings.GOOGLE_TRANSLATE_API_KEY,
        endpoint: str = "https://translation.googleapis.com/language/translate/v2",
        timeout_seconds: float = settings.TRANSLATION_TIMEOUT_SECONDS,
        max_retries: int = settings.TRANSLATION_MAX_RETRIES
    ):
        config = ProviderConfig(
            provider_name="google_cloud_translate",
            api_key=api_key.strip() if api_key else "",
            endpoint=endpoint,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries
        )
        super().__init__(config)

    def _execute_request(self, text: str, source_lang: str, target_lang: str) -> str:
        source_code = source_lang.split("-")[0].lower()
        target_code = target_lang.split("-")[0].lower()

        url = f"{self.config.endpoint}?key={self.config.api_key}"
        payload = {
            "q": text,
            "source": source_code,
            "target": target_code,
            "format": "text"
        }

        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                res = client.post(url, json=payload)
                
                if res.status_code == 200:
                    data = res.json()
                    if "data" in data and "translations" in data["data"] and len(data["data"]["translations"]) > 0:
                        return data["data"]["translations"][0]["translatedText"]
                    raise TranslationError(
                        error_code="MALFORMED_RESPONSE",
                        message="Missing 'data.translations' array in Google Cloud Translate response.",
                        status_code=200,
                        retryable=False
                    )

                elif res.status_code == 401 or res.status_code == 403:
                    raise TranslationError(
                        error_code="AUTH_FAILURE",
                        message=f"Google Cloud Translation authentication failed: {res.text}",
                        status_code=res.status_code,
                        retryable=False
                    )

                elif res.status_code == 429:
                    raise TranslationError(
                        error_code="RATE_LIMIT",
                        message="Google Cloud Translation rate limit reached.",
                        status_code=429,
                        retryable=True
                    )

                elif res.status_code >= 500:
                    raise TranslationError(
                        error_code="SERVER_ERROR",
                        message=f"Google Cloud Translation server error: {res.status_code}",
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
                message=f"Google Cloud Translation timed out after {self.config.timeout_seconds}s",
                retryable=True
            ) from e
        except httpx.RequestError as e:
            raise TranslationError(
                error_code="NETWORK_ERROR",
                message=f"Network communication failure: {str(e)}",
                retryable=True
            ) from e

