import base64
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.voice.providers.bhashini_provider import BhashiniSTTProvider, BhashiniTTSProvider
from app.services.voice.providers.factory import get_stt_provider, get_tts_provider


@pytest.mark.asyncio
async def test_bhashini_stt_and_tts_roundtrip():
    mock_stt_resp = MagicMock()
    mock_stt_resp.raise_for_status = MagicMock()
    mock_stt_resp.json.return_value = {"pipelineResponse": [{"output": [{"source": "नमस्ते"}]}]}

    expected_wav = b"RIFFtestwav"
    mock_tts_resp = MagicMock()
    mock_tts_resp.raise_for_status = MagicMock()
    mock_tts_resp.json.return_value = {
        "pipelineResponse": [{"audio": [{"audioContent": base64.b64encode(expected_wav).decode("utf-8")}]}]
    }

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=[mock_stt_resp, mock_tts_resp])

    with patch("app.services.voice.providers.bhashini_provider.httpx.AsyncClient", return_value=mock_client):
        stt = BhashiniSTTProvider(api_key="test-key", user_id="u1")
        text = await stt.transcribe(b"dummy-audio", "hi")
        assert text == "नमस्ते"

        tts = BhashiniTTSProvider(api_key="test-key", user_id="u1")
        audio = await tts.synthesize("नमस्ते", "hi")
        assert audio == expected_wav


def test_bhashini_factory_requires_api_key():
    with patch.dict(os.environ, {"VOICE_STT_PROVIDER": "bhashini", "BHASHINI_API_KEY": ""}, clear=False):
        with pytest.raises(ValueError, match="BHASHINI_API_KEY"):
            get_stt_provider()

    with patch.dict(os.environ, {"VOICE_TTS_PROVIDER": "bhashini", "BHASHINI_API_KEY": "key123"}, clear=False):
        provider = get_tts_provider()
        assert isinstance(provider, BhashiniTTSProvider)
