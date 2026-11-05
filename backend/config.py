import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "NoticeSaathi"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "notice-saathi-development-secret-key-change-in-prod-32bytes")
    
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

settings = Settings()

# Ensure local storage directories exist
Path(settings.STORAGE_LOCAL_DIR).mkdir(parents=True, exist_ok=True)
Path(f"{settings.STORAGE_LOCAL_DIR}/originals").mkdir(parents=True, exist_ok=True)
Path(f"{settings.STORAGE_LOCAL_DIR}/pages").mkdir(parents=True, exist_ok=True)
Path(f"{settings.STORAGE_LOCAL_DIR}/audio").mkdir(parents=True, exist_ok=True)
