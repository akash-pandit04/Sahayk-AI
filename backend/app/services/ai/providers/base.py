from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class LLMProvider(ABC):
    @abstractmethod
    async def extract_intent_and_profile(self, user_message: str, current_profile: dict) -> dict:
        """
        Expected to return a dict like:
        {
            "intent": "FIND_SCHEME",
            "profile_updates": {"age": 65, "state": "Madhya Pradesh"},
            "missing_fields": []
        }
        """
        pass

    @abstractmethod
    async def generate_response(self, user_message: str, context: dict) -> str:
        """
        context contains:
        {
            "system_instructions": "...",
            "profile": {...},
            "eligibility_result": {...},
            "retrieved_schemes": [...]
        }
        """
        pass

class EmbeddingProvider(ABC):
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        pass
        
    @property
    @abstractmethod
    def dimension(self) -> int:
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        pass
