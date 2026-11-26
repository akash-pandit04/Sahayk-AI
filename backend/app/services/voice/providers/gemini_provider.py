import base64
import io
import os
import re
import wave

import httpx

from app.services.voice.providers.base import STTProvider, TTSProvider

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _detect_audio_mime(audio_bytes: bytes) -> str:
    if audio_bytes.startswith(b"RIFF"):
        return "audio/wav"
    if audio_bytes.startswith(b"OggS"):
        return "audio/ogg"
    if audio_bytes.startswith(b"ID3") or audio_bytes[:2] == b"\xff\xfb":
        return "audio/mp3"
    return "audio/webm"


def _pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 24000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


class GeminiSTTProvider(STTProvider):
    """Speech-to-Text using Gemini multimodal audio understanding."""

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    async def transcribe(self, audio_bytes: bytes, language: str) -> str:
        url = f"{GEMINI_API_BASE}/{self.model}:generateContent"
        mime_type = _detect_audio_mime(audio_bytes)
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": (
                                f"Transcribe the spoken audio verbatim in language code '{language}'. "
                                "Return ONLY the transcribed text without extra commentary."
                            )
                        },
                        {"inlineData": {"mimeType": mime_type, "data": audio_b64}},
                    ]
                }
            ]
        }
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


class GeminiTTSProvider(TTSProvider):
    """Text-to-Speech using Gemini audio generation."""

    def __init__(self, api_key: str, model: str | None = None, voice_name: str = "Kore"):
        self.api_key = api_key
        self.model = model or os.getenv("GEMINI_TTS_MODEL", "gemini-3.8-flash-tts")
        self.voice_name = voice_name

    async def synthesize(self, text: str, language: str) -> bytes:
        url = f"{GEMINI_API_BASE}/{self.model}:generateContent"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"Speak clearly and naturally in language '{language}': {text}"}
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": self.voice_name}
                    }
                },
            },
        }
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        inline = data["candidates"][0]["content"]["parts"][0]["inlineData"]
        audio_bytes = base64.b64decode(inline["data"])
        mime_type = inline.get("mimeType", "")
        if "pcm" in mime_type.lower():
            rate_match = re.search(r"rate=(\d+)", mime_type)
            rate = int(rate_match.group(1)) if rate_match else 24000
            return _pcm_to_wav(audio_bytes, sample_rate=rate)
        return audio_bytes
