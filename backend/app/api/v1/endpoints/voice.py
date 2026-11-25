import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Response
from pydantic import BaseModel
from app.core.deps import rate_limit
from app.services.voice.providers.factory import get_stt_provider, get_tts_provider

router = APIRouter()

class SynthesizeRequest(BaseModel):
    text: str
    language: str

@router.post("/transcribe", dependencies=[Depends(rate_limit(requests=10, window=60))])
async def transcribe_audio(
    request: Request,
    language: str = Form(...),
    conversation_id: str = Form(None),
    audio: UploadFile = File(...)
):
    """
    Accepts audio and returns transcribed text.
    Validates MIME types and limits size.
    """
    # 1. Validation
    # Allow common audio mimes
    allowed_mimes = ["audio/webm", "audio/mp4", "audio/wav", "audio/mpeg", "audio/ogg", "application/octet-stream"]
    if audio.content_type not in allowed_mimes:
        raise HTTPException(status_code=400, detail="Unsupported audio MIME type.")
        
    # Read and limit size (e.g. 5MB max for MVP)
    audio_bytes = await audio.read()
    if len(audio_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio file too large. Maximum is 5MB.")
        
    if len(audio_bytes) < 100:
        raise HTTPException(status_code=400, detail="Audio file too small or empty.")

    # 2. Check for E2E testing override
    env = os.getenv("ENVIRONMENT", "development")
    mock_header = request.headers.get("X-Mock-Transcription")
    if mock_header and env in ["test", "development"]:
        import urllib.parse
        decoded_mock = urllib.parse.unquote(mock_header)
        return {
            "text": decoded_mock,
            "language": language,
            "conversation_id": conversation_id
        }

    # 3. Process via Provider
    try:
        stt_provider = get_stt_provider()
        text = await stt_provider.transcribe(audio_bytes, language)
        return {
            "text": text,
            "language": language,
            "conversation_id": conversation_id
        }
    except Exception as e:
        import logging
        logging.error(f"STT Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Transcription service failed.")

@router.post("/synthesize", dependencies=[Depends(rate_limit(requests=20, window=60))])
async def synthesize_speech(
    req: SynthesizeRequest
):
    """
    Accepts text and returns an audio file (e.g. WAV).
    """
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
        
    if len(req.text) > 2000:
        raise HTTPException(status_code=400, detail="Text too long for synthesis.")
        
    try:
        tts_provider = get_tts_provider()
        audio_bytes = await tts_provider.synthesize(req.text, req.language)
        
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        import logging
        logging.error(f"TTS Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Speech synthesis service failed.")
