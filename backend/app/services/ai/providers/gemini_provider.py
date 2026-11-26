import json
import os
from typing import List

import httpx

from app.services.ai.providers.base import EmbeddingProvider, LLMProvider

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    async def _generate(self, system_instruction: str, user_text: str, json_mode: bool = False) -> str:
        url = f"{GEMINI_API_BASE}/{self.model}:generateContent"
        payload: dict = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        }
        if json_mode:
            payload["generationConfig"] = {"responseMimeType": "application/json"}

        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return data["candidates"][0]["content"]["parts"][0]["text"]

    async def extract_intent_and_profile(self, user_message: str, current_profile: dict) -> dict:
        system_prompt = (
            "Extract citizen intent and demographic/eligibility profile attributes from the message. "
            "Never collect PII such as Aadhaar numbers, PAN, phone numbers, or emails. "
            'Return ONLY valid JSON matching: {"intent": "str", "profile_updates": {}, "missing_fields": []}.'
        )
        user_prompt = f"Current Profile: {json.dumps(current_profile)}\nUser Message: {user_message}"
        content = await self._generate(system_prompt, user_prompt, json_mode=True)
        return json.loads(content)

    async def generate_response(self, user_message: str, context: dict) -> str:
        language = context.get("language", "en")
        system_prompt = f"""SYSTEM INSTRUCTIONS:
You are Sahayak AI, a government scheme assistant for citizens of India.

CRITICAL HIERARCHY OF TRUTH:
1. DETERMINISTIC ELIGIBILITY RESULT (`eligibility_status` inside each retrieved scheme): This is the absolute truth. Never override it. If status is NOT_ELIGIBLE, state clearly that they do not meet the criteria. If status is INSUFFICIENT_INFORMATION, ask for `missing_information`.
2. RETRIEVED VERIFIED CONTEXT: Use ONLY the verified scheme records below to explain benefits, criteria, and official sources.

RULES:
- Never invent schemes, benefits, eligibility rules, or URLs.
- Never say "You are definitely approved." Use phrases such as "Based on the information provided, you appear to meet the eligibility criteria; final approval rests with the concerned government authority."
- Respond in language code: {language}.

RETRIEVED VERIFIED SCHEMES:
{json.dumps(context.get("retrieved_schemes", []))}
"""
        return await self._generate(system_prompt, user_message, json_mode=False)


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self._model = model or os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

    async def generate_embedding(self, text: str) -> List[float]:
        url = f"{GEMINI_API_BASE}/{self._model}:embedContent"
        payload = {
            "model": f"models/{self._model}",
            "content": {"parts": [{"text": text}]},
            "outputDimensionality": 1536,
        }
        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        return data["embedding"]["values"]

    @property
    def dimension(self) -> int:
        return 1536

    @property
    def model_name(self) -> str:
        return self._model
