import pytest
import json
from unittest.mock import MagicMock
from backend.config import Settings, parse_cors_origins, DEFAULT_DEV_SECRET_KEY
from services.api.main import safe_exception_handler

def test_development_configuration_defaults(monkeypatch):
    """Verifies that development configuration defaults are convenient and valid."""
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
    cfg = Settings(ENVIRONMENT="development", SECRET_KEY=DEFAULT_DEV_SECRET_KEY)
    assert cfg.ENVIRONMENT == "development"
    assert cfg.DEBUG is True
    assert cfg.SECRET_KEY == DEFAULT_DEV_SECRET_KEY
    assert len(cfg.CORS_ALLOWED_ORIGINS) > 0
    assert "http://localhost:3000" in cfg.CORS_ALLOWED_ORIGINS
    assert cfg.CORS_ALLOW_CREDENTIALS is True
    # In dev, validate_production_configuration should pass without error
    cfg.validate_production_configuration()

def test_valid_production_configuration():
    """Verifies that a well-configured production setting passes validation."""
    cfg = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="c" * 32,
        CORS_ALLOWED_ORIGINS=["https://noticesaathi.example.gov.in"]
    )
    assert cfg.ENVIRONMENT == "production"
    assert cfg.DEBUG is False
    assert len(cfg.SECRET_KEY) == 32
    assert cfg.CORS_ALLOWED_ORIGINS == ["https://noticesaathi.example.gov.in"]
    cfg.validate_production_configuration()

def test_missing_or_empty_production_secret():
    """Verifies that empty or missing SECRET_KEY in production raises critical security error."""
    cfg = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="",
        CORS_ALLOWED_ORIGINS=["https://noticesaathi.example.gov.in"]
    )
    with pytest.raises(ValueError, match="CRITICAL_SECURITY_ERROR: Production SECRET_KEY is missing"):
        cfg.validate_production_configuration()

def test_weak_or_fallback_production_secret():
    """Verifies that using the dev fallback key in production is rejected."""
    cfg = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY=DEFAULT_DEV_SECRET_KEY,
        CORS_ALLOWED_ORIGINS=["https://noticesaathi.example.gov.in"]
    )
    with pytest.raises(ValueError, match="cannot use the development fallback key"):
        cfg.validate_production_configuration()

    cfg_short = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="short-secret-key-16",
        CORS_ALLOWED_ORIGINS=["https://noticesaathi.example.gov.in"]
    )
    with pytest.raises(ValueError, match="too short"):
        cfg_short.validate_production_configuration()

def test_wildcard_cors_rejection_in_production():
    """Verifies that wildcard origin in production with credentials raises error."""
    cfg_wildcard = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="x" * 32,
        CORS_ALLOWED_ORIGINS=["*"],
        CORS_ALLOW_CREDENTIALS=True
    )
    with pytest.raises(ValueError, match="Wildcard origin '\\*' is strictly prohibited when CORS credentials are enabled"):
        cfg_wildcard.validate_production_configuration()

def test_unconfigured_cors_in_production():
    """Verifies that empty CORS origins list in production raises error."""
    cfg_no_cors = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="x" * 32,
        CORS_ALLOWED_ORIGINS=[]
    )
    with pytest.raises(ValueError, match="CORS_ALLOWED_ORIGINS must be explicitly configured"):
        cfg_no_cors.validate_production_configuration()

def test_safe_production_error_response_no_stack_trace(monkeypatch):
    """
    Verifies that when DEBUG is False, an unhandled exception returns HTTP 500
    with safe generic error JSON, and does NOT leak python stack traces or paths.
    """
    req = MagicMock()
    req.method = "GET"
    req.url.path = "/api/v1/documents"
    exc = RuntimeError("SensitiveDatabaseConnectionException: host=10.0.0.5 pass=SuperSecret")

    # 1. Test in simulated production (DEBUG=False)
    monkeypatch.setattr("backend.config.settings.DEBUG", False)
    res_prod = safe_exception_handler(req, exc)
    assert res_prod.status_code == 500
    body_prod = json.loads(res_prod.body)
    assert body_prod["code"] == "INTERNAL_SERVER_ERROR"
    assert "SensitiveDatabaseConnectionException" not in str(body_prod)
    assert "SuperSecret" not in str(body_prod)
    assert "Traceback" not in str(body_prod)

    # 2. Test in development (DEBUG=True)
    monkeypatch.setattr("backend.config.settings.DEBUG", True)
    res_dev = safe_exception_handler(req, exc)
    assert res_dev.status_code == 500
    body_dev = json.loads(res_dev.body)
    assert "detail" in body_dev
    assert "SensitiveDatabaseConnectionException" in body_dev["detail"]
