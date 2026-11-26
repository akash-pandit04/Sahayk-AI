import json
import os
from typing import List

import httpx

from app.services.ai.providers.base import EmbeddingProvider, LLMProvider

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    async def _generate(self, system_instruction: str, user_text: str, json_mode: bool = False) -> str:
        payload: dict = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        }
        if json_mode:
            payload["generationConfig"] = {"responseMimeType": "application/json"}

        headers = {"x-goog-api-key": self.api_key, "Content-Type": "application/json"}
        candidates = [self.model]
        for fallback in ("gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-latest"):
            if fallback not in candidates:
                candidates.append(fallback)

        last_err: Exception | None = None
        async with httpx.AsyncClient(timeout=12.0) as client:
            for model_name in candidates:
                url = f"{GEMINI_API_BASE}/{model_name}:generateContent"
                try:
                    resp = await client.post(url, json=payload, headers=headers)
                    if resp.status_code in (404, 429, 503):
                        last_err = httpx.HTTPStatusError(
                            f"{resp.status_code} for {model_name}", request=resp.request, response=resp
                        )
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                except (httpx.ReadTimeout, httpx.ConnectTimeout) as e:
                    last_err = e
                    continue

        if last_err:
            raise last_err
        raise RuntimeError("No Gemini model succeeded")

    async def extract_intent_and_profile(self, user_message: str, current_profile: dict) -> dict:
        system_prompt = (
            "Classify the citizen's intent into one of: GREETING, IDENTITY, OUT_OF_SCOPE, FIND_SCHEME, SCHEME_INFO. "
            "Use GREETING for hello/hi/namaste, IDENTITY for 'what is your name/who are you', OUT_OF_SCOPE for non-scheme topics (weather, coding, sports, etc.), and FIND_SCHEME/SCHEME_INFO for government schemes or personal eligibility info. "
            "Also extract demographic/eligibility profile attributes (age, gender, state, occupation, bpl_status, income_group, location_type, owns_pucca_house, has_agricultural_land). "
            "Never collect PII (Aadhaar, PAN, phone, email). "
            'Return ONLY valid JSON: {"intent": "str", "profile_updates": {}, "missing_fields": []}.'
        )
        user_prompt = f"Current Profile: {json.dumps(current_profile)}\nUser Message: {user_message}"
        content = await self._generate(system_prompt, user_prompt, json_mode=True)
        return json.loads(content)

    async def generate_response(self, user_message: str, context: dict) -> str:
        language = context.get("language", "en")
        intent = context.get("intent", "FIND_SCHEME")

        if intent in ("GREETING", "IDENTITY"):
            system_prompt = (
                f"You are Sahayak AI, a friendly voice assistant that helps citizens of India discover verified Government of India welfare schemes. "
                f"Respond warmly in language code '{language}' in 1 to 2 short plain-text spoken sentences (no markdown). "
                "Introduce yourself as Sahayak AI and invite them to ask about government schemes or tell you their age/occupation."
            )
            return await self._generate(system_prompt, user_message, json_mode=False)

        if intent == "OUT_OF_SCOPE":
            system_prompt = (
                f"You are Sahayak AI, a dedicated assistant ONLY for Government of India welfare schemes. "
                f"Politely explain in language code '{language}' in 1 to 2 short plain-text spoken sentences (no markdown) "
                "that you only help with government welfare schemes and eligibility, and ask how you can help with a scheme."
            )
            return await self._generate(system_prompt, user_message, json_mode=False)

        system_prompt = f"""SYSTEM INSTRUCTIONS:
You are Sahayak AI, a live voice assistant helping citizens of India find government welfare schemes.

CRITICAL HIERARCHY OF TRUTH:
1. DETERMINISTIC ELIGIBILITY RESULT (`eligibility_status` inside each retrieved scheme): This is the absolute truth. Never override it. If status is NOT_ELIGIBLE, do not claim eligibility. If status is INSUFFICIENT_INFORMATION, ask concisely for `missing_information`.
2. RETRIEVED VERIFIED CONTEXT: Use ONLY the verified scheme records below.

VOICE & RESPONSE RULES:
- Respond in language code '{language}' in a warm, simple, spoken conversational style.
- Keep it concise for live voice output: 2 to 3 short sentences (under 60 words total).
- Output plain spoken text ONLY: NO markdown asterisks (**), NO bullet points, NO numbered lists, NO headings.
- Focus primarily on schemes with status POTENTIALLY_ELIGIBLE. If none are POTENTIALLY_ELIGIBLE yet, ask 1 short follow-up question for the most important missing information (such as age, occupation, income/BPL status, or urban/rural housing).
- Never invent schemes, benefits, rules, or URLs. Never say "You are definitely approved"; briefly note that final approval rests with the government department.

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
