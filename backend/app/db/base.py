# Import all the models, so that Base has them before being
# imported by Alembic
from app.db.base_class import Base
from app.models.admin import Admin
from app.models.scheme_data.models import (
    Category, Language, State, Scheme, SchemeBenefit, 
    EligibilityRule, RequiredDocument, ApplicationStep, 
    SchemeSource, AuditLog, SchemeEmbedding, ConversationSession
)
from app.models.ingestion import IngestionRecord
