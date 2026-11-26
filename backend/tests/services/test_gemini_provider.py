import base64
import io
import os
import wave
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai.providers.factory import get_embedding_provider, get_llm_provider
from app.services.ai.providers.gemini_provider import GeminiEmbeddingProvider, GeminiLLMProvider
from app.services.voice.providers.factory import get_stt_provider, get_tts_provider
from app.services.voice.providers.gemini_provider import GeminiSTTProvider, GeminiTTSProvider


@pytest.mark.asyncio
async def test_gemini_llm_and_embedding():
    llm_extract_resp = MagicMock()
    llm_extract_resp.raise_for_status = MagicMock()
    llm_extract_resp.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": '{"intent":"FIND_SCHEME","profile_updates":{"age":65},"missing_fields":[]}'}]}}
        ]
    }

    llm_answer_resp = MagicMock()
    llm_answer_resp.raise_for_status = MagicMock()
    llm_answer_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Based on the information provided, you appear eligible for IGNOAPS."}]}}]
    }

    emb_resp = MagicMock()
    emb_resp.raise_for_status = MagicMock()
    emb_resp.json.return_value = {"embedding": {"values": [0.1] * 1536}}

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=[llm_extract_resp, llm_answer_resp, emb_resp])

    with patch("app.services.ai.providers.gemini_provider.httpx.AsyncClient", return_value=mock_client):
        llm = GeminiLLMProvider(api_key="gem-key")
        extracted = await llm.extract_intent_and_profile("I am 65", {})
        assert extracted["profile_updates"]["age"] == 65

        answer = await llm.generate_response("What scheme?", {"retrieved_schemes": [], "language": "en"})
        assert "IGNOAPS" in answer

        emb = GeminiEmbeddingProvider(api_key="gem-key")
        vec = await emb.generate_embedding("Old age pension")
        assert len(vec) == 1536
        assert emb.dimension == 1536


@pytest.mark.asyncio
async def test_gemini_stt_and_tts_pcm_to_wav():
    stt_resp = MagicMock()
    stt_resp.raise_for_status = MagicMock()
    stt_resp.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "मेरी उम्र 65 साल है"}]}}]
    }

    pcm_frames = b"\x00\x00" * 1600
    tts_resp = MagicMock()
    tts_resp.raise_for_status = MagicMock()
    tts_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "inlineData": {
                                "mimeType": "audio/pcm;rate=24000",
                                "data": base64.b64encode(pcm_frames).decode("utf-8"),
                            }
                        }
                    ]
                }
            }
        ]
    }

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=[stt_resp, tts_resp])

    with patch("app.services.voice.providers.gemini_provider.httpx.AsyncClient", return_value=mock_client):
        stt = GeminiSTTProvider(api_key="gem-key")
        text = await stt.transcribe(b"RIFFdummy", "hi")
        assert text == "मेरी उम्र 65 साल है"

        tts = GeminiTTSProvider(api_key="gem-key")
        wav_bytes = await tts.synthesize("नमस्ते", "hi")
        assert wav_bytes.startswith(b"RIFF")
        with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
            assert wf.getframerate() == 24000
            assert wf.getnchannels() == 1


def test_gemini_factories():
    with patch.dict(
        os.environ,
        {
            "GEMINI_API_KEY": "gem-key",
            "VOICE_STT_PROVIDER": "gemini",
            "VOICE_TTS_PROVIDER": "gemini",
        },
        clear=False,
    ):
        assert isinstance(get_llm_provider(), GeminiLLMProvider)
        assert isinstance(get_embedding_provider(), GeminiEmbeddingProvider)
        assert isinstance(get_stt_provider(), GeminiSTTProvider)
        assert isinstance(get_tts_provider(), GeminiTTSProvider)
