from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
import json

from app.core.deps import get_db, require_admin
from app.models.admin import Admin
from app.models.scheme_data.models import Category, AuditLog
from app.schemas.scheme_data.schemas import CategoryCreate, CategoryResponse
from app.schemas.response import SuccessResponse

router = APIRouter()

def log_audit(db: Session, admin_id: str, action: str, entity_type: str, entity_id: str, before=None, after=None, ip=None):
    log = AuditLog(
        admin_id=admin_id, action=action, entity_type=entity_type,
        entity_id=entity_id, before_state=before, after_state=after, ip_address=ip
    )
    db.add(log)
    db.commit()

@router.get("", response_model=SuccessResponse)
def get_categories(db: Session = Depends(get_db), current_admin: Admin = Depends(require_admin)) -> Any:
    cats = db.query(Category).all()
    return SuccessResponse(data=[CategoryResponse.model_validate(c).model_dump() for c in cats])

@router.post("", response_model=SuccessResponse)
def create_category(
    cat_in: CategoryCreate, 
    request: Request,
    db: Session = Depends(get_db), 
    current_admin: Admin = Depends(require_admin)
) -> Any:
    if db.query(Category).filter(Category.name == cat_in.name).first():
        raise HTTPException(status_code=400, detail="Category exists")
    
    cat = Category(**cat_in.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    
    log_audit(db, current_admin.id, "CREATE", "CATEGORY", cat.id, None, cat_in.model_dump(), request.client.host)
    return SuccessResponse(data=CategoryResponse.model_validate(cat).model_dump())
