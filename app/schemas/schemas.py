"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- Role Schemas ---
class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None


class RoleCreate(RoleBase):
    parent_names: List[str] = Field(default_factory=list)


class RoleResponse(RoleBase):
    id: int
    
    class Config:
        from_attributes = True


# --- Policy Schemas ---
class PolicyBase(BaseModel):
    name: str
    content: Dict[str, Any]  # Flexible JSON rules


class PolicyCreate(PolicyBase):
    pass


class PolicyResponse(PolicyBase):
    id: int
    version: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# --- Authorization Schemas (The Engine I/O) ---
class AuthRequest(BaseModel):
    subject: Dict[str, Any]  # For ABAC attributes (role, dept, user_id)
    action: str
    resource: Dict[str, Any]  # For ABAC attributes (owner, type, status)
    dry_run: bool = False  # For dry-run feature


class AuthResponse(BaseModel):
    decision: bool
    reason: str
    trace_id: Optional[int] = None

