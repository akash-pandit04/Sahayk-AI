from typing import List
from app.services.ai.providers.base import LLMProvider, EmbeddingProvider

class MockLLMProvider(LLMProvider):
    async def extract_intent_and_profile(self, user_message: str, current_profile: dict) -> dict:
        # Extremely simplified mock for testing
        updates = {}
        import re
        age_match = re.search(r'\d+', user_message)
        if age_match:
            updates["age"] = int(age_match.group(0))
            
        if "farmer" in user_message.lower():
            updates["occupation"] = "farmer"
            updates["has_agricultural_land"] = True
            
        if "urban" in user_message.lower():
            updates["location_type"] = "urban"
            updates["owns_pucca_house"] = False
            
        if "daughter" in user_message.lower() or "girl" in user_message.lower():
            updates["gender"] = "female"
            
        if "boy" in user_message.lower():
            updates["gender"] = "male"
            
        if "below poverty line" in user_message.lower():
            updates["bpl_status"] = True
                
        return {
            "intent": "FIND_SCHEME",
            "profile_updates": updates,
            "missing_fields": []
        }

    async def generate_response(self, user_message: str, context: dict) -> str:
        # Mocking grounded validation
        schemes = context.get("retrieved_schemes", [])
        if not schemes:
            return "I'm sorry, I couldn't find any relevant schemes."
        
        scheme_names = [s["name"] for s in schemes]
        return f"Based on your profile, I found: {', '.join(scheme_names)}. Your status is {context.get('eligibility_result', {}).get('status')}."

class MockEmbeddingProvider(EmbeddingProvider):
    async def generate_embedding(self, text: str) -> List[float]:
        # Return a deterministic mock embedding (dimension 1536)
        # We just hash the text to create somewhat stable vectors
        import hashlib
        h = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        vec = [float((h + i) % 100) / 100.0 for i in range(1536)]
        
        # normalize
        length = sum(x*x for x in vec) ** 0.5
        if length > 0:
            vec = [x / length for x in vec]
        return vec
        
    @property
    def dimension(self) -> int:
        return 1536

    @property
    def model_name(self) -> str:
        return "mock-embedding-1536"
