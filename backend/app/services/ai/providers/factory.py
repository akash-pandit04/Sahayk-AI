import os
from app.services.ai.providers.base import LLMProvider, EmbeddingProvider
from app.services.ai.providers.mock import MockLLMProvider, MockEmbeddingProvider


def get_llm_provider() -> LLMProvider:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        from app.services.ai.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key)
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise RuntimeError("OPENAI_API_KEY is required in production; mock LLM provider is disabled.")
    return MockLLMProvider()


def get_embedding_provider() -> EmbeddingProvider:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        from app.services.ai.providers.openai_provider import OpenAIEmbeddingProvider
        return OpenAIEmbeddingProvider(api_key=api_key)
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        raise RuntimeError("OPENAI_API_KEY is required in production; mock embedding provider is disabled.")
    return MockEmbeddingProvider()
