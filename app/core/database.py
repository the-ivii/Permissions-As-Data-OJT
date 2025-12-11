"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import SQLALCHEMY_DATABASE_URL

# Create database engine (SQLite needs special connect_args; others don’t)
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()


def get_db():
    """Generator function for FastAPI dependency injection.
    Creates a session, yields it, and closes it after usage to ensure proper cleanup.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

