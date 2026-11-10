import io
import math
import struct
import wave
import httpx
from typing import Dict, Any, Tuple, Optional
from backend.config import settings

# Authoritative Voice Catalog from Gnani Documentation (Document B)
VOICE_MAP = {
    "te-IN": "Lavanya",
    "hi-IN": "Nalini",
    "en-IN": "Kaveri",
    "ta-IN": "Asmita",
    "kn-IN": "Saanvi"
}

def generate_mock_wav(duration_s: float = 2.0, sample_rate: int = 16000) -> bytes:
    """
    Generates a valid binary 16-bit PCM WAV byte stream for local testing & development.
    Ensures browser <audio> elements render and play without errors.
    """
    num_samples = int(sample_rate * duration_s)
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav_file:
        wav_file.setnchannels(1)      # mono
        wav_file.setsampwidth(2)      # 16-bit
        wav_file.setframerate(sample_rate)
        
        frames = bytearray()
        for i in range(num_samples):
            t = float(i) / sample_rate
            envelope = min(t * 10, 1.0) * min((duration_s - t) * 10, 1.0)
            val = envelope * 0.25 * (
                math.sin(2 * math.pi * 440.0 * t) + 
                0.5 * math.sin(2 * math.pi * 554.37 * t) +
                0.3 * math.sin(2 * math.pi * 659.25 * t)
            )
            sample_val = int(max(min(val, 1.0), -1.0) * 32767.0)
            frames.extend(struct.pack('<h', sample_val))
            
        wav_file.writeframes(frames)
    return buf.getvalue()

class GnaniTTSAdapter:
    """
    Adapter for Gnani Timbre v2.5 Text-to-Speech REST API.
    Authoritative Spec:
      Endpoint: POST https://api.vachana.ai/api/v1/tts/inference
      Headers:
        Content-Type: application/json
        X-API-Key-ID: <API_KEY>
      Body:
        text: str
        voice: str (e.g. Lavanya for te-IN, Nalini for hi-IN)
        model: "timbre-v2.5"
        language: BCP-47 string
        speed: float (0.85 to 1.15)
        audio_config: { sample_rate: 48000, num_channels: 1, sample_width: 2, encoding: "linear_pcm", container: "wav" }
      Response:
        200 OK: Binary audio/wav bytes
    """
    def __init__(self, api_key: str = settings.GNANI_API_KEY, base_url: str = settings.GNANI_BASE_URL):
        self.api_key = api_key.strip() if api_key else ""
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}{settings.GNANI_TTS_ENDPOINT}"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def synthesize(
        self,
        text: str,
        language: str = "te-IN",
        speed: float = 1.0
    ) -> Tuple[bytes, Dict[str, Any]]:
        voice = VOICE_MAP.get(language, "Lavanya")
        
        # Transparent mock fallback when API key is unconfigured
        if not self.is_configured:
            mock_audio = generate_mock_wav(duration_s=2.5, sample_rate=16000)
            return mock_audio, {
                "is_mock": True,
                "model": "mock-timbre-v2.5",
                "voice": voice,
                "language": language,
                "speed": speed,
                "container": "wav",
                "message": "GNANI_API_KEY is not configured in environment. Local development mock audio synthesized."
            }

        headers = {
            "Content-Type": "application/json",
            "X-API-Key-ID": self.api_key
        }
        
        payload = {
            "text": text,
            "voice": voice,
            "model": settings.GNANI_TTS_MODEL,
            "language": language,
            "speed": max(0.85, min(1.15, speed)),
            "audio_config": {
                "sample_rate": 48000,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav"
            }
        }
        
        try:
            with httpx.Client(timeout=httpx.Timeout(connect=4.0, read=25.0, write=5.0, pool=4.0)) as client:
                response = client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload
                )
                if response.status_code == 200:
                    return response.content, {
                        "is_mock": False,
                        "model": settings.GNANI_TTS_MODEL,
                        "voice": voice,
                        "language": language,
                        "speed": speed,
                        "container": "wav"
                    }
                else:
                    # Upstream error: return fallback audio with clear error telemetry
                    mock_audio = generate_mock_wav(duration_s=2.0)
                    return mock_audio, {
                        "is_mock": True,
                        "error_fallback": True,
                        "upstream_status": response.status_code,
                        "upstream_error": response.text,
                        "message": "Gnani upstream error. Fallback audio provided."
                    }
        except Exception as e:
            mock_audio = generate_mock_wav(duration_s=2.0)
            return mock_audio, {
                "is_mock": True,
                "error_fallback": True,
                "exception": str(e)
            }

gnani_tts_adapter = GnaniTTSAdapter()
