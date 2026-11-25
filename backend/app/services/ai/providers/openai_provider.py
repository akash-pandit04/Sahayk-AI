import os
import json
from typing import List
from app.services.ai.providers.base import LLMProvider, EmbeddingProvider

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: str):
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed. Please add it to requirements.txt.")
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def extract_intent_and_profile(self, user_message: str, current_profile: dict) -> dict:
        prompt = f"""
        Extract user profile and intent from the message.
        Current Profile: {json.dumps(current_profile)}
        User Message: {user_message}
        
        Return ONLY JSON matching:
        {{"intent": "str", "profile_updates": {{}}, "missing_fields": []}}
        """
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)

    async def generate_response(self, user_message: str, context: dict) -> str:
        prompt = f"""
        SYSTEM INSTRUCTIONS:
        You are Sahayak AI, a government scheme assistant. 
        
        CRITICAL HIERARCHY OF TRUTH:
        1. DETERMINISTIC ELIGIBILITY RESULT: This is the absolute truth about whether the user is eligible. You CANNOT override this. If the engine says NOT_ELIGIBLE, you must tell the user they are not eligible.
        2. RETRIEVED VERIFIED CONTEXT: Use this to explain WHY they are eligible or what benefits they get.
        
        RULES:
        - Answer ONLY using the retrieved verified scheme information below.
        - Never invent government schemes, benefits, or URLs.
        - Clearly distinguish deterministic evaluation from official final approval.
        
        RETRIEVED DATA:
        {json.dumps(context.get('retrieved_schemes', []))}
        
        ELIGIBILITY STATUS:
        {json.dumps(context.get('eligibility_result', {}))}
        """
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content

class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str):
        try:
            import openai
        except ImportError:
            raise RuntimeError("openai package not installed.")
        self.client = openai.AsyncOpenAI(api_key=api_key)
        
    async def generate_embedding(self, text: str) -> List[float]:
        response = await self.client.embeddings.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response.data[0].embedding
        
    @property
    def dimension(self) -> int:
        return 1536

    @property
    def model_name(self) -> str:
        return "text-embedding-ada-002"
