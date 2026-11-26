import io
from app.services.voice.providers.base import STTProvider, TTSProvider


class OpenAISTTProvider(STTProvider):
    def __init__(self, api_key: str):
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed.")
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def transcribe(self, audio_bytes: bytes, language: str) -> str:
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.webm"
        transcript = await self.client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language[:2] if language else None,
        )
        return transcript.text


class OpenAITTSProvider(TTSProvider):
    def __init__(self, api_key: str):
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed.")
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def synthesize(self, text: str, language: str) -> bytes:
        response = await self.client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            response_format="wav",
            input=text,
        )
        return response.content
