import base64
import os
import httpx

from app.services.voice.providers.base import STTProvider, TTSProvider

DEFAULT_BHASHINI_URL = "https://dhruva-api.bhashini.gov.in/services/inference/pipeline"


class BhashiniSTTProvider(STTProvider):
    """Bhashini ULCA ASR (Speech-to-Text) client."""

    def __init__(
        self,
        api_key: str,
        pipeline_url: str = DEFAULT_BHASHINI_URL,
        user_id: str | None = None,
        service_id: str = "ai4bharat/conformer-hi-gpu--t4",
    ):
        self.api_key = api_key
        self.pipeline_url = pipeline_url
        self.user_id = user_id
        self.service_id = service_id

    async def transcribe(self, audio_bytes: bytes, language: str) -> str:
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        payload = {
            "pipelineTasks": [
                {
                    "taskType": "asr",
                    "config": {
                        "language": {"sourceLanguage": language[:2]},
                        "serviceId": self.service_id,
                        "audioFormat": "wav",
                        "samplingRate": 16000,
                    },
                }
            ],
            "inputData": {"audio": [{"audioContent": audio_b64}]},
        }
        headers = {"Authorization": self.api_key, "Content-Type": "application/json"}
        if self.user_id:
            headers["userID"] = self.user_id

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.pipeline_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return data["pipelineResponse"][0]["output"][0]["source"]


class BhashiniTTSProvider(TTSProvider):
    """Bhashini ULCA TTS (Text-to-Speech) client."""

    def __init__(
        self,
        api_key: str,
        pipeline_url: str = DEFAULT_BHASHINI_URL,
        user_id: str | None = None,
        service_id: str = "ai4bharat/indic-tts-coqui-indo_aryan-gpu--t4",
    ):
        self.api_key = api_key
        self.pipeline_url = pipeline_url
        self.user_id = user_id
        self.service_id = service_id

    async def synthesize(self, text: str, language: str) -> bytes:
        payload = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {"sourceLanguage": language[:2]},
                        "serviceId": self.service_id,
                        "gender": "female",
                        "samplingRate": 16000,
                    },
                }
            ],
            "inputData": {"input": [{"source": text}]},
        }
        headers = {"Authorization": self.api_key, "Content-Type": "application/json"}
        if self.user_id:
            headers["userID"] = self.user_id

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.pipeline_url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        audio_b64 = data["pipelineResponse"][0]["audio"][0]["audioContent"]
        return base64.b64decode(audio_b64)
