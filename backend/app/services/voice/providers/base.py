from abc import ABC, abstractmethod
from typing import Optional

class STTProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, language: str) -> str:
        """
        Convert audio bytes to text for the specified language.
        language should be a short code (e.g., 'hi', 'ta', 'te').
        """
        pass

class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, language: str, voice_name: Optional[str] = None) -> bytes:
        """
        Convert text to audio bytes in the specified language.
        Return format should ideally be a standard format like WAV or MP3.
        """
        pass
