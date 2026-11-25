from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Any
import logging

from app.core.deps import get_db
from app.schemas.response import SuccessResponse, ErrorResponse

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("", response_model=SuccessResponse)
def health_check() -> Any:
    """
    Check API health.
    """
    return SuccessResponse(data={"status": "API is operational"})

@router.get("/db", response_model=SuccessResponse, responses={status.HTTP_500_INTERNAL_SERVER_ERROR: {"model": ErrorResponse}})
def db_health_check(db: Session = Depends(get_db)) -> Any:
    """
    Check Database connectivity and health.
    """
    try:
        # Execute a simple query
        db.execute(text("SELECT 1"))
        return SuccessResponse(data={"status": "Database is connected and operational"})
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "DATABASE_UNAVAILABLE",
                    "message": "Could not connect to the database"
                }
            }
        )
