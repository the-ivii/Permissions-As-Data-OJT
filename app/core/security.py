"""Security and authentication utilities."""
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import ADMIN_API_KEY

security_scheme = HTTPBearer()


def verify_admin_key(credentials: HTTPAuthorizationCredentials = Security(security_scheme)):
    """Verifies the token provided in the Authorization header."""
    if credentials.credentials != ADMIN_API_KEY:
        raise HTTPException(
            status_code=403, 
            detail="Invalid or missing API Key for management access."
        )
    return True

