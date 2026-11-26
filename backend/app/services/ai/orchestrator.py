import asyncio
import re
import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.models.scheme_data.models import ConversationSession, Scheme
from app.services.ai.providers.factory import get_embedding_provider, get_llm_provider
from app.services.ai.retrieval import RetrievalService
from app.services.eligibility.engine import evaluate_eligibility

SENSITIVE_PROFILE_KEYS = {
    "aadhaar", "aadhar", "aadhaar_number", "pan", "pan_number",
    "phone", "mobile", "phone_number", "email", "bank_account", "ifsc", "passport",
}
_AADHAAR_RE = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
_PHONE_RE = re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b")
_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

_CREATOR_QUERY_RE = re.compile(
    r"(who\s+(made|created|built|developed|trained)\s+you|"
    r"who\s+(are|is)\s+your\s+(creator|creators|developer|developers|maker|makers|team)|"
    r"made\s+by\s+google|created\s+by\s+google|"
    r"kisne\s+banaya|किसने\s+बनाया|बनाया\s+है|निर्माता)",
    re.IGNORECASE,
)
_NAME_QUERY_RE = re.compile(
    r"(what\s+is\s+your\s+name|what's\s+your\s+name|who\s+are\s+you|tell\s+me\s+your\s+name|"
    r"tumhara\s+naam|aapka\s+naam|तुम्हारा\s+नाम|आपका\s+नाम|आप\s+कौन\s+हैं)",
    re.IGNORECASE,
)


def _match_identity_filter(message: str, language: str) -> str | None:
    """Deterministic filter for creator and assistant name queries."""
    if _CREATOR_QUERY_RE.search(message):
        if language == "hi":
            return (
                "मैं Sahayak AI हूँ। मुझे Akash Pandit, Abhishek Mishra, Patel Swastik Surya, "
                "Shakya Jay Jitendra, Veer Patangiya, और Upendra Gupta की पूरी टीम ने मिलकर "
                "EPICS (Engineering Project in Community Service) प्रोजेक्ट के लिए बनाया है।"
            )
        return (
            "I am Sahayak AI. I have been made by Akash Pandit, Abhishek Mishra, Patel Swastik Surya, "
            "Shakya Jay Jitendra, Veer Patangiya, and Upendra Gupta together for the project called "
            "EPICS (Engineering Project in Community Service)."
        )
    if _NAME_QUERY_RE.search(message):
        if language == "hi":
            return "मैं Sahayak AI हूँ, आपका लाइव वॉयस सहायक। बताइए, आज मैं आपकी क्या मदद कर सकता हूँ?"
        return "I am Sahayak AI, your live voice assistant. How can I help you today?"
    return None


def sanitize_profile_updates(updates: dict) -> dict:
    """Enforce data minimization by dropping PII keys and scrubbing sensitive patterns."""
    cleaned = {}
    for k, v in updates.items():
        if k.startswith("_") or k.lower() in SENSITIVE_PROFILE_KEYS:
            continue
        if isinstance(v, str):
            v = _AADHAAR_RE.sub("[REDACTED]", v)
            v = _PHONE_RE.sub("[REDACTED]", v)
            v = _EMAIL_RE.sub("[REDACTED]", v)
        cleaned[k] = v
    return cleaned


def scrub_pii_text(text: str) -> str:
    text = _AADHAAR_RE.sub("[REDACTED]", text)
    text = _PHONE_RE.sub("[REDACTED]", text)
    return _EMAIL_RE.sub("[REDACTED]", text)


class AssistantOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.llm_provider = get_llm_provider()
        self.embedding_provider = get_embedding_provider()
        self.retrieval_service = RetrievalService(db)

    def get_or_create_session(self, session_id: str) -> ConversationSession:
        if not session_id:
            session_id = str(uuid.uuid4())

        session = self.db.query(ConversationSession).filter(ConversationSession.session_id == session_id).first()
        if not session:
            session = ConversationSession(session_id=session_id, profile_data={})
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
        return session

    def update_session_profile(self, session: ConversationSession, updates: dict):
        if not updates:
            return

        updates = sanitize_profile_updates(updates)
        current_data = dict(session.profile_data or {})
        for k, v in updates.items():
            if v is None and k in current_data:
                del current_data[k]
            elif v is not None:
                current_data[k] = v

        session.profile_data = current_data
        flag_modified(session, "profile_data")
        self.db.commit()
        self.db.refresh(session)

    def append_conversation_turn(self, session: ConversationSession, user_message: str, assistant_message: str):
        current_data = dict(session.profile_data or {})
        history = list(current_data.get("_chat_history", []))
        history.append({"role": "user", "text": scrub_pii_text(user_message)})
        history.append({"role": "assistant", "text": assistant_message})
        current_data["_chat_history"] = history[-12:]
        session.profile_data = current_data
        flag_modified(session, "profile_data")
        self.db.commit()
        self.db.refresh(session)

    async def process_query(self, session_id: str, message: str, language: str = "en") -> dict:
        # 1. Load Session
        session = self.get_or_create_session(session_id)
        raw_profile = dict(session.profile_data or {})
        history = list(raw_profile.get("_chat_history", []))
        eval_profile = {k: v for k, v in raw_profile.items() if not k.startswith("_")}

        # Deterministic identity/creator filter
        identity_reply = _match_identity_filter(message, language)
        if identity_reply is not None:
            self.append_conversation_turn(session, message, identity_reply)
            return {
                "conversation_id": session.session_id,
                "intent": "IDENTITY",
                "response_text": identity_reply,
                "missing_fields": [],
                "scheme_results": [],
                "sources": [],
            }

        # 2. Extract Intent/Profile & Embed Query in parallel to minimize latency
        if self.db.bind.dialect.name == "sqlite":
            extraction = await self.llm_provider.extract_intent_and_profile(message, raw_profile)
            query_vector = None
        else:
            extraction, query_vector = await asyncio.gather(
                self.llm_provider.extract_intent_and_profile(message, raw_profile),
                self.embedding_provider.generate_embedding(message),
            )

        # 3. Update Profile Context
        if extraction.get("profile_updates"):
            self.update_session_profile(session, extraction["profile_updates"])
            eval_profile = {k: v for k, v in (session.profile_data or {}).items() if not k.startswith("_")}

        intent = extraction.get("intent", "SCHEME_QUERY")

        # Natural conversational path for greetings, mic checks, and general Q&A
        if intent in ("GREETING", "IDENTITY", "OUT_OF_SCOPE", "GENERAL_CHAT"):
            response_text = await self.llm_provider.generate_response(
                message,
                {
                    "profile": eval_profile,
                    "history": history,
                    "retrieved_schemes": [],
                    "language": language,
                    "intent": "GENERAL_CHAT",
                },
            )
            self.append_conversation_turn(session, message, response_text)
            return {
                "conversation_id": session.session_id,
                "intent": intent,
                "response_text": response_text,
                "missing_fields": [],
                "scheme_results": [],
                "sources": [],
            }

        # 4. Retrieval (Only Published Schemes)
        candidate_schemes = await self.retrieval_service.search_schemes(message, limit=5, query_vector=query_vector)

        # 5. Deterministic Eligibility Evaluation (Source of Truth)
        evaluated_schemes = []
        for scheme in candidate_schemes:
            result = evaluate_eligibility(eval_profile, scheme.eligibility_rules, scheme.rule_logic)
            evaluated_schemes.append({
                "scheme": scheme,
                "eligibility": result,
            })

        # 6. Build Context for LLM
        context_schemes = []
        eligible_sources = []
        fallback_sources = []
        seen_urls = set()
        for eval_item in evaluated_schemes:
            scheme = eval_item["scheme"]
            status_val = eval_item["eligibility"].status
            sources = [{"title": s.title, "url": s.url} for s in scheme.sources if s.verification_status == "VERIFIED"]
            for src in sources:
                if src["url"] not in seen_urls:
                    if status_val == "POTENTIALLY_ELIGIBLE":
                        eligible_sources.append(src)
                        seen_urls.add(src["url"])
                    elif status_val == "INSUFFICIENT_INFORMATION":
                        fallback_sources.append(src)
                        seen_urls.add(src["url"])

            context_schemes.append({
                "name": scheme.name,
                "description": scheme.detailed_description,
                "eligibility_status": eval_item["eligibility"].model_dump(),
                "benefits": [{"type": b.benefit_type, "desc": b.description} for b in scheme.benefits],
            })

        sources_list = eligible_sources if eligible_sources else fallback_sources

        context = {
            "profile": eval_profile,
            "history": history,
            "retrieved_schemes": context_schemes,
            "language": language,
            "intent": intent,
        }

        # 7. Generate Validated Response
        response_text = await self.llm_provider.generate_response(message, context)
        self.append_conversation_turn(session, message, response_text)

        missing_fields = list(extraction.get("missing_fields", []))
        if not any(e["eligibility"].status == "POTENTIALLY_ELIGIBLE" for e in evaluated_schemes):
            for e in evaluated_schemes:
                if e["eligibility"].status == "INSUFFICIENT_INFORMATION":
                    for field in e["eligibility"].missing_information:
                        if field not in missing_fields:
                            missing_fields.append(field)

        return {
            "conversation_id": session.session_id,
            "intent": intent,
            "response_text": response_text,
            "missing_fields": missing_fields,
            "scheme_results": [{"id": e["scheme"].id, "name": e["scheme"].name, "status": e["eligibility"].status} for e in evaluated_schemes],
            "sources": sources_list,
        }
