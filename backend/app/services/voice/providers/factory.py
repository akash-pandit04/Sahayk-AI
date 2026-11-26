import os
from app.services.voice.providers.base import STTProvider, TTSProvider
from app.services.voice.providers.mock import MockSTTProvider, MockTTSProvider


def _is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").lower() == "production"


def get_stt_provider() -> STTProvider:
    provider = os.getenv("VOICE_STT_PROVIDER", "").lower()

    if provider == "mock":
        if _is_production():
            raise ValueError("VOICE_STT_PROVIDER='mock' is forbidden in production.")
        return MockSTTProvider()
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required when VOICE_STT_PROVIDER='gemini'.")
        from app.services.voice.providers.gemini_provider import GeminiSTTProvider
        return GeminiSTTProvider(api_key=api_key)
    raise ValueError(f"Invalid or missing VOICE_STT_PROVIDER: {provider}. Production must use 'gemini'.")


def get_tts_provider() -> TTSProvider:
    provider = os.getenv("VOICE_TTS_PROVIDER", "").lower()

    if provider == "mock":
        if _is_production():
            raise ValueError("VOICE_TTS_PROVIDER='mock' is forbidden in production.")
        return MockTTSProvider()
    if provider == "gemini":
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is required when VOICE_TTS_PROVIDER='gemini'.")
        from app.services.voice.providers.gemini_provider import GeminiTTSProvider
        return GeminiTTSProvider(api_key=api_key)
    raise ValueError(f"Invalid or missing VOICE_TTS_PROVIDER: {provider}. Production must use 'gemini'.")
