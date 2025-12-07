"""Management API endpoints (Role/Policy CRUD)."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import schemas
from app import crud
from app.api.deps import get_db
from app.core.security import verify_admin_key
from app.services.cache import ACTIVE_POLICY_CACHE

router = APIRouter()


@router.post("/roles/", response_model=schemas.RoleResponse)
def create_role_api(
    role: schemas.RoleCreate, 
    db: Session = Depends(get_db), 
    verified: bool = Depends(verify_admin_key)
):
    """Create a new role. Requires Admin API Key."""
    return crud.create_role(db=db, role=role)


@router.post("/policies/", response_model=schemas.PolicyResponse)
def create_policy_api(
    policy: schemas.PolicyCreate, 
    db: Session = Depends(get_db), 
    verified: bool = Depends(verify_admin_key)
):
    """Create a new policy version. Requires Admin API Key."""
    return crud.create_policy(db=db, policy=policy)


@router.post("/policies/{policy_id}/activate", response_model=schemas.PolicyResponse)
def activate_policy_version_api(
    policy_id: int, 
    db: Session = Depends(get_db), 
    verified: bool = Depends(verify_admin_key)
):
    """Activate a policy version. Requires Admin API Key."""
    policy = crud.activate_policy(db, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.get("/policies/", response_model=List[schemas.PolicyResponse])
def list_policies_api(
    db: Session = Depends(get_db), 
    verified: bool = Depends(verify_admin_key)
):
    """Retrieves a list of all policy versions in the database. Requires Admin API Key."""
    return crud.get_all_policies(db)


@router.get("/policies/active", response_model=schemas.PolicyResponse)
def get_active_policy_api(
    db: Session = Depends(get_db), 
    verified: bool = Depends(verify_admin_key)
):
    """Retrieves the single currently active policy. Requires Admin API Key."""
    # This leverages the existing cache lookup logic for efficiency
    active_policy = ACTIVE_POLICY_CACHE.get("policy")
    if not active_policy:
        active_policy = crud.get_active_policy(db)
    
    if not active_policy:
        raise HTTPException(status_code=404, detail="No policy is currently active.")
    return active_policy

