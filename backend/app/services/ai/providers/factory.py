import os
from app.services.ai.providers.base import EmbeddingProvider, LLMProvider
from app.services.ai.providers.mock import MockEmbeddingProvider, MockLLMProvider


def get_llm_provider() -> LLMProvider:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        from app.services.ai.providers.gemini_provider import GeminiLLMProvider
        return GeminiLLMProvider(api_key=api_key)
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise RuntimeError("GEMINI_API_KEY is required in production; mock LLM provider is disabled.")
    return MockLLMProvider()


def get_embedding_provider() -> EmbeddingProvider:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        from app.services.ai.providers.gemini_provider import GeminiEmbeddingProvider
        return GeminiEmbeddingProvider(api_key=api_key)
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise RuntimeError("GEMINI_API_KEY is required in production; mock embedding provider is disabled.")
    return MockEmbeddingProvider()
