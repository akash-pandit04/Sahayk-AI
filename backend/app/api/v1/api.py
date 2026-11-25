from fastapi import APIRouter
from app.api.v1.endpoints.admin import schemes, categories, audit, ingestion
from app.api.v1.endpoints import assistant, health, auth, voice

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])

# Admin routes
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
# Dashboard uses schemes endpoint directly, there is no dashboard router in Phase 2
api_router.include_router(schemes.router, prefix="/admin/schemes", tags=["admin-schemes"])
api_router.include_router(categories.router, prefix="/admin/categories", tags=["admin-categories"])
api_router.include_router(audit.router, prefix="/admin/audit-logs", tags=["admin-audit"])
api_router.include_router(ingestion.router, prefix="/admin/ingestion", tags=["admin-ingestion"])

# Public Assistant Routes
api_router.include_router(assistant.router, prefix="/assistant", tags=["assistant"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
