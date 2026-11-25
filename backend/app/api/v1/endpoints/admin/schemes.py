from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.deps import get_db, require_admin
from app.models.admin import Admin
from app.models.scheme_data.models import (
    Scheme, Category, SchemeStatus, VerificationStatus,
    SchemeBenefit, EligibilityRule, RequiredDocument, ApplicationStep, SchemeSource
)
from app.schemas.scheme_data.schemas import (
    SchemeCreate, SchemeUpdate, SchemeResponse,
    SchemeBenefitCreate, EligibilityRuleCreate, RequiredDocumentCreate, ApplicationStepCreate, SchemeSourceCreate
)
from app.schemas.response import SuccessResponse
from app.api.v1.endpoints.admin.categories import log_audit

router = APIRouter()

@router.get("", response_model=SuccessResponse)
def get_schemes(
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    status: Optional[SchemeStatus] = None
) -> Any:
    query = db.query(Scheme)
    if status:
        query = query.filter(Scheme.status == status)
    if search:
        query = query.filter(Scheme.name.ilike(f"%{search}%"))
        
    total = query.count()
    schemes = query.order_by(desc(Scheme.created_at)).offset(skip).limit(limit).all()
    
    data = [SchemeResponse.model_validate(s).model_dump() for s in schemes]
    return SuccessResponse(data={"items": data, "total": total, "skip": skip, "limit": limit})

@router.post("", response_model=SuccessResponse)
def create_scheme(
    scheme_in: SchemeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
) -> Any:
    db_scheme = Scheme(
        name=scheme_in.name,
        short_description=scheme_in.short_description,
        detailed_description=scheme_in.detailed_description,
        status=scheme_in.status,
        target_group=scheme_in.target_group,
        application_mode=scheme_in.application_mode,
        official_application_url=scheme_in.official_application_url,
        created_by=current_admin.id,
        updated_by=current_admin.id
    )
    
    if scheme_in.category_ids:
        categories = db.query(Category).filter(Category.id.in_(scheme_in.category_ids)).all()
        db_scheme.categories = categories

    db.add(db_scheme)
    db.commit()
    db.refresh(db_scheme)
    
    log_audit(db, current_admin.id, "CREATE", "SCHEME", db_scheme.id, None, {"name": db_scheme.name}, request.client.host)
    return SuccessResponse(data=SchemeResponse.model_validate(db_scheme).model_dump())

