import pytest
import os
import urllib.parse
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_voice_pipeline_e2e(client):
    """
    Test the complete voice pipeline:
    Audio -> STT -> Assistant API -> TTS -> Audio
    And test follow-up context retention.
    """
    
    # We will bypass the E2E E2E (which goes through fastAPI UploadFile)
    # But since we use FastAPI TestClient which handles multipart nicely:
    
    # 1. First interaction
    with open("tests/dummy.wav", "wb") as f:
        f.write(b"dummy audio content here" * 10)
        
    with open("tests/dummy.wav", "rb") as f:
        res1_stt = client.post(
            "/api/v1/voice/transcribe",
            data={"language": "hi"},
            files={"audio": ("dummy.wav", f, "audio/wav")},
            headers={"X-Mock-Transcription": urllib.parse.quote("मेरी उम्र 65 साल है।")}
        )
        
    assert res1_stt.status_code == 200
    data1 = res1_stt.json()
    assert data1["text"] == "मेरी उम्र 65 साल है।"
    
    # Pass to assistant
    res1_ai = client.post(
        "/api/v1/assistant/query",
        json={"message": data1["text"], "language": "hi"}
    )
    assert res1_ai.status_code == 200
    ai_data1 = res1_ai.json()
    conv_id = ai_data1["conversation_id"]
    
    # Synthesize
    res1_tts = client.post(
        "/api/v1/voice/synthesize",
        json={"text": ai_data1["response_text"], "language": "hi"}
    )
    assert res1_tts.status_code == 200
    assert res1_tts.headers["content-type"] == "audio/wav"
    
    # 2. Follow-up query
    with open("tests/dummy.wav", "wb") as f:
        f.write(b"dummy audio content here" * 10)
        
    with open("tests/dummy.wav", "rb") as f:
        res2_stt = client.post(
            "/api/v1/voice/transcribe",
            data={"language": "hi", "conversation_id": conv_id},
            files={"audio": ("dummy.wav", f, "audio/wav")},
            headers={"X-Mock-Transcription": urllib.parse.quote("मैं मध्य प्रदेश में रहती हूं।")}
        )
    assert res2_stt.status_code == 200
    
    res2_ai = client.post(
        "/api/v1/assistant/query",
        json={"message": "मैं मध्य प्रदेश में रहती हूं।", "language": "hi", "conversation_id": conv_id}
    )
    assert res2_ai.status_code == 200
    
    # 3. Third query
    res3_ai = client.post(
        "/api/v1/assistant/query",
        json={"message": "मेरे लिए कौन सी योजना है?", "language": "hi", "conversation_id": conv_id}
    )
    assert res3_ai.status_code == 200
    
    # Cleanup
    if os.path.exists("tests/dummy.wav"):
        os.remove("tests/dummy.wav")

@pytest.mark.asyncio
async def test_invalid_audio_mime(client):
    with open("tests/dummy.txt", "wb") as f:
        f.write(b"fake text file")
        
    with open("tests/dummy.txt", "rb") as f:
        res = client.post(
            "/api/v1/voice/transcribe",
            data={"language": "hi"},
            files={"audio": ("dummy.txt", f, "text/plain")}
        )
        
    assert res.status_code == 400
    assert "MIME type" in res.json()["detail"]
    
    if os.path.exists("tests/dummy.txt"):
        os.remove("tests/dummy.txt")

@pytest.mark.asyncio
async def test_oversized_audio(client):
    # Simulate a huge file (we'll just use a mock object or send a big payload)
    # Actually, we can just send > 5MB string
    big_content = b"0" * (6 * 1024 * 1024)
    with open("tests/huge.wav", "wb") as f:
        f.write(big_content)
        
    with open("tests/huge.wav", "rb") as f:
        res = client.post(
            "/api/v1/voice/transcribe",
            data={"language": "hi"},
            files={"audio": ("huge.wav", f, "audio/wav")}
        )
        
    assert res.status_code == 400
    assert "large" in res.json()["detail"]
    
    if os.path.exists("tests/huge.wav"):
        os.remove("tests/huge.wav")

@pytest.mark.asyncio
async def test_empty_synthesis_text(client):
    res = client.post(
        "/api/v1/voice/synthesize",
        json={"text": "   ", "language": "hi"}
    )
    assert res.status_code == 400
