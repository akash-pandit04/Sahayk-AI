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
        api_key = os.getenv("BHASHINI_API_KEY")
        if not api_key:
            raise ValueError("BHASHINI_API_KEY is required when VOICE_STT_PROVIDER='bhashini'.")
        from app.services.voice.providers.bhashini_provider import BhashiniSTTProvider, DEFAULT_BHASHINI_URL
        return BhashiniSTTProvider(
            api_key=api_key,
            pipeline_url=os.getenv("BHASHINI_PIPELINE_URL") or DEFAULT_BHASHINI_URL,
            user_id=os.getenv("BHASHINI_USER_ID"),
        )
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
        api_key = os.getenv("BHASHINI_API_KEY")
        if not api_key:
            raise ValueError("BHASHINI_API_KEY is required when VOICE_TTS_PROVIDER='bhashini'.")
        from app.services.voice.providers.bhashini_provider import BhashiniTTSProvider, DEFAULT_BHASHINI_URL
        return BhashiniTTSProvider(
            api_key=api_key,
            pipeline_url=os.getenv("BHASHINI_PIPELINE_URL") or DEFAULT_BHASHINI_URL,
            user_id=os.getenv("BHASHINI_USER_ID"),
        )
    raise ValueError(f"Invalid or missing VOICE_TTS_PROVIDER: {provider}. Production must not use 'mock'.")
