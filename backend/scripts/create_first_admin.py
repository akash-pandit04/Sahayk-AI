import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.admin import Admin
from app.core.security import get_password_hash
from app.core.config import settings

def init_db(db: Session) -> None:
    admin = db.query(Admin).filter(Admin.email == settings.FIRST_ADMIN_EMAIL).first()
    if not admin:
        admin = Admin(
            email=settings.FIRST_ADMIN_EMAIL,
            password_hash=get_password_hash(settings.FIRST_ADMIN_PASSWORD),
            is_active=True,
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print(f"Created first admin user: {settings.FIRST_ADMIN_EMAIL}")
    else:
        print(f"Admin user already exists: {settings.FIRST_ADMIN_EMAIL}")

if __name__ == "__main__":
    print("Creating initial admin user...")
    db = SessionLocal()
    init_db(db)
