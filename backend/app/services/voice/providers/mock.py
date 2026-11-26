import io
import wave
from app.services.voice.providers.base import STTProvider, TTSProvider

class MockSTTProvider(STTProvider):
    async def transcribe(self, audio_bytes: bytes, language: str) -> str:
        # Default mock behaviour if no test override is provided
        if language == "hi":
            return "मेरी उम्र 65 साल है और मैं मध्य प्रदेश में रहती हूं। मेरे लिए कौन सी सरकारी योजना है?"
        elif language == "ta":
            return "எனக்கு 65 வயது, நான் தமிழ்நாட்டில் வசிக்கிறேன்."
        elif language == "te":
            return "నా వయసు 65 సంవత్సరాలు, నేను ఆంధ్ర ప్రదేశ్ లో నివసిస్తున్నాను."
        return "I am 65 years old and I live in Madhya Pradesh."

class MockTTSProvider(TTSProvider):
    async def synthesize(self, text: str, language: str, voice_name: str | None = None) -> bytes:
        # Generate a tiny, valid WAV file in memory (just a short silence/beep)
        # This allows the frontend HTMLAudioElement to successfully load and 'play' it.
        output = io.BytesIO()
        with wave.open(output, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(8000)
            # Add a few frames of silence
            wav_file.writeframes(b'\x00\x00' * 8000)
            
        return output.getvalue()
