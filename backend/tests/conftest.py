import pytest
import os

# Set explicit provider configuration for local testing as per requirements
os.environ["VOICE_STT_PROVIDER"] = "mock"
os.environ["VOICE_TTS_PROVIDER"] = "mock"
os.environ["GEMINI_API_KEY"] = ""

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.core.deps import get_db
from app.main import app
from app.models.admin import Admin
from app.core.security import get_password_hash
from app.models.admin import Admin

# Use an in-memory SQLite database for testing instead of overriding the main DB to prevent corruption.
# For full compatibility testing with pgvector, a dedicated test PG database should be used in CI/CD.
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session")
def db_engine():
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db(db_engine):
    connection = db_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def test_admin(db):
    admin = Admin(
        email="test@admin.com",
        password_hash=get_password_hash("testpassword"),
        is_active=True
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin

@pytest.fixture(scope="function")
def admin_token_headers(client, test_admin):
    login_data = {
        "username": "test@admin.com",
        "password": "testpassword",
    }
    r = client.post("/api/v1/auth/login", data=login_data)
    tokens = r.json()
    a_token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {a_token}"}
    return headers
