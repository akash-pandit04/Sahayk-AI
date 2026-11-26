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
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when VOICE_STT_PROVIDER='openai'.")
        from app.services.voice.providers.openai_provider import OpenAISTTProvider
        return OpenAISTTProvider(api_key=api_key)
    if provider == "bhashini":
        raise NotImplementedError("Bhashini STT Provider requires BHASHINI_API_KEY and pipeline endpoint integration.")
    raise ValueError(f"Invalid or missing VOICE_STT_PROVIDER: {provider}. Production must not use 'mock'.")


def get_tts_provider() -> TTSProvider:
    provider = os.getenv("VOICE_TTS_PROVIDER", "").lower()

    if provider == "mock":
        if _is_production():
            raise ValueError("VOICE_TTS_PROVIDER='mock' is forbidden in production.")
        return MockTTSProvider()
    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required when VOICE_TTS_PROVIDER='openai'.")
        from app.services.voice.providers.openai_provider import OpenAITTSProvider
        return OpenAITTSProvider(api_key=api_key)
    if provider == "bhashini":
        raise NotImplementedError("Bhashini TTS Provider requires BHASHINI_API_KEY and pipeline endpoint integration.")
    raise ValueError(f"Invalid or missing VOICE_TTS_PROVIDER: {provider}. Production must not use 'mock'.")
