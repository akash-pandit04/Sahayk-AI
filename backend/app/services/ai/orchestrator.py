import uuid
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from app.models.scheme_data.models import ConversationSession, Scheme
from app.services.ai.providers.factory import get_llm_provider
from app.services.ai.retrieval import RetrievalService
from app.services.eligibility.engine import evaluate_eligibility

class AssistantOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        self.llm_provider = get_llm_provider()
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
            
        # Merge updates. We treat None as 'remove' or 'unknown'
        current_data = dict(session.profile_data)
        for k, v in updates.items():
            if v is None and k in current_data:
                del current_data[k]
            elif v is not None:
                current_data[k] = v
                
        session.profile_data = current_data
        self.db.commit()
        self.db.refresh(session)

    async def process_query(self, session_id: str, message: str, language: str = "en") -> dict:
        # 1. Load Session
        session = self.get_or_create_session(session_id)
        
        # 2. Extract Intent and Profile Updates
        extraction = await self.llm_provider.extract_intent_and_profile(message, session.profile_data)
        
        # 3. Update Profile Context
        if extraction.get("profile_updates"):
            self.update_session_profile(session, extraction["profile_updates"])
            
        intent = extraction.get("intent", "GENERAL_QUESTION")
        
        # 4. Retrieval (Only Published Schemes)
        candidate_schemes = await self.retrieval_service.search_schemes(message, limit=5)
        
        # 5. Deterministic Eligibility Evaluation (Source of Truth)
        evaluated_schemes = []
        for scheme in candidate_schemes:
            result = evaluate_eligibility(session.profile_data, scheme.eligibility_rules, scheme.rule_logic)
            evaluated_schemes.append({
                "scheme": scheme,
                "eligibility": result
            })
            
        # Re-rank or Filter based on eligibility
        # For simplicity, we just pass the evaluated schemes down.
        
        # 6. Build Context for LLM
        # Do not leak DB models directly, serialize safely.
        context_schemes = []
        sources_list = []
        for eval_item in evaluated_schemes:
            scheme = eval_item["scheme"]
            sources = [{"title": s.title, "url": s.url} for s in scheme.sources if s.verification_status == "VERIFIED"]
            sources_list.extend(sources)
            
            context_schemes.append({
                "name": scheme.name,
                "description": scheme.detailed_description,
                "eligibility_status": eval_item["eligibility"].dict(),
                "benefits": [{"type": b.benefit_type, "desc": b.description} for b in scheme.benefits]
            })

        context = {
            "profile": session.profile_data,
            "retrieved_schemes": context_schemes,
            "language": language
        }
        
        # 7. Generate Validated Response
        response_text = await self.llm_provider.generate_response(message, context)
        
        # 8. Post-generation validation
        # (e.g. string matching to ensure we don't invent schemes)
        # If the LLM mentions a scheme name not in context_schemes, we might fallback.
        # For MVP, we trust the LLMProvider's system prompt to enforce this.
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
            "sources": sources_list
        }
