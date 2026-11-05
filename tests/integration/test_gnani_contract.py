import json
import pytest
import httpx
from backend.modules.gnani_stt.adapter import GnaniSTTAdapter
from backend.modules.gnani_tts.adapter import GnaniTTSAdapter

def test_gnani_stt_contract_request_structure(monkeypatch):
    """
    Asserts the exact URL, headers, and multipart form fields for Gnani STT.
    Endpoint: POST https://api.vachana.ai/stt/v3
    Header: X-API-Key-ID
    Form: audio_file, language_code
    """
    captured_requests = []

    def mock_post(self, url, *args, **kwargs):
        captured_requests.append({
            "url": str(url),
            "headers": kwargs.get("headers", {}),
            "files": kwargs.get("files", {}),
            "data": kwargs.get("data", {})
        })
        # Simulate official Gnani response from Document B
        mock_response = httpx.Response(
            status_code=200,
            json={
                "success": True,
                "request_id": "019fd17d-1106-7265-88ab-3ed12d029292",
                "transcript": "విచారణ తేదీ ఎప్పుడు?",
                "model": "gnani-prisma-v2.5"
            },
            request=httpx.Request("POST", str(url))
        )
        return mock_response

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    adapter = GnaniSTTAdapter(api_key="test-gnani-key-xyz", base_url="https://api.vachana.ai")
    sample_wav = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"
    result = adapter.transcribe(sample_wav, language_code="te-IN")

    assert len(captured_requests) == 1
    req = captured_requests[0]
    
    # Assert authoritative URL
    assert req["url"] == "https://api.vachana.ai/stt/v3"
    # Assert authentication header
    assert req["headers"].get("X-API-Key-ID") == "test-gnani-key-xyz"
    # Assert form payload fields
    assert "audio_file" in req["files"]
    assert req["data"].get("language_code") == "te-IN"
    # Assert response decoding
    assert result["success"] is True
    assert result["transcript"] == "విచారణ తేదీ ఎప్పుడు?"
    assert result["is_mock"] is False
    assert result["model"] == "gnani-prisma-v2.5"

def test_gnani_tts_contract_request_structure(monkeypatch):
    """
    Asserts the exact URL, headers, and JSON body for Gnani TTS.
    Endpoint: POST https://api.vachana.ai/api/v1/tts/inference
    Header: X-API-Key-ID, Content-Type: application/json
    Body: text, voice, model: timbre-v2.5, language, speed, audio_config
    """
    captured_requests = []
    fake_wav_bytes = b"RIFF....WAVEfmt ...."

    def mock_post(self, url, *args, **kwargs):
        captured_requests.append({
            "url": str(url),
            "headers": kwargs.get("headers", {}),
            "json": kwargs.get("json", {})
        })
        return httpx.Response(
            status_code=200,
            content=fake_wav_bytes,
            headers={"Content-Type": "audio/wav"},
            request=httpx.Request("POST", str(url))
        )

    monkeypatch.setattr(httpx.Client, "post", mock_post)

    adapter = GnaniTTSAdapter(api_key="test-gnani-key-abc", base_url="https://api.vachana.ai")
    audio, meta = adapter.synthesize(
        text="విచారణ తేదీ 25 నవంబర్ 2026",
        language="te-IN",
        speed=1.0
    )

    assert len(captured_requests) == 1
    req = captured_requests[0]
    
    # Assert authoritative URL
    assert req["url"] == "https://api.vachana.ai/api/v1/tts/inference"
    # Assert authentication header
    assert req["headers"].get("X-API-Key-ID") == "test-gnani-key-abc"
    assert req["headers"].get("Content-Type") == "application/json"
    
    # Assert payload structure
    payload = req["json"]
    assert payload["text"] == "విచారణ తేదీ 25 నవంబర్ 2026"
    assert payload["voice"] == "Lavanya"
    assert payload["model"] == "timbre-v2.5"
    assert payload["language"] == "te-IN"
    assert payload["speed"] == 1.0
    assert payload["audio_config"]["sample_rate"] == 48000
    assert payload["audio_config"]["encoding"] == "linear_pcm"
    assert payload["audio_config"]["container"] == "wav"

    # Assert response handling
    assert audio == fake_wav_bytes
    assert meta["is_mock"] is False
    assert meta["model"] == "timbre-v2.5"

