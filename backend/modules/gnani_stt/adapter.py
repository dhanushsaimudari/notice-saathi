import io
import uuid
import httpx
from typing import Dict, Any, Optional
from backend.config import settings

class GnaniSTTAdapter:
    """
    Adapter for Gnani Prisma v2.5 Speech-to-Text REST API.
    Authoritative Spec:
      Endpoint: POST https://api.vachana.ai/stt/v3
      Headers: X-API-Key-ID: <API_KEY>
      Form Data:
        audio_file: (@audio.wav, multipart)
        language_code: BCP-47 string (e.g. te-IN, hi-IN, en-IN)
      Response:
        JSON { success: bool, request_id: str, transcript: str, model: str }
    """
    def __init__(self, api_key: str = settings.GNANI_API_KEY, base_url: str = settings.GNANI_BASE_URL):
        self.api_key = api_key.strip() if api_key else ""
        self.base_url = base_url.rstrip("/")
        self.endpoint = f"{self.base_url}{settings.GNANI_STT_ENDPOINT}"

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def transcribe(
        self,
        audio_bytes: bytes,
        language_code: str = "te-IN"
    ) -> Dict[str, Any]:
        """
        Transcribes speech audio bytes.
        If GNANI_API_KEY is not configured, returns an explicit, transparent mock object.
        Never conflates mock fallback with live verification.
        """
        if not self.is_configured:
            mock_transcripts = {
                "te-IN": "ఈ పత్రం గురించి మరియు ఇందులో ఉన్న తేదీ గురించి నాకు చెప్పండి.",
                "hi-IN": "इस नोटिस के बारे में बताइए और इसमें क्या तारीख लिखी है?",
                "en-IN": "What is this notice about and what date is mentioned?"
            }
            return {
                "success": True,
                "request_id": f"mock_stt_{uuid.uuid4().hex[:8]}",
                "transcript": mock_transcripts.get(language_code, mock_transcripts["en-IN"]),
                "is_mock": True,
                "model": "mock-prisma-v2.5",
                "message": "GNANI_API_KEY is not configured in environment. Local development mock returned."
            }

        headers = {
            "X-API-Key-ID": self.api_key
        }
        
        files = {
            "audio_file": ("question.wav", audio_bytes, "audio/wav")
        }
        data = {
            "language_code": language_code
        }
        
        try:
            with httpx.Client(timeout=httpx.Timeout(connect=4.0, read=25.0, write=5.0, pool=4.0)) as client:
                response = client.post(
                    self.endpoint,
                    headers=headers,
                    files=files,
                    data=data
                )
                if response.status_code == 200:
                    res_json = response.json()
                    res_json["is_mock"] = False
                    return res_json
                else:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response.text,
                        "is_mock": False
                    }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "is_mock": False
            }

gnani_stt_adapter = GnaniSTTAdapter()
