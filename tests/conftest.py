"""Pytest configuration and fixtures."""
import os

# Set test API key before importing app modules (required for config validation)
os.environ["ADMIN_API_KEY"] = "SUPER_SECRET_ADMIN_KEY_2404"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest
from app.core.database import Base, get_db
from app.main import app

# Set test API key before importing app (required for config)
os.environ["ADMIN_API_KEY"] = "SUPER_SECRET_ADMIN_KEY_2404"

# Setup temporary database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override dependency
app.dependency_overrides[get_db] = override_get_db

# Create test client
client = TestClient(app=app)


# Setup: Create and drop tables for clean testing environment
@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Create tables before tests and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

