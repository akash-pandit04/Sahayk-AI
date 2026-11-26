import json
import os
from typing import List, Optional

import httpx

from app.services.ai.providers.base import EmbeddingProvider, LLMProvider

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model = model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    async def _generate(
        self,
        system_instruction: str,
        user_text: str,
        json_mode: bool = False,
        history: Optional[List[dict]] = None,
    ) -> str:
        contents = []
        for turn in history or []:
            role = "model" if turn.get("role") == "assistant" else "user"
            text = (turn.get("text") or "").strip()
            if text:
                contents.append({"role": role, "parts": [{"text": text}]})
        contents.append({"role": "user", "parts": [{"text": user_text}]})

        payload: dict = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": contents,
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
        clean_profile = {k: v for k, v in (current_profile or {}).items() if not k.startswith("_")}
        history = (current_profile or {}).get("_chat_history", [])[-6:]
        system_prompt = (
            "Classify the user's latest message into one intent: "
            "SCHEME_QUERY (asking about government schemes, welfare, pensions, subsidies, scholarships, health insurance, housing, farming aid, eligibility, or sharing personal age/income/occupation/location for schemes) "
            "OR GENERAL_CHAT (greetings, mic checks like 'can you hear me?', follow-up conversation, general knowledge, everyday questions, asking who you are, or general chat). "
            "Also extract any eligibility profile attributes if mentioned (age, gender, state, occupation, bpl_status, income_group, location_type, owns_pucca_house, has_agricultural_land). "
            "Never collect PII (Aadhaar, PAN, phone, email). "
            'Return ONLY valid JSON: {"intent": "SCHEME_QUERY|GENERAL_CHAT", "profile_updates": {}, "missing_fields": []}.'
        )
        user_prompt = f"Current Profile: {json.dumps(clean_profile)}\nLatest User Message: {user_message}"
        content = await self._generate(system_prompt, user_prompt, json_mode=True, history=history)
        return json.loads(content)

    async def generate_response(self, user_message: str, context: dict) -> str:
        language = context.get("language", "en")
        intent = context.get("intent", "SCHEME_QUERY")
        history = context.get("history", [])

        identity_rules = (
            "IDENTITY & CREATOR RULES (MANDATORY):\n"
            "- Your name is always Sahayak AI. Never say you are Gemini or made/trained by Google or Google developers.\n"
            "- If asked who made/created/built/developed you or about your team/creators, always state that you were made by "
            "Akash Pandit, Abhishek Mishra, Patel Swastik Surya, Shakya Jay Jitendra, Veer Patangiya, and Upendra Gupta "
            "together for the project called EPICS (Engineering Project in Community Service).\n"
        )

        if intent == "GENERAL_CHAT":
            system_prompt = (
                f"You are Sahayak AI, a warm, intelligent, natural conversational voice assistant "
                f"who can chat naturally on any topic and also specializes in Indian government welfare schemes.\n"
                f"{identity_rules}"
                f"INSTRUCTIONS:\n"
                f"- Answer the user's exact question directly and contextually using the conversation history.\n"
                f"- For example, if they ask 'Can you hear me?', confirm naturally ('Yes, I can hear you clearly! How can I help?'). If they ask general questions, answer helpfully and ask a relevant follow-up or cross-question to keep the conversation natural.\n"
                f"- Respond in language code '{language}' in concise spoken plain text (2 to 4 short sentences, NO markdown asterisks, bullets, or headings).\n"
                f"- Do NOT claim specific government scheme eligibility amounts or official URLs unless verified scheme data was provided."
            )
            return await self._generate(system_prompt, user_message, json_mode=False, history=history)

        system_prompt = f"""SYSTEM INSTRUCTIONS:
You are Sahayak AI, a natural, intelligent voice assistant helping citizens of India with government welfare schemes.
{identity_rules}

CRITICAL HIERARCHY OF TRUTH:
1. DETERMINISTIC ELIGIBILITY RESULT (`eligibility_status` inside each retrieved scheme): This is the absolute truth. Never override it. If status is NOT_ELIGIBLE, do not claim eligibility. If status is INSUFFICIENT_INFORMATION, ask a natural cross-question for `missing_information`.
2. RETRIEVED VERIFIED CONTEXT: Use ONLY the verified scheme records below for scheme facts, benefits, and URLs.

VOICE & CONVERSATION RULES:
- Use the conversation history naturally so follow-ups and clarifications feel like a real human dialogue.
- Respond in language code '{language}' in concise spoken plain text (2 to 4 short sentences, NO markdown **, bullets, or headings).
- Focus primarily on schemes with status POTENTIALLY_ELIGIBLE. If none are POTENTIALLY_ELIGIBLE yet, ask 1 natural cross-question for the missing information (e.g., age, occupation, BPL/income status, urban/rural housing).
- Never invent schemes, benefits, rules, or URLs. Never say "You are definitely approved"; note briefly that final approval rests with the concerned government department.

RETRIEVED VERIFIED SCHEMES:
{json.dumps(context.get("retrieved_schemes", []))}
"""
        return await self._generate(system_prompt, user_message, json_mode=False, history=history)


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
