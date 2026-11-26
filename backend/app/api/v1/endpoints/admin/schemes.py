from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.deps import get_db, require_admin
from app.models.admin import Admin
from app.models.scheme_data.models import (
    Scheme, Category, SchemeStatus, SourceType, VerificationStatus,
    SchemeBenefit, EligibilityRule, RequiredDocument, ApplicationStep, SchemeSource
)
from app.schemas.scheme_data.schemas import (
    SchemeCreate, SchemeUpdate, SchemeResponse,
    SchemeBenefitCreate, EligibilityRuleCreate, RequiredDocumentCreate, ApplicationStepCreate,
    SchemeSourceCreate, SchemeSourceUpdate,
)
from app.schemas.response import SuccessResponse
from app.api.v1.endpoints.admin.categories import log_audit
from app.services.ingestion.fetcher import fetch_url
from app.services.ingestion.extractor import extract_html, extract_pdf, generate_hash

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
        authoritative_types = {
            SourceType.OFFICIAL_GOVERNMENT,
            SourceType.STATE_GOVERNMENT,
            SourceType.GOVERNMENT_PORTAL,
            SourceType.MINISTRY,
        }
        if not scheme.sources or not any(
            s.verification_status == VerificationStatus.VERIFIED and s.source_type in authoritative_types
            for s in scheme.sources
        ):
            raise HTTPException(
                status_code=400,
                detail="Cannot publish: scheme must have at least one verified official government source.",
            )
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


@router.patch("/{id}/sources/{source_id}", response_model=SuccessResponse)
def update_source(
    id: str,
    source_id: str,
    source_in: SchemeSourceUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin),
) -> Any:
    """Updates or verifies an existing scheme source."""
    source = db.query(SchemeSource).filter(SchemeSource.id == source_id, SchemeSource.scheme_id == id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    update_data = source_in.model_dump(exclude_unset=True)
    if update_data.get("verification_status") == VerificationStatus.VERIFIED:
        if (update_data.get("source_type") or source.source_type) == SourceType.OTHER:
            raise HTTPException(status_code=400, detail="Only official government sources can be verified.")
        source.verified_by = current_admin.id
        source.last_verified_at = datetime.utcnow()

    for field, value in update_data.items():
        setattr(source, field, value)

    db.commit()
    db.refresh(source)
    log_audit(db, current_admin.id, "UPDATE", "SOURCE", source.id, None, update_data, request.client.host if request.client else None)
    return SuccessResponse(data={"id": source.id, "verification_status": source.verification_status.value})


@router.post("/{id}/sources/{source_id}/recheck", response_model=SuccessResponse)
async def recheck_source(
    id: str,
    source_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin),
) -> Any:
    """Re-fetches a source URL to verify freshness and detect content hash changes."""
    source = db.query(SchemeSource).filter(SchemeSource.id == source_id, SchemeSource.scheme_id == id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    content_bytes, content_type = await fetch_url(source.url)
    raw_text = extract_pdf(content_bytes) if "application/pdf" in content_type else extract_html(content_bytes)
    new_hash = generate_hash(raw_text)
    now = datetime.utcnow()

    changed = bool(source.content_hash and source.content_hash != new_hash)
    before_status = source.verification_status.value
    source.last_fetched_at = now
    source.content_hash = new_hash

    if changed:
        source.verification_status = VerificationStatus.NEEDS_REVIEW
        action = "SOURCE_CHANGED"
    else:
        if source.verification_status == VerificationStatus.VERIFIED:
            source.last_verified_at = now
            source.verified_by = current_admin.id
        action = "SOURCE_RECHECKED"

    db.commit()
    db.refresh(source)

    log_audit(
        db,
        current_admin.id,
        action,
        "SOURCE",
        source.id,
        {"verification_status": before_status},
        {"verification_status": source.verification_status.value, "content_hash": new_hash},
        request.client.host if request.client else None,
    )
    return SuccessResponse(
        data={
            "id": source.id,
            "changed": changed,
            "verification_status": source.verification_status.value,
            "content_hash": source.content_hash,
            "last_fetched_at": source.last_fetched_at.isoformat() if source.last_fetched_at else None,
            "last_verified_at": source.last_verified_at.isoformat() if source.last_verified_at else None,
        }
    )


@router.post("/{id}/new-version", response_model=SuccessResponse)
def create_scheme_version(
    id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin),
) -> Any:
    """Creates a new DRAFT version linked via parent_scheme_id without modifying the existing version."""
    parent = db.query(Scheme).filter(Scheme.id == id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Scheme not found")

    draft_v2 = Scheme(
        name=parent.name,
        short_description=parent.short_description,
        detailed_description=parent.detailed_description,
        status=SchemeStatus.DRAFT,
        target_group=parent.target_group,
        application_mode=parent.application_mode,
        official_application_url=parent.official_application_url,
        version=parent.version + 1,
        parent_scheme_id=parent.id,
        rule_logic=parent.rule_logic,
        categories=list(parent.categories),
        languages=list(parent.languages),
        states=list(parent.states),
        created_by=current_admin.id,
        updated_by=current_admin.id,
    )
    db.add(draft_v2)
    db.flush()

    for b in parent.benefits:
        db.add(SchemeBenefit(scheme_id=draft_v2.id, benefit_type=b.benefit_type, amount_value=b.amount_value, description=b.description))
    for r in parent.eligibility_rules:
        db.add(
            EligibilityRule(
                scheme_id=draft_v2.id,
                field=r.field,
                operator=r.operator,
                value=r.value,
                data_type=r.data_type,
                group_id=r.group_id,
                is_mandatory=r.is_mandatory,
                explanation=r.explanation,
            )
        )
    for d in parent.documents:
        db.add(
            RequiredDocument(
                scheme_id=draft_v2.id,
                document_name=d.document_name,
                description=d.description,
                is_mandatory=d.is_mandatory,
                notes=d.notes,
                display_order=d.display_order,
            )
        )
    for s in parent.application_steps:
        db.add(
            ApplicationStep(
                scheme_id=draft_v2.id,
                step_number=s.step_number,
                title=s.title,
                description=s.description,
                application_mode=s.application_mode,
                url_reference=s.url_reference,
            )
        )
    for src in parent.sources:
        db.add(
            SchemeSource(
                scheme_id=draft_v2.id,
                title=src.title,
                url=src.url,
                source_type=src.source_type,
                verification_status=VerificationStatus.UNVERIFIED,
                content_hash=src.content_hash,
                last_fetched_at=src.last_fetched_at,
                notes=src.notes,
            )
        )

    db.commit()
    db.refresh(draft_v2)

    log_audit(
        db,
        current_admin.id,
        "CREATE_VERSION",
        "SCHEME",
        draft_v2.id,
        {"parent_scheme_id": parent.id, "parent_version": parent.version},
        {"version": draft_v2.version, "status": SchemeStatus.DRAFT.value},
        request.client.host if request.client else None,
    )
    return SuccessResponse(data=SchemeResponse.model_validate(draft_v2).model_dump())

