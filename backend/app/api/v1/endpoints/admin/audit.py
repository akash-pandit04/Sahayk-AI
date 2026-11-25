from typing import Any, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.deps import get_db, require_admin
from app.models.admin import Admin
from app.models.scheme_data.models import AuditLog
from app.schemas.scheme_data.schemas import AuditLogResponse
from app.schemas.response import SuccessResponse

router = APIRouter()

@router.get("", response_model=SuccessResponse)
def get_audit_logs(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin),
    skip: int = 0,
    limit: int = 100,
    entity_type: Optional[str] = None
) -> Any:
    query = db.query(AuditLog)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    
    total = query.count()
    logs = query.order_by(desc(AuditLog.timestamp)).offset(skip).limit(limit).all()
    
    data = [AuditLogResponse.model_validate(l).model_dump() for l in logs]
    return SuccessResponse(data={"items": data, "total": total, "skip": skip, "limit": limit})
