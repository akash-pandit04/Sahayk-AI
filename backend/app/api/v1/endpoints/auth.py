from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core import security
from app.core.deps import get_db, require_admin
from app.models.admin import Admin
from app.schemas.admin import AdminResponse
from app.schemas.token import Token
from app.schemas.response import SuccessResponse

router = APIRouter()

@router.post("/login", response_model=Token)
def login_access_token(
    db: Session = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    admin = db.query(Admin).filter(Admin.email == form_data.username).first()
    if not admin or not security.verify_password(form_data.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not admin.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # Update last login
    admin.last_login_at = datetime.utcnow()
    db.commit()

    return Token(
        access_token=security.create_access_token(subject=admin.id),
        token_type="bearer",
    )

@router.get("/me", response_model=SuccessResponse)
def get_current_admin_info(
    current_admin: Admin = Depends(require_admin),
) -> SuccessResponse:
    """
    Get current admin info.
    """
    admin_data = AdminResponse.model_validate(current_admin)
    return SuccessResponse(data=admin_data)

@router.post("/logout", response_model=SuccessResponse)
def logout(current_admin: Admin = Depends(require_admin)) -> SuccessResponse:
    """
    Logout the admin.
    Note: Since we are using stateless JWT tokens, actual token invalidation
    would require a Redis blacklist. For Phase 1, we rely on the client to discard the token
    and short expiry times.
    """
    return SuccessResponse(data={"message": "Successfully logged out. Please discard your token."})
