from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.admin import Admin
from app.schemas.token import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)

def get_db() -> Generator:
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()

def get_current_admin(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> Admin:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    
    admin = db.query(Admin).filter(Admin.id == token_data.sub).first()
    if not admin:
        raise HTTPException(status_code=404, detail="Admin not found")
    if not admin.is_active:
        raise HTTPException(status_code=400, detail="Inactive admin")
    
    return admin

def require_admin(current_admin: Admin = Depends(get_current_admin)) -> Admin:
    """Dependency for ensuring the user is a valid, active admin."""
    return current_admin

import time
from fastapi import Request

# Simple in-memory rate limiting for MVP
_rate_limit_store = {}

def rate_limit(requests: int = 10, window: int = 60):
    """
    Rate limit dependency factory.
    Production deployments MUST replace this with Redis/distributed limiter.
    """
    def _limiter(request: Request):
        client_ip = request.client.host if request.client else "127.0.0.1"
        endpoint = request.url.path
        key = f"{client_ip}:{endpoint}"
        
        now = time.time()
        
        if key not in _rate_limit_store:
            _rate_limit_store[key] = []
            
        # Clean up old requests
        _rate_limit_store[key] = [t for t in _rate_limit_store[key] if now - t < window]
        
        if len(_rate_limit_store[key]) >= requests:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
            
        _rate_limit_store[key].append(now)
        
    return _limiter