@router.get("/{id}", response_model=SuccessResponse)
def get_scheme(
    id: str,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
) -> Any:
    scheme = db.query(Scheme).filter(Scheme.id == id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return SuccessResponse(data=SchemeResponse.model_validate(scheme).model_dump())

@router.patch("/{id}", response_model=SuccessResponse)
def update_scheme(
    id: str,
    scheme_in: SchemeUpdate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
) -> Any:
    scheme = db.query(Scheme).filter(Scheme.id == id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
        
    before_state = {"status": scheme.status}
        
    update_data = scheme_in.model_dump(exclude_unset=True)
    
    # Check publishing constraints
    if "status" in update_data and update_data["status"] == SchemeStatus.PUBLISHED:
        if not scheme.sources or not any(s.verification_status == VerificationStatus.VERIFIED for s in scheme.sources):
            raise HTTPException(status_code=400, detail="Cannot publish: scheme must have at least one verified source.")
        if not scheme.eligibility_rules:
            raise HTTPException(status_code=400, detail="Cannot publish: scheme must have eligibility rules.")
        if not scheme.benefits:
            raise HTTPException(status_code=400, detail="Cannot publish: scheme must have at least one benefit.")

    if "category_ids" in update_data:
        categories = db.query(Category).filter(Category.id.in_(update_data["category_ids"])).all()
        scheme.categories = categories
        del update_data["category_ids"]

    for field, value in update_data.items():
        setattr(scheme, field, value)
        
    scheme.updated_by = current_admin.id
    db.commit()
    db.refresh(scheme)
    
    after_state = {"status": scheme.status}
    log_audit(db, current_admin.id, "UPDATE", "SCHEME", scheme.id, before_state, after_state, request.client.host)
    
    # If status changed to PUBLISHED (or any update to a published/archived scheme), sync embedding
    # We use a background task so external API failure doesn't block the CMS update.
    if scheme.status == SchemeStatus.PUBLISHED or scheme.status == SchemeStatus.ARCHIVED:
        from app.services.ai.retrieval import RetrievalService
        import asyncio
        
        def run_sync(s_id: str):
            # new db session for background task
            from app.db.session import SessionLocal
            db_bg = SessionLocal()
            try:
                retriever = RetrievalService(db_bg)
                asyncio.run(retriever.sync_scheme_embedding(s_id))
            except Exception as e:
                import logging
                logging.error(f"Failed to sync embedding for scheme {s_id}: {e}")
            finally:
                db_bg.close()

        background_tasks.add_task(run_sync, scheme.id)

    return SuccessResponse(data=SchemeResponse.model_validate(scheme).model_dump())


# Sub-resources for a scheme
@router.post("/{id}/benefits", response_model=SuccessResponse)
def add_benefit(id: str, benefit_in: SchemeBenefitCreate, request: Request, db: Session = Depends(get_db), current_admin: Admin = Depends(require_admin)):
    scheme = db.query(Scheme).filter(Scheme.id == id).first()
    if not scheme: raise HTTPException(status_code=404)
    benefit = SchemeBenefit(**benefit_in.model_dump(), scheme_id=id)
    db.add(benefit)
    db.commit()
    log_audit(db, current_admin.id, "CREATE", "BENEFIT", benefit.id, None, benefit_in.model_dump(), request.client.host)
    return SuccessResponse(data={"message": "Added benefit"})

@router.post("/{id}/rules", response_model=SuccessResponse)
def add_rule(id: str, rule_in: EligibilityRuleCreate, request: Request, db: Session = Depends(get_db), current_admin: Admin = Depends(require_admin)):
    scheme = db.query(Scheme).filter(Scheme.id == id).first()
    if not scheme: raise HTTPException(status_code=404)
    rule = EligibilityRule(**rule_in.model_dump(), scheme_id=id)
    db.add(rule)
    db.commit()
    log_audit(db, current_admin.id, "CREATE", "RULE", rule.id, None, rule_in.model_dump(), request.client.host)
    return SuccessResponse(data={"message": "Added rule"})

@router.post("/{id}/documents", response_model=SuccessResponse)
def add_document(id: str, doc_in: RequiredDocumentCreate, request: Request, db: Session = Depends(get_db), current_admin: Admin = Depends(require_admin)):
    scheme = db.query(Scheme).filter(Scheme.id == id).first()
    if not scheme: raise HTTPException(status_code=404)
    doc = RequiredDocument(**doc_in.model_dump(), scheme_id=id)
    db.add(doc)
    db.commit()
    log_audit(db, current_admin.id, "CREATE", "DOCUMENT", doc.id, None, doc_in.model_dump(), request.client.host)
    return SuccessResponse(data={"message": "Added document"})

@router.post("/{id}/steps", response_model=SuccessResponse)
def add_step(id: str, step_in: ApplicationStepCreate, request: Request, db: Session = Depends(get_db), current_admin: Admin = Depends(require_admin)):
    scheme = db.query(Scheme).filter(Scheme.id == id).first()
    if not scheme: raise HTTPException(status_code=404)
    step = ApplicationStep(**step_in.model_dump(), scheme_id=id)
    db.add(step)
    db.commit()
    log_audit(db, current_admin.id, "CREATE", "STEP", step.id, None, step_in.model_dump(), request.client.host)
    return SuccessResponse(data={"message": "Added application step"})

@router.post("/{id}/sources", response_model=SuccessResponse)
def add_source(id: str, source_in: SchemeSourceCreate, request: Request, db: Session = Depends(get_db), current_admin: Admin = Depends(require_admin)):
    scheme = db.query(Scheme).filter(Scheme.id == id).first()
    if not scheme: raise HTTPException(status_code=404)
    
    source_data = source_in.model_dump()
    if source_data.get("verification_status") == VerificationStatus.VERIFIED:
        source_data["verified_by"] = current_admin.id
        from datetime import datetime
        source_data["last_verified_at"] = datetime.utcnow()
        
    source = SchemeSource(**source_data, scheme_id=id)
    db.add(source)
    db.commit()
    log_audit(db, current_admin.id, "CREATE", "SOURCE", source.id, None, source_in.model_dump(), request.client.host)
    return SuccessResponse(data={"message": "Added source"})

