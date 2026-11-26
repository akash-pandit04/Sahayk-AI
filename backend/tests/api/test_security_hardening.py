import os
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from app.core.config import INSECURE_DEFAULT_JWT_SECRET, Settings
from app.models.scheme_data.models import ConversationSession
from app.services.ai.orchestrator import sanitize_profile_updates
from app.services.ai.providers.factory import get_embedding_provider, get_llm_provider
from app.services.voice.providers.factory import get_stt_provider, get_tts_provider


def test_security_headers_on_health_and_admin(client, admin_token_headers):
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200
    assert health_res.headers.get("X-Content-Type-Options") == "nosniff"
    assert health_res.headers.get("X-Frame-Options") == "DENY"
    assert health_res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"

    admin_res = client.get("/api/v1/admin/schemes", headers=admin_token_headers)
    assert admin_res.status_code == 200
    assert admin_res.headers.get("Cache-Control") == "no-store"


def test_production_guardrails_reject_insecure_defaults():
    weak_jwt = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="sqlite:///./test.db",
        JWT_SECRET_KEY=INSECURE_DEFAULT_JWT_SECRET,
        VOICE_STT_PROVIDER="gemini",
        VOICE_TTS_PROVIDER="gemini",
        GEMINI_API_KEY="AIza-test",
    )
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        weak_jwt.validate_production_settings()

    mock_voice = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="sqlite:///./test.db",
        JWT_SECRET_KEY="a" * 40,
        VOICE_STT_PROVIDER="mock",
        VOICE_TTS_PROVIDER="gemini",
        GEMINI_API_KEY="AIza-test",
    )
    with pytest.raises(RuntimeError, match="Mock voice providers"):
        mock_voice.validate_production_settings()

    missing_gemini = Settings(
        ENVIRONMENT="production",
        DATABASE_URL="sqlite:///./test.db",
        JWT_SECRET_KEY="a" * 40,
        VOICE_STT_PROVIDER="gemini",
        VOICE_TTS_PROVIDER="gemini",
        GEMINI_API_KEY=None,
    )
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        missing_gemini.validate_production_settings()


def test_provider_factories_forbid_mock_in_production():
    with patch.dict(
        os.environ,
        {
            "ENVIRONMENT": "production",
            "VOICE_STT_PROVIDER": "mock",
            "VOICE_TTS_PROVIDER": "mock",
            "GEMINI_API_KEY": "",
        },
        clear=False,
    ):
        with pytest.raises(ValueError, match="forbidden in production"):
            get_stt_provider()
        with pytest.raises(ValueError, match="forbidden in production"):
            get_tts_provider()
        with pytest.raises(RuntimeError, match="mock LLM provider is disabled"):
            get_llm_provider()
        with pytest.raises(RuntimeError, match="mock embedding provider is disabled"):
            get_embedding_provider()


def test_pii_sanitization_strips_sensitive_data():
    raw_updates = {
        "age": 65,
        "state": "MP",
        "aadhaar": "1234 5678 9012",
        "phone_number": "9876543210",
        "notes": "Call 9876543210 or check 1234-5678-9012 or user@example.com",
    }
    cleaned = sanitize_profile_updates(raw_updates)
    assert cleaned["age"] == 65
    assert cleaned["state"] == "MP"
    assert "aadhaar" not in cleaned
    assert "phone_number" not in cleaned
    assert "9876543210" not in cleaned["notes"]
    assert "1234-5678-9012" not in cleaned["notes"]
    assert "user@example.com" not in cleaned["notes"]


def test_purge_expired_sessions(db):
    old_id = str(uuid.uuid4())
    fresh_id = str(uuid.uuid4())
    old_session = ConversationSession(
        id=old_id,
        session_id=f"old-{uuid.uuid4()}",
        profile_data={"age": 60},
        updated_at=datetime.utcnow() - timedelta(days=10),
    )
    fresh_session = ConversationSession(
        id=fresh_id,
        session_id=f"fresh-{uuid.uuid4()}",
        profile_data={"age": 30},
        updated_at=datetime.utcnow(),
    )
    db.add_all([old_session, fresh_session])
    db.commit()

    cutoff = datetime.utcnow() - timedelta(days=7)
    deleted = (
        db.query(ConversationSession)
        .filter(ConversationSession.updated_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()

    assert deleted >= 1
    assert db.query(ConversationSession).filter(ConversationSession.id == old_id).first() is None
    assert db.query(ConversationSession).filter(ConversationSession.id == fresh_id).first() is not None
