from pydantic import BaseModel
from typing import Any, Optional, Dict

class SuccessResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: Dict[str, Any]
