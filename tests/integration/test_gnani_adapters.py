import pytest
from backend.modules.gnani_stt.adapter import gnani_stt_adapter
from backend.modules.gnani_tts.adapter import gnani_tts_adapter, generate_mock_wav

def test_gnani_stt_adapter_mock_fallback():
    # Test mock fallback when unconfigured
    from backend.modules.gnani_stt.adapter import GnaniSTTAdapter
    adapter = GnaniSTTAdapter(api_key="")
    audio_sample = b"RIFF....WAVEfmt ...."
    res = adapter.transcribe(audio_sample, language_code="te-IN")
    assert res["success"] is True
    assert res["is_mock"] is True
    assert "transcript" in res
    assert len(res["transcript"]) > 0

def test_gnani_tts_adapter_synthesis():
    test_text = "విచారణ తేదీ 18 నవంబర్ 2026 న నిర్ణయించబడింది."
    wav_bytes, meta = gnani_tts_adapter.synthesize(
        text=test_text,
        language="te-IN",
        speed=1.0
    )
    assert len(wav_bytes) > 100
    assert wav_bytes[:4] == b"RIFF"
    assert wav_bytes[8:12] == b"WAVE"
    if not meta.get("error_fallback"):
        assert meta["container"] == "wav"
        assert meta["voice"] == "Lavanya"
    else:
        assert meta["is_mock"] is True

def test_mock_wav_generator_header():
    wav = generate_mock_wav(duration_s=1.0)
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    assert len(wav) > 1000
