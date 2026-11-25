import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.scheme_data.models import SourceType

class IngestionStatus(str, enum.Enum):
    PENDING = "PENDING"
    EXTRACTED = "EXTRACTED"
    NORMALIZED = "NORMALIZED"
    REVIEWED = "REVIEWED"
    REJECTED = "REJECTED"

class IngestionRecord(Base):
    __tablename__ = "ingestion_records"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Source Info
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_type: Mapped[Optional[SourceType]] = mapped_column(Enum(SourceType), nullable=True)
    source_domain: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    # Processing Data
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    normalized_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ambiguity_flags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Metadata
    content_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_published_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    source_last_modified: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Workflow Status
    status: Mapped[IngestionStatus] = mapped_column(Enum(IngestionStatus), default=IngestionStatus.PENDING)
    reviewer_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("admins.id"), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Association to the final created scheme version
    scheme_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("schemes.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
