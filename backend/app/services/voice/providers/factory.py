import os
from app.services.voice.providers.base import STTProvider, TTSProvider
from app.services.voice.providers.mock import MockSTTProvider, MockTTSProvider

def get_stt_provider() -> STTProvider:
    provider = os.getenv("VOICE_STT_PROVIDER", "").lower()
    
    if provider == "mock":
        return MockSTTProvider()
    elif provider == "bhashini":
        raise NotImplementedError("Bhashini STT Provider is NOT CONFIGURED")
    else:
        raise ValueError(f"Invalid or missing VOICE_STT_PROVIDER: {provider}. Production must not use 'mock'.")

def get_tts_provider() -> TTSProvider:
    provider = os.getenv("VOICE_TTS_PROVIDER", "").lower()
    
    if provider == "mock":
        return MockTTSProvider()
    elif provider == "bhashini":
        raise NotImplementedError("Bhashini TTS Provider is NOT CONFIGURED")
    else:
        raise ValueError(f"Invalid or missing VOICE_TTS_PROVIDER: {provider}. Production must not use 'mock'.")
