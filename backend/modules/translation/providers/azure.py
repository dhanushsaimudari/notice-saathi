import httpx
from typing import Optional
from backend.config import settings
from backend.modules.translation.providers.base import (
    BaseTranslationProvider,
    ProviderConfig,
    TranslationError
)

class AzureTranslatorProvider(BaseTranslationProvider):
    """
    Adapter for Azure AI Translator REST API v3.0.
    Authoritative Spec:
      Endpoint: POST https://api.cognitive.microsofttranslator.com/translate?api-version=3.0&from=<from>&to=<to>
      Headers:
        Ocp-Apim-Subscription-Key: <KEY>
        Ocp-Apim-Subscription-Region: <REGION>
        Content-Type: application/json
      Request Body:
        [ { "Text": "<text>" } ]
      Response Body:
        [
          {
            "translations": [
              { "text": "<translated_text>", "to": "te" }
            ]
          }
        ]
    """
    def __init__(
        self,
        api_key: str = settings.AZURE_TRANSLATOR_KEY,
        region: str = settings.AZURE_TRANSLATOR_REGION,
        endpoint: str = "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0",
        timeout_seconds: float = settings.TRANSLATION_TIMEOUT_SECONDS,
        max_retries: int = settings.TRANSLATION_MAX_RETRIES
    ):
        config = ProviderConfig(
            provider_name="azure_translator",
            api_key=api_key.strip() if api_key else "",
            endpoint=endpoint,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            region=region
        )
        super().__init__(config)

    def _execute_request(self, text: str, source_lang: str, target_lang: str) -> str:
        source_code = source_lang.split("-")[0].lower()
        target_code = target_lang.split("-")[0].lower()

        url = f"{self.config.endpoint}&from={source_code}&to={target_code}"
        headers = {
            "Ocp-Apim-Subscription-Key": self.config.api_key,
            "Content-Type": "application/json"
        }
        if self.config.region:
            headers["Ocp-Apim-Subscription-Region"] = self.config.region

        payload = [{"Text": text}]

        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                res = client.post(url, headers=headers, json=payload)
                
                if res.status_code == 200:
                    data = res.json()
                    if isinstance(data, list) and len(data) > 0 and "translations" in data[0]:
                        return data[0]["translations"][0]["text"]
                    raise TranslationError(
                        error_code="MALFORMED_RESPONSE",
                        message="Missing 'translations' in Azure Translator response array.",
                        status_code=200,
                        retryable=False
                    )

                elif res.status_code == 401 or res.status_code == 403:
                    raise TranslationError(
                        error_code="AUTH_FAILURE",
                        message=f"Azure Translator authentication failed: {res.text}",
                        status_code=res.status_code,
                        retryable=False
                    )

                elif res.status_code == 429:
                    raise TranslationError(
                        error_code="RATE_LIMIT",
                        message="Azure Translator rate limit exceeded.",
                        status_code=429,
                        retryable=True
                    )

                elif res.status_code >= 500:
                    raise TranslationError(
                        error_code="SERVER_ERROR",
                        message=f"Azure Translator server error: {res.status_code}",
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
                message=f"Azure Translator timed out after {self.config.timeout_seconds}s",
                retryable=True
            ) from e
        except httpx.RequestError as e:
            raise TranslationError(
                error_code="NETWORK_ERROR",
                message=f"Network error during Azure Translator request: {str(e)}",
                retryable=True
            ) from e

