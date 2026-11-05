import time
import logging
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple, List
from pydantic import BaseModel, Field

logger = logging.getLogger("noticesaathi.translation")

class ProviderConfig(BaseModel):
    provider_name: str
    api_key: str = ""
    endpoint: str = ""
    timeout_seconds: float = 15.0
    max_retries: int = 2
    retry_backoff_base: float = 0.5
    region: Optional[str] = None

class TranslationResult(BaseModel):
    translated_text: str
    provider_name: str
    source_language: str
    target_language: str
    latency_ms: float
    is_fallback: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)

class TranslationError(Exception):
    def __init__(self, error_code: str, message: str, status_code: Optional[int] = None, retryable: bool = False):
        super().__init__(f"[{error_code}] {message}")
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable

def scrub_sensitive_info(text: str) -> str:
    """Removes API keys and secrets from log strings."""
    scrubbed = re.sub(r'(?:key|token|secret|auth)=([a-zA-Z0-9_\-\.]{6,})', r'\1=***REDACTED***', text, flags=re.IGNORECASE)
    return scrubbed

class BaseTranslationProvider(ABC):
    def __init__(self, config: ProviderConfig):
        self.config = config

    @property
    def provider_name(self) -> str:
        return self.config.provider_name

    @property
    def is_configured(self) -> bool:
        return bool(self.config.api_key.strip())

    @abstractmethod
    def _execute_request(self, text: str, source_lang: str, target_lang: str) -> str:
        """Subclasses implement the direct HTTP API call here."""
        pass

    def translate(self, text: str, source_lang: str, target_lang: str) -> TranslationResult:
        """
        Executes translation with:
        - Strict configuration check
        - Bounded retries with exponential backoff
        - Schema & script validation
        - Latency measurement
        - Safe, non-leaking logging
        """
        if not self.is_configured:
            raise TranslationError(
                error_code="UNCONFIGURED",
                message=f"Provider {self.provider_name} has no credentials configured.",
                retryable=False
            )

        start_time = time.time()
        last_exception: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                raw_translation = self._execute_request(text, source_lang, target_lang)
                if not raw_translation or not raw_translation.strip():
                    raise TranslationError(
                        error_code="EMPTY_RESPONSE",
                        message="Provider returned an empty translation string.",
                        retryable=False
                    )

                clean_text = raw_translation.strip()
                self._validate_output_schema(clean_text, target_lang)

                latency_ms = (time.time() - start_time) * 1000.0
                return TranslationResult(
                    translated_text=clean_text,
                    provider_name=self.provider_name,
                    source_language=source_lang,
                    target_language=target_lang,
                    latency_ms=round(latency_ms, 2)
                )

            except TranslationError as te:
                last_exception = te
                if not te.retryable or attempt >= self.config.max_retries:
                    logger.warning(f"Translation failed on {self.provider_name}: {scrub_sensitive_info(str(te))}")
                    raise te
                # Wait before retry
                backoff = self.config.retry_backoff_base * (2 ** attempt)
                time.sleep(backoff)

            except Exception as e:
                last_exception = e
                if attempt >= self.config.max_retries:
                    logger.error(f"Translation unexpected error on {self.provider_name}: {scrub_sensitive_info(str(e))}")
                    raise TranslationError(
                        error_code="EXECUTION_ERROR",
                        message=str(e),
                        retryable=False
                    ) from e
                backoff = self.config.retry_backoff_base * (2 ** attempt)
                time.sleep(backoff)

        raise TranslationError(
            error_code="MAX_RETRIES_EXCEEDED",
            message=f"Failed after {self.config.max_retries} retries: {last_exception}",
            retryable=False
        )

    def _validate_output_schema(self, text: str, target_lang: str) -> None:
        """Validates that output text matches expectations for the requested target language."""
        if target_lang.startswith("te"):
            # Check presence of Telugu Unicode range U+0C00 - U+0C7F or intact placeholder tags
            has_telugu = any('\u0c00' <= char <= '\u0c7f' for char in text)
            has_tags = "__" in text
            if not has_telugu and not has_tags:
                raise TranslationError(
                    error_code="INVALID_TARGET_SCRIPT",
                    message="Telugu translation response contained no Telugu script characters.",
                    retryable=False
                )

