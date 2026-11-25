import enum
from datetime import datetime
import uuid
from typing import List, Optional
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Text, Enum, JSON, Integer, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.db.base_class import Base

class SchemeStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    SOURCE_VERIFIED = "SOURCE_VERIFIED"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"

class SourceType(str, enum.Enum):
    OFFICIAL_GOVERNMENT = "OFFICIAL_GOVERNMENT"
    GOVERNMENT_PORTAL = "GOVERNMENT_PORTAL"
    MINISTRY = "MINISTRY"
    STATE_GOVERNMENT = "STATE_GOVERNMENT"
    OTHER = "OTHER"

class VerificationStatus(str, enum.Enum):
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    EXPIRED = "EXPIRED"

class OperatorType(str, enum.Enum):
    EQUALS = "EQUALS"
    NOT_EQUALS = "NOT_EQUALS"
    GREATER_THAN = "GREATER_THAN"
    GREATER_THAN_EQUALS = "GREATER_THAN_EQUALS"
    LESS_THAN = "LESS_THAN"
    LESS_THAN_EQUALS = "LESS_THAN_EQUALS"
    IN = "IN"
    NOT_IN = "NOT_IN"

class DataType(str, enum.Enum):
    NUMBER = "NUMBER"
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    LIST = "LIST"

# Join tables
scheme_category_map = Table(
    "scheme_category_map",
    Base.metadata,
    Column("scheme_id", String(36), ForeignKey("schemes.id"), primary_key=True),
    Column("category_id", String(36), ForeignKey("scheme_categories.id"), primary_key=True),
)

scheme_language_map = Table(
    "scheme_language_map",
    Base.metadata,
    Column("scheme_id", String(36), ForeignKey("schemes.id"), primary_key=True),
    Column("language_code", String(10), ForeignKey("languages.code"), primary_key=True),
)

scheme_state_map = Table(
    "scheme_state_map",
    Base.metadata,
    Column("scheme_id", String(36), ForeignKey("schemes.id"), primary_key=True),
    Column("state_code", String(10), ForeignKey("states.code"), primary_key=True),
)


class Category(Base):
    __tablename__ = "scheme_categories"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class Language(Base):
    __tablename__ = "languages"
    code: Mapped[str] = mapped_column(String(10), primary_key=True) # e.g. "en", "hi", "ta"
    name: Mapped[str] = mapped_column(String)

class State(Base):
    __tablename__ = "states"
    code: Mapped[str] = mapped_column(String(10), primary_key=True) # e.g. "ALL", "MP", "UP"
    name: Mapped[str] = mapped_column(String)


class Scheme(Base):
    __tablename__ = "schemes"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, index=True)
    short_description: Mapped[str] = mapped_column(Text)
    detailed_description: Mapped[str] = mapped_column(Text)
    
    status: Mapped[SchemeStatus] = mapped_column(Enum(SchemeStatus), default=SchemeStatus.DRAFT, index=True)
    target_group: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    application_mode: Mapped[Optional[str]] = mapped_column(String, nullable=True) # Online, Offline, Both
    official_application_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_scheme_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("schemes.id"), nullable=True)
    
    rule_logic: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True) # Safe declarative AST for rules (AND/OR trees)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("admins.id"), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("admins.id"), nullable=True)

    # Relationships
    categories = relationship("Category", secondary=scheme_category_map)
    languages = relationship("Language", secondary=scheme_language_map)
    states = relationship("State", secondary=scheme_state_map)
    
    benefits = relationship("SchemeBenefit", back_populates="scheme", cascade="all, delete-orphan")
    eligibility_rules = relationship("EligibilityRule", back_populates="scheme", cascade="all, delete-orphan")
    documents = relationship("RequiredDocument", back_populates="scheme", cascade="all, delete-orphan")
    application_steps = relationship("ApplicationStep", back_populates="scheme", cascade="all, delete-orphan")
    sources = relationship("SchemeSource", back_populates="scheme", cascade="all, delete-orphan")


class SchemeBenefit(Base):
    __tablename__ = "scheme_benefits"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scheme_id: Mapped[str] = mapped_column(String(36), ForeignKey("schemes.id", ondelete="CASCADE"))
    benefit_type: Mapped[str] = mapped_column(String) # e.g. FINANCIAL, MATERIAL, SERVICE
    amount_value: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(Text)
    
    scheme = relationship("Scheme", back_populates="benefits")


class EligibilityRule(Base):
    __tablename__ = "eligibility_rules"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scheme_id: Mapped[str] = mapped_column(String(36), ForeignKey("schemes.id", ondelete="CASCADE"))
    
    # Structural components
    field: Mapped[str] = mapped_column(String) # e.g. age, income, state, caste
    operator: Mapped[OperatorType] = mapped_column(Enum(OperatorType))
    value: Mapped[str] = mapped_column(String) # Stored as string, interpreted by data_type
    data_type: Mapped[DataType] = mapped_column(Enum(DataType))
    
    group_id: Mapped[Optional[str]] = mapped_column(String, nullable=True) # for OR/AND grouping
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    scheme = relationship("Scheme", back_populates="eligibility_rules")


class RequiredDocument(Base):
    __tablename__ = "required_documents"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scheme_id: Mapped[str] = mapped_column(String(36), ForeignKey("schemes.id", ondelete="CASCADE"))
    document_name: Mapped[str] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    
    scheme = relationship("Scheme", back_populates="documents")


class ApplicationStep(Base):
    __tablename__ = "application_steps"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scheme_id: Mapped[str] = mapped_column(String(36), ForeignKey("schemes.id", ondelete="CASCADE"))
    step_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    application_mode: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    url_reference: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    scheme = relationship("Scheme", back_populates="application_steps")


class SchemeSource(Base):
    __tablename__ = "scheme_sources"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scheme_id: Mapped[str] = mapped_column(String(36), ForeignKey("schemes.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String)
    url: Mapped[str] = mapped_column(String)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType))
    verification_status: Mapped[VerificationStatus] = mapped_column(Enum(VerificationStatus), default=VerificationStatus.UNVERIFIED)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_fetched_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_by: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("admins.id"), nullable=True)
    
    scheme = relationship("Scheme", back_populates="sources")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    admin_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("admins.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String, index=True) # e.g. CREATE, UPDATE, PUBLISH, ARCHIVE, DELETE
    entity_type: Mapped[str] = mapped_column(String, index=True) # e.g. SCHEME, RULE, SOURCE
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    before_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class SchemeEmbedding(Base):
    __tablename__ = "scheme_embeddings"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    scheme_id: Mapped[str] = mapped_column(String(36), ForeignKey("schemes.id", ondelete="CASCADE"), unique=True)
    model_name: Mapped[str] = mapped_column(String)
    dimension: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String)
    embedding = mapped_column(Vector(1536))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ConversationSession(Base):
    __tablename__ = "conversation_sessions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    profile_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

