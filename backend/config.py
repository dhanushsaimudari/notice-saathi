import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List, Optional

DEFAULT_DEV_SECRET_KEY: str = "notice-saathi-development-secret-key-change-in-prod-32bytes"
DEFAULT_DEV_CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]
WEAK_SECRETS: List[str] = [
    "secret", "changeme", "password", "admin", "123456", "12345678",
    "12345678901234567890123456789012",
    DEFAULT_DEV_SECRET_KEY
]

def parse_cors_origins(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        try:
            import json
            parsed = json.loads(raw)
            return [str(o).strip() for o in parsed if str(o).strip()]
        except Exception:
            pass
    return [o.strip() for o in raw.split(",") if o.strip()]

class Settings(BaseSettings):
    PROJECT_NAME: str = "NoticeSaathi"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    # Outside development/test, default DEBUG to False
    DEBUG: bool = os.getenv(
        "DEBUG",
        "true" if os.getenv("ENVIRONMENT", "development").lower() in ["development", "dev", "local", "test"] else "false"
    ).lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", DEFAULT_DEV_SECRET_KEY)

    # CORS Configuration
    CORS_ALLOWED_ORIGINS: List[str] = []
    CORS_ALLOW_CREDENTIALS: bool = True

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./notice_saathi_v2.db")

    # Storage
    STORAGE_LOCAL_DIR: str = os.getenv("STORAGE_LOCAL_DIR", "./data/storage")
    MAX_UPLOAD_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    MAX_PAGES_PER_DOC: int = 20
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".jpg", ".jpeg", ".png"]
    ALLOWED_MIME_TYPES: List[str] = ["application/pdf", "image/jpeg", "image/png"]

    # Gnani AI Configuration
    GNANI_API_KEY: str = os.getenv("GNANI_API_KEY", "")
    GNANI_BASE_URL: str = os.getenv("GNANI_BASE_URL", "https://api.vachana.ai")
    GNANI_STT_ENDPOINT: str = "/stt/v3"
    GNANI_TTS_ENDPOINT: str = "/api/v1/tts/inference"
    GNANI_TTS_SSE_ENDPOINT: str = "/api/v1/tts/sse"
    GNANI_TTS_MODEL: str = os.getenv("GNANI_TTS_MODEL", "timbre-v2.5")

    # Translation Provider Configuration
    GOOGLE_TRANSLATE_API_KEY: str = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    AZURE_TRANSLATOR_KEY: str = os.getenv("AZURE_TRANSLATOR_KEY", "")
    AZURE_TRANSLATOR_REGION: str = os.getenv("AZURE_TRANSLATOR_REGION", "centralindia")
    TRANSLATION_PROVIDER: str = os.getenv("TRANSLATION_PROVIDER", "auto")
    TRANSLATION_TIMEOUT_SECONDS: float = float(os.getenv("TRANSLATION_TIMEOUT_SECONDS", "15.0"))
    TRANSLATION_MAX_RETRIES: int = int(os.getenv("TRANSLATION_MAX_RETRIES", "2"))
    REQUIRE_CONSENT_FOR_CLOUD_TRANSLATION: bool = os.getenv("REQUIRE_CONSENT_FOR_CLOUD_TRANSLATION", "true").lower() == "true"

    # Supported Languages
    SUPPORTED_LANGUAGES: List[str] = ["en-IN", "te-IN", "hi-IN", "ta-IN", "kn-IN"]
    DEFAULT_LANGUAGE: str = "te-IN"  # Target persona default from project requirements

    # Session & Retention
    GUEST_SESSION_EXPIRE_HOURS: int = 24
    RETENTION_HOURS: int = 48

    model_config = {
        "case_sensitive": True,
        "env_file": ".env",
        "extra": "ignore"
    }

    def __init__(self, **values):
        super().__init__(**values)
        raw_cors = os.getenv("CORS_ALLOWED_ORIGINS")
        if raw_cors:
            self.CORS_ALLOWED_ORIGINS = parse_cors_origins(raw_cors)
        elif not self.CORS_ALLOWED_ORIGINS:
            if self.ENVIRONMENT.lower() in ["development", "dev", "local", "test"]:
                self.CORS_ALLOWED_ORIGINS = DEFAULT_DEV_CORS_ORIGINS.copy()
            else:
                self.CORS_ALLOWED_ORIGINS = []

    def validate_production_configuration(self) -> None:
        """
        Enforces strict security invariants in production environments.
        Raises ValueError with clear, actionable diagnostics if violated.
        """
        is_prod = self.ENVIRONMENT.lower() in ["production", "prod", "staging"]
        if not is_prod:
            return

        # 1. SECRET_KEY validation
        if not self.SECRET_KEY or self.SECRET_KEY.strip() == "":
            raise ValueError(
                "CRITICAL_SECURITY_ERROR: Production SECRET_KEY is missing. "
                "Set a high-entropy secret (at least 32 characters) via the SECRET_KEY environment variable."
            )
        if self.SECRET_KEY in WEAK_SECRETS:
            raise ValueError(
                "CRITICAL_SECURITY_ERROR: Production SECRET_KEY cannot use the development fallback key or a known weak secret. "
                "Generate a cryptographically secure key (e.g. `openssl rand -hex 32`)."
            )
        if len(self.SECRET_KEY) < 32:
            raise ValueError(
                f"CRITICAL_SECURITY_ERROR: Production SECRET_KEY is too short ({len(self.SECRET_KEY)} chars). "
                "Minimum length is 32 characters."
            )

        # 2. CORS validation
        if not self.CORS_ALLOWED_ORIGINS:
            raise ValueError(
                "CRITICAL_SECURITY_ERROR: In production, CORS_ALLOWED_ORIGINS must be explicitly configured "
                "with trusted origins (e.g., 'https://app.example.com')."
            )
        if "*" in self.CORS_ALLOWED_ORIGINS:
            if self.CORS_ALLOW_CREDENTIALS:
                raise ValueError(
                    "CRITICAL_SECURITY_ERROR: Wildcard origin '*' is strictly prohibited when CORS credentials "
                    "are enabled (W3C CORS credentialed request violation)."
                )
            raise ValueError(
                "CRITICAL_SECURITY_ERROR: Wildcard origin '*' is prohibited in production. "
                "Specify explicit domain names in CORS_ALLOWED_ORIGINS."
            )

        # 3. DEBUG validation
        if self.DEBUG:
            raise ValueError(
                "CRITICAL_SECURITY_ERROR: DEBUG must be set to False in production environments "
                "to prevent exposing debug traces, framework internals, or environment state."
            )

settings = Settings()

# Ensure local storage directories exist
Path(settings.STORAGE_LOCAL_DIR).mkdir(parents=True, exist_ok=True)
Path(f"{settings.STORAGE_LOCAL_DIR}/originals").mkdir(parents=True, exist_ok=True)
Path(f"{settings.STORAGE_LOCAL_DIR}/pages").mkdir(parents=True, exist_ok=True)
Path(f"{settings.STORAGE_LOCAL_DIR}/audio").mkdir(parents=True, exist_ok=True)
