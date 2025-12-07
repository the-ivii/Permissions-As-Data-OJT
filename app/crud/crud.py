"""Database CRUD operations."""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException
from app.models import Role, Policy, AuditLog
from app import schemas
from app.services.cache import ACTIVE_POLICY_CACHE
from app.core.logging_config import logger


def get_role_by_name(db: Session, name: str):
    """Get a role by its name."""
    return db.query(Role).filter(Role.name == name).first()


def get_active_policy(db: Session):
    """Get the currently active policy."""
    return db.query(Policy).filter(Policy.is_active == True).first()


def create_audit_log(db: Session, log: dict):
    """Create an audit log entry."""
    db_log = AuditLog(**log)
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log


def create_role(db: Session, role: schemas.RoleCreate):
    """Create a new role with optional parent roles."""
    logger.info(f"Creating role: {role.name} with parents: {role.parent_names}")
    # Safety Check: Role cannot be its own parent
    if role.name in role.parent_names:
        logger.warning(f"Cycle detection: role {role.name} cannot inherit from itself")
        raise HTTPException(status_code=400, detail="A role cannot inherit from itself (Cycle detected).")

    db_role = Role(name=role.name, description=role.description)
    
    # Handle Inheritance
    if role.parent_names:
        for parent_name in role.parent_names:
            parent_role = get_role_by_name(db, parent_name)
            if parent_role:
                db_role.parents.append(parent_role)
            else:
                raise HTTPException(status_code=404, detail=f"Parent role '{parent_name}' not found.")
    
    try:
        db.add(db_role)
        db.commit()
        db.refresh(db_role)
        logger.info(f"Role created successfully: {db_role.name} (ID: {db_role.id})")
        return db_role
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create role {role.name}: {e}")
        raise HTTPException(status_code=400, detail="Role already exists or invalid data.")


def create_policy(db: Session, policy: schemas.PolicyCreate):
    """Create a new policy version with auto-versioning."""
    # Auto-Versioning Logic: Find the highest version and increment
    last_policy = db.query(Policy)\
        .filter(Policy.name == policy.name)\
        .order_by(desc(Policy.version))\
        .first()
    
    new_version = 1
    if last_policy:
        new_version = last_policy.version + 1

    db_policy = Policy(
        name=policy.name,
        content=policy.content,
        version=new_version,
        is_active=False
    )
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy


def activate_policy(db: Session, policy_id: int):
    """Activate a policy version and deactivate all others."""
    logger.info(f"Activating policy ID: {policy_id}")
    # Deactivate all policies first
    db.query(Policy).filter(Policy.is_active == True).update(
        {Policy.is_active: False}, 
        synchronize_session=False
    )
    db.commit()
    
    # Activate the target policy
    target_policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if target_policy:
        target_policy.is_active = True
        db.commit()
        db.refresh(target_policy)
        ACTIVE_POLICY_CACHE["policy"] = target_policy
        logger.info(f"Policy activated: {target_policy.name} v{target_policy.version} (ID: {target_policy.id})")
    else:
        logger.warning(f"Policy not found: ID {policy_id}")
    return target_policy


def get_policy_by_id(db: Session, policy_id: int):
    """Retrieve a specific policy version by its ID."""
    return db.query(Policy).filter(Policy.id == policy_id).first()


def get_all_policies(db: Session, skip: int = 0, limit: int = 100):
    """Retrieve all policy versions, ordered by version number."""
    return db.query(Policy).order_by(Policy.version.desc()).offset(skip).limit(limit).all()

