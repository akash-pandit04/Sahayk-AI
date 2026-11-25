import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from urllib.parse import urlparse

from app.core.deps import get_db
from app.core.deps import require_admin
from app.models.admin import Admin
from app.models.ingestion import IngestionRecord, IngestionStatus
from app.models.scheme_data.models import SourceType, Scheme, SchemeStatus
from app.services.ingestion.fetcher import fetch_url
from app.services.ingestion.extractor import extract_html, extract_pdf, generate_hash
from app.services.ingestion.normalizer import normalize_scheme_text
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class IngestionUrlRequest(BaseModel):
    url: str
    source_type: SourceType

@router.post("/url")
async def ingest_url(
    req: IngestionUrlRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """Fetch and extract text from a government URL."""
    content_bytes, content_type = await fetch_url(req.url)
    
    # We only support HTML for URL ingestion right now, though could check content_type for pdf
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
        reviewer_id=current_admin.id
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
    current_admin: Admin = Depends(require_admin)
):
    """Upload and extract text from a government PDF."""
    if file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF size exceeds 10MB limit.")
        
    if not file.filename.lower().endswith(".pdf") or file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Invalid file type. Only PDF is allowed.")
        
    content_bytes = await file.read()
    raw_text = extract_pdf(content_bytes)
    c_hash = generate_hash(raw_text)
    
    record = IngestionRecord(
        source_url=source_url,
        source_type=source_type,
        source_title=file.filename,
        raw_text=raw_text,
        content_hash=c_hash,
        status=IngestionStatus.EXTRACTED,
        reviewer_id=current_admin.id
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    
    return {"id": record.id, "status": record.status, "message": "Successfully extracted text from PDF."}

@router.post("/{record_id}/normalize")
async def normalize_record(
    record_id: str,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """Calls the LLM to convert raw text into a normalized JSON structure."""
    record = db.query(IngestionRecord).filter(IngestionRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
        
    normalized = await normalize_scheme_text(record.raw_text)
    
    record.normalized_data = normalized
    record.ambiguity_flags = normalized.get("ambiguity_flags", {})
    record.status = IngestionStatus.NORMALIZED
    record.reviewed_at = datetime.utcnow()
    
    db.commit()
    return {"id": record.id, "status": record.status, "normalized_data": record.normalized_data}

@router.post("/{record_id}/approve")
async def approve_record(
    record_id: str,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_admin)
):
    """Approves the ingestion record and creates a DRAFT Scheme."""
    record = db.query(IngestionRecord).filter(IngestionRecord.id == record_id).first()
    if not record or record.status != IngestionStatus.NORMALIZED:
        raise HTTPException(status_code=400, detail="Record must be NORMALIZED to approve.")
        
    # We will build the actual scheme from normalized data in the Seeder/Admin flow.
    # In a real UI, the admin would submit the modified JSON back.
    # Here we just mark it reviewed and create a stub Draft scheme.
    
    data = record.normalized_data
    scheme = Scheme(
        name=data.get("name", "Untitled"),
        short_description=data.get("short_description", ""),
        detailed_description=data.get("detailed_description", ""),
        status=SchemeStatus.DRAFT,
        target_group=data.get("target_group"),
        application_mode=data.get("application_mode"),
        official_application_url=data.get("official_application_url"),
        version=1,
        created_by=current_admin.id
    )
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    
    record.status = IngestionStatus.REVIEWED
    record.scheme_id = scheme.id
    db.commit()
    
    return {"message": "Approved", "scheme_id": scheme.id}
