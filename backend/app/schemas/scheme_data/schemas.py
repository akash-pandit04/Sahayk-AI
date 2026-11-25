from typing import List, Optional, Any
from pydantic import BaseModel, HttpUrl, Field, field_validator
from datetime import datetime
from app.models.scheme_data.models import (
    SchemeStatus, SourceType, VerificationStatus,
    OperatorType, DataType
)

# Base models
class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: str
    class Config:
        from_attributes = True


class SchemeBenefitBase(BaseModel):
    benefit_type: str
    amount_value: Optional[str] = None
    description: str

class SchemeBenefitCreate(SchemeBenefitBase):
    pass

class SchemeBenefitResponse(SchemeBenefitBase):
    id: str
    scheme_id: str
    class Config:
        from_attributes = True


class EligibilityRuleBase(BaseModel):
    field: str
    operator: OperatorType
    value: str
    data_type: DataType
    group_id: Optional[str] = None
    is_mandatory: bool = True
    explanation: Optional[str] = None

class EligibilityRuleCreate(EligibilityRuleBase):
    pass

class EligibilityRuleResponse(EligibilityRuleBase):
    id: str
    scheme_id: str
    class Config:
        from_attributes = True


class RequiredDocumentBase(BaseModel):
    document_name: str
    description: Optional[str] = None
    is_mandatory: bool = True
    notes: Optional[str] = None
    display_order: int = 0

class RequiredDocumentCreate(RequiredDocumentBase):
    pass

class RequiredDocumentResponse(RequiredDocumentBase):
    id: str
    scheme_id: str
    class Config:
        from_attributes = True


class ApplicationStepBase(BaseModel):
    step_number: int
    title: str
    description: str
    application_mode: Optional[str] = None
    url_reference: Optional[str] = None # Relaxing from HttpUrl to allow simple refs

class ApplicationStepCreate(ApplicationStepBase):
    pass

class ApplicationStepResponse(ApplicationStepBase):
    id: str
    scheme_id: str
    class Config:
        from_attributes = True


class SchemeSourceBase(BaseModel):
    title: str
    url: str
    source_type: SourceType
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    notes: Optional[str] = None

class SchemeSourceCreate(SchemeSourceBase):
    pass

class SchemeSourceUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    source_type: Optional[SourceType] = None
    verification_status: Optional[VerificationStatus] = None
    notes: Optional[str] = None

class SchemeSourceResponse(SchemeSourceBase):
    id: str
    scheme_id: str
    last_verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    class Config:
        from_attributes = True


class SchemeBase(BaseModel):
    name: str
    short_description: str
    detailed_description: str
    status: SchemeStatus = SchemeStatus.DRAFT
    target_group: Optional[str] = None
    application_mode: Optional[str] = None
    official_application_url: Optional[str] = None

class SchemeCreate(SchemeBase):
    category_ids: List[str] = []
    # Optionally nested creation
    # benefits: List[SchemeBenefitCreate] = []
    # rules: List[EligibilityRuleCreate] = []
    pass

class SchemeUpdate(BaseModel):
    name: Optional[str] = None
    short_description: Optional[str] = None
    detailed_description: Optional[str] = None
    status: Optional[SchemeStatus] = None
    target_group: Optional[str] = None
    application_mode: Optional[str] = None
    official_application_url: Optional[str] = None
    category_ids: Optional[List[str]] = None

class SchemeResponse(SchemeBase):
    id: str
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    
    categories: List[CategoryResponse] = []
    benefits: List[SchemeBenefitResponse] = []
    eligibility_rules: List[EligibilityRuleResponse] = []
    documents: List[RequiredDocumentResponse] = []
    application_steps: List[ApplicationStepResponse] = []
    sources: List[SchemeSourceResponse] = []
    
    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: str
    admin_id: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    timestamp: datetime
    before_state: Optional[Any] = None
    after_state: Optional[Any] = None
    ip_address: Optional[str] = None
    class Config:
        from_attributes = True
