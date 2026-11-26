from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.v1.endpoints.admin.categories import log_audit
from app.core.deps import get_db, require_admin
from app.models.admin import Admin
from app.models.ingestion import IngestionRecord, IngestionStatus
from app.models.scheme_data.models import (
    ApplicationStep,
    DataType,
    EligibilityRule,
    OperatorType,
    RequiredDocument,
    Scheme,
    SchemeBenefit,
    SchemeSource,
    SchemeStatus,
    SourceType,
    VerificationStatus,
)
from app.services.ingestion.extractor import extract_html, extract_pdf, generate_hash
from app.services.ingestion.fetcher import fetch_url
from app.services.ingestion.normalizer import normalize_scheme_text

router = APIRouter()


class IngestionUrlRequest(BaseModel):
    url: str
    source_type: SourceType


class IngestionApproveRequest(BaseModel):
    normalized_data: Optional[Dict[str, Any]] = None


class IngestionRejectRequest(BaseModel):
    reason: str = "Rejected by admin during review."


def _serialize_record(record: IngestionRecord, include_raw: bool = False) -> Dict[str, Any]:
    data = {
        "id": record.id,
        "source_url": record.source_url,
        "source_type": record.source_type.value if record.source_type else None,
        "source_domain": record.source_domain,
        "source_title": record.source_title,
        "normalized_data": record.normalized_data,
        "ambiguity_flags": record.ambiguity_flags,
        "content_hash": record.content_hash,
        "fetched_at": record.fetched_at.isoformat() if record.fetched_at else None,
        "status": record.status.value if record.status else None,
        "reviewer_id": record.reviewer_id,
        "reviewed_at": record.reviewed_at.isoformat() if record.reviewed_at else None,
        "rejection_reason": record.rejection_reason,
        "scheme_id": record.scheme_id,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
    if include_raw:
        data["raw_text"] = record.raw_text
    return data


@router.get("")
def list_ingestion_records(
    status: Optional[IngestionStatus] = None,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin),
):
    """Lists all ingestion records ordered by newest first."""
    query = db.query(IngestionRecord)
    if status:
        query = query.filter(IngestionRecord.status == status)
    records = query.order_by(desc(IngestionRecord.created_at)).limit(100).all()
    return {"items": [_serialize_record(r) for r in records]}


@router.get("/{record_id}")
def get_ingestion_record(
    record_id: str,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin),
):
    """Returns full ingestion record details including extracted raw text."""
    record = db.query(IngestionRecord).filter(IngestionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return _serialize_record(record, include_raw=True)


@router.post("/url")
async def ingest_url(
    req: IngestionUrlRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin),
):
    """Fetch and extract text from a government URL."""
    content_bytes, content_type = await fetch_url(req.url)

    if "application/pdf" in content_type:
        raw_text = extract_pdf(content_bytes)
    else:
        raw_text = extract_html(content_bytes)

    c_hash = generate_hash(raw_text)

    record = IngestionRecord(
        source_url=req.url,
        source_type=req.source_type,
        source_domain=urlparse(req.url).netloc,
        raw_text=raw_text,
        content_hash=c_hash,
        status=IngestionStatus.EXTRACTED,
        reviewer_id=current_admin.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"id": record.id, "status": record.status, "message": "Successfully extracted text."}


