"""Application configuration and settings."""
import os
from dotenv import load_dotenv

# Load environment variables from .env (if present)
load_dotenv()

# Database configuration
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./permissions.db")

# Security configuration - REQUIRED, no default for security
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY")
if not ADMIN_API_KEY:
    raise ValueError(
        "ADMIN_API_KEY environment variable is required. "
        "Please set it in your .env file or environment variables."
    )

