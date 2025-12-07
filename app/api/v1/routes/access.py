"""Access/Authorization API endpoints."""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import schemas
from app.api.deps import get_db
from app.services.authorization import authorize_request

router = APIRouter()


@router.post("/access", response_model=schemas.AuthResponse)
def authorize(
    request: schemas.AuthRequest, 
    db: Session = Depends(get_db)
):
    """The master authorization endpoint."""
    return authorize_request(request, db)


@router.post("/access/batch", response_model=List[schemas.AuthResponse])
def authorize_batch(
    requests: List[schemas.AuthRequest], 
    db: Session = Depends(get_db)
):
    """Processes multiple authorization requests simultaneously."""
    results = []
    for req in requests:
        result = authorize_request(req, db)
        results.append(result)
    return results