@router.post("/pdf")
async def ingest_pdf(
    source_type: SourceType = Form(...),
    source_url: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin),
):
    """Upload and extract text from a government PDF."""
    content_bytes = await file.read()
    if len(content_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF size exceeds 10MB limit.")

    if not (file.filename or "").lower().endswith(".pdf") or file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF is allowed.")

    raw_text = extract_pdf(content_bytes)
    c_hash = generate_hash(raw_text)

    record = IngestionRecord(
        source_url=source_url,
        source_type=source_type,
        source_title=file.filename,
        raw_text=raw_text,
        content_hash=c_hash,
        status=IngestionStatus.EXTRACTED,
        reviewer_id=current_admin.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return {"id": record.id, "status": record.status, "message": "Successfully extracted text from PDF."}


@router.post("/{record_id}/normalize")
async def normalize_record(
    record_id: str,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin),
):
    """Calls the LLM to convert raw text into a normalized JSON structure."""
    record = db.query(IngestionRecord).filter(IngestionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    normalized = await normalize_scheme_text(record.raw_text or "")

    record.normalized_data = normalized
    record.ambiguity_flags = normalized.get("ambiguity_flags", {})
    record.status = IngestionStatus.NORMALIZED
    record.reviewed_at = datetime.utcnow()

    db.commit()
    return {"id": record.id, "status": record.status, "normalized_data": record.normalized_data}


@router.post("/{record_id}/reject")
def reject_record(
    record_id: str,
    req: IngestionRejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin),
):
    """Rejects an ingestion record during human review."""
    record = db.query(IngestionRecord).filter(IngestionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    record.status = IngestionStatus.REJECTED
    record.rejection_reason = req.reason
    record.reviewer_id = current_admin.id
    record.reviewed_at = datetime.utcnow()
    db.commit()

    log_audit(
        db,
        current_admin.id,
        "REJECT",
        "INGESTION_RECORD",
        record.id,
        None,
        {"reason": req.reason},
        request.client.host if request.client else None,
    )
    return {"id": record.id, "status": record.status.value}


@router.post("/{record_id}/approve")
async def approve_record(
    record_id: str,
    request: Request,
    req: Optional[IngestionApproveRequest] = Body(default=None),
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin),
):
    """Approves the normalized ingestion proposal and creates a DRAFT Scheme."""
    record = db.query(IngestionRecord).filter(IngestionRecord.id == record_id).first()
    if not record or record.status != IngestionStatus.NORMALIZED:
        raise HTTPException(status_code=400, detail="Record must be NORMALIZED to approve.")

    data = (req.normalized_data if req and req.normalized_data is not None else record.normalized_data) or {}
    scheme = Scheme(
        name=data.get("name", "Untitled"),
        short_description=data.get("short_description", ""),
        detailed_description=data.get("detailed_description", ""),
        status=SchemeStatus.DRAFT,
        target_group=data.get("target_group"),
        application_mode=data.get("application_mode"),
        official_application_url=data.get("official_application_url") or record.source_url,
        version=1,
        created_by=current_admin.id,
        updated_by=current_admin.id,
    )
    db.add(scheme)
    db.flush()

    if record.source_url:
        db.add(
            SchemeSource(
                scheme_id=scheme.id,
                title=record.source_title or record.source_domain or "Ingested Source",
                url=record.source_url,
                source_type=record.source_type or SourceType.OTHER,
                verification_status=VerificationStatus.UNVERIFIED,
                content_hash=record.content_hash,
                last_fetched_at=record.fetched_at,
            )
        )

    for b in data.get("benefits", []) or []:
        if isinstance(b, dict) and b.get("description"):
            db.add(
                SchemeBenefit(
                    scheme_id=scheme.id,
                    benefit_type=b.get("benefit_type", "SERVICE"),
                    amount_value=b.get("amount_value"),
                    description=b["description"],
                )
            )

    for r in data.get("rules", []) or []:
        if not isinstance(r, dict):
            continue
        try:
            op = OperatorType(r.get("operator", ""))
            dt = DataType(r.get("data_type", ""))
        except ValueError:
            continue
        if r.get("field") and r.get("value") is not None:
            db.add(
                EligibilityRule(
                    scheme_id=scheme.id,
                    field=str(r["field"]),
                    operator=op,
                    value=str(r["value"]),
                    data_type=dt,
                    explanation=r.get("explanation"),
                )
            )

    for idx, d in enumerate(data.get("documents", []) or []):
        if isinstance(d, dict) and d.get("document_name"):
            db.add(
                RequiredDocument(
                    scheme_id=scheme.id,
                    document_name=d["document_name"],
                    description=d.get("description"),
                    is_mandatory=bool(d.get("is_mandatory", True)),
                    display_order=idx,
                )
            )

    for idx, s in enumerate(data.get("steps", []) or [], start=1):
        if isinstance(s, dict) and s.get("title") and s.get("description"):
            db.add(
                ApplicationStep(
                    scheme_id=scheme.id,
                    step_number=int(s.get("step_number", idx)),
                    title=s["title"],
                    description=s["description"],
                    application_mode=s.get("application_mode"),
                    url_reference=s.get("url_reference"),
                )
            )

    record.normalized_data = data
    record.status = IngestionStatus.REVIEWED
    record.scheme_id = scheme.id
    record.reviewer_id = current_admin.id
    record.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(scheme)

    log_audit(
        db,
        current_admin.id,
        "APPROVE_INGESTION",
        "SCHEME",
        scheme.id,
        None,
        {"ingestion_record_id": record.id, "status": SchemeStatus.DRAFT.value},
        request.client.host if request.client else None,
    )

    return {"message": "Approved", "scheme_id": scheme.id}
