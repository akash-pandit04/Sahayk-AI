from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.deps import get_db, rate_limit
from app.services.ai.orchestrator import AssistantOrchestrator

router = APIRouter()

class AssistantQueryRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    language: str = "hi"

class SchemeResult(BaseModel):
    id: str
    name: str
    status: str

class Source(BaseModel):
    title: str
    url: str

class AssistantQueryResponse(BaseModel):
    conversation_id: str
    language: str
    intent: str
    response_text: str
    needs_more_information: bool
    missing_fields: List[str]
    scheme_results: List[SchemeResult]
    sources: List[Source]

@router.post("/query", response_model=AssistantQueryResponse, dependencies=[Depends(rate_limit(requests=20, window=60))])
async def process_query(
    query_in: AssistantQueryRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public AI Assistant endpoint.
    Includes basic abuse protection in the future.
    """
    if len(query_in.message) > 500:
        raise HTTPException(status_code=400, detail="Message too long")
        
    orchestrator = AssistantOrchestrator(db)
    
    try:
        result = await orchestrator.process_query(
            session_id=query_in.conversation_id,
            message=query_in.message,
            language=query_in.language
        )
        
        return AssistantQueryResponse(
            conversation_id=result["conversation_id"],
            language=query_in.language,
            intent=result.get("intent", "UNKNOWN"),
            response_text=result["response_text"],
            needs_more_information=len(result.get("missing_fields", [])) > 0,
            missing_fields=result.get("missing_fields", []),
            scheme_results=result.get("scheme_results", []),
            sources=result.get("sources", [])
        )
    except Exception as e:
        import logging
        logging.exception("Assistant Error")
        raise HTTPException(status_code=500, detail="An error occurred processing the assistant query.")
