# test_main.py

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

# TEMPORARY TEST DATABASE SETUP (SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Override dependency get_db() from main.py
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Import models + app AFTER engine setup
import models
from main import app, get_db

app.dependency_overrides[get_db] = override_get_db

# FIXED TestClient (NO keyword argument)
client = TestClient(app)

# FIXTURE: Create & drop tables for testing
@pytest.fixture(scope="module", autouse=True)
def setup_db():
    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)

# TEST CASES
def test_initial_deny_no_policy():
    """
    If no active policy exists, access should be denied.
    """
    response = client.post("/access", json={
        "subject": {"role": "guest"},
        "action": "test",
        "resource": {}
    })

    body = response.json()

    assert body["decision"] is False
    assert "No active policy" in body["reason"]