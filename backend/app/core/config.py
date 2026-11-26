from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

INSECURE_DEFAULT_JWT_SECRET = "super-secret-key-change-in-production-1234567890"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Sahayak AI"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # CORS
    CORS_ORIGINS: List[str] = []

    # Database
    DATABASE_URL: str

    # JWT Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Gemini AI & Voice Providers
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_STT_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_TTS_MODEL: str = "gemini-3.1-flash-tts-preview"
    VOICE_STT_PROVIDER: str = "mock"
    VOICE_TTS_PROVIDER: str = "mock"

    # Privacy / Retention
    SESSION_RETENTION_DAYS: int = 7

    # Bootstrap
    FIRST_ADMIN_EMAIL: str = "admin@sahayak.local"
    FIRST_ADMIN_PASSWORD: str = "adminpassword"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

    def validate_production_settings(self) -> None:
        """Fail fast if unsafe defaults or mock providers are enabled in production."""
        if self.ENVIRONMENT.lower() != "production":
            return

        if self.JWT_SECRET_KEY == INSECURE_DEFAULT_JWT_SECRET or len(self.JWT_SECRET_KEY) < 32:
            raise RuntimeError("Insecure JWT_SECRET_KEY in production. Must be >= 32 chars and non-default.")

        if self.VOICE_STT_PROVIDER.lower() in ("", "mock") or self.VOICE_TTS_PROVIDER.lower() in ("", "mock"):
            raise RuntimeError("Mock voice providers are forbidden when ENVIRONMENT=production.")

        if not self.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY must be configured when ENVIRONMENT=production.")


settings = Settings()