def test_gnani_unconfigured_credentials_labeled_as_mock():
    """
    Asserts that when credentials are not configured, adapters explicitly label
    output as mock and never report as verified live API calls.
    """
    unconfigured_stt = GnaniSTTAdapter(api_key="", base_url="https://api.vachana.ai")
    stt_res = unconfigured_stt.transcribe(b"dummy_bytes", language_code="te-IN")
    assert stt_res["is_mock"] is True
    assert "GNANI_API_KEY is not configured" in stt_res["message"]

    unconfigured_tts = GnaniTTSAdapter(api_key="", base_url="https://api.vachana.ai")
    audio, meta = unconfigured_tts.synthesize("Test", language="te-IN")
    assert meta["is_mock"] is True
    assert "GNANI_API_KEY is not configured" in meta["message"]
    assert audio[:4] == b"RIFF"

def test_gnani_stt_timeout_handling(monkeypatch):
    """
    Asserts that network timeout during STT does not crash the server and returns structured error.
    """
    def mock_timeout(self, *args, **kwargs):
        raise httpx.ReadTimeout("Gnani STT connection timed out after 30s")

    monkeypatch.setattr(httpx.Client, "post", mock_timeout)

    adapter = GnaniSTTAdapter(api_key="test-key", base_url="https://api.vachana.ai")
    res = adapter.transcribe(b"dummy_wav_data", language_code="te-IN")

    assert res["success"] is False
    assert "timed out" in res["error"].lower()
    assert res["is_mock"] is False

def test_gnani_stt_invalid_credentials_401(monkeypatch):
    """
    Asserts that 401 Unauthorized responses from Gnani are cleanly captured with status code.
    """
    def mock_401(self, url, *args, **kwargs):
        return httpx.Response(
            status_code=401,
            text='{"error": "Unauthorized", "message": "Invalid API key ID"}',
            request=httpx.Request("POST", str(url))
        )

    monkeypatch.setattr(httpx.Client, "post", mock_401)

    adapter = GnaniSTTAdapter(api_key="invalid-key-123", base_url="https://api.vachana.ai")
    res = adapter.transcribe(b"dummy_wav_data", language_code="te-IN")

    assert res["success"] is False
    assert res["status_code"] == 401
    assert "Invalid API key" in res["error"]
    assert res["is_mock"] is False

def test_gnani_tts_provider_unavailable_503(monkeypatch):
    """
    Asserts that upstream 503 Provider Unavailable returns fallback audio and clear error telemetry.
    """
    def mock_503(self, url, *args, **kwargs):
        return httpx.Response(
            status_code=503,
            text="Service Temporarily Unavailable",
            request=httpx.Request("POST", str(url))
        )

    monkeypatch.setattr(httpx.Client, "post", mock_503)

    adapter = GnaniTTSAdapter(api_key="test-key", base_url="https://api.vachana.ai")
    audio, meta = adapter.synthesize("విచారణ తేదీ 25 నవంబర్ 2026", language="te-IN")

    assert meta["error_fallback"] is True
    assert meta["upstream_status"] == 503
    assert audio[:4] == b"RIFF"

def test_live_gnani_integration_smoke_test():
    """
    Live smoke test for Gnani API integration.
    Strict Release Rule: If GNANI_API_KEY is unset, this test explicitly marks live integration as
    UNVERIFIED and skips. It NEVER pretends a mock was a live test.
    """
    import os
    from backend.config import settings
    if not settings.GNANI_API_KEY:
        pytest.skip("LIVE UNVERIFIED: GNANI_API_KEY is not configured in local environment.")

    # If key is provided:
    stt_adapter = GnaniSTTAdapter(api_key=settings.GNANI_API_KEY)
    tts_adapter = GnaniTTSAdapter(api_key=settings.GNANI_API_KEY)

    # 1. Test TTS synthesis
    audio_bytes, meta = tts_adapter.synthesize("నమస్కారం", language="te-IN")
    assert meta["is_mock"] is False
    assert len(audio_bytes) > 1000
    assert audio_bytes[:4] == b"RIFF"

    # 2. Test STT transcription
    stt_res = stt_adapter.transcribe(audio_bytes, language_code="te-IN")
    assert stt_res["is_mock"] is False
    assert "transcript" in stt_res


