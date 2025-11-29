from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException
import models, schemas


def get_role_by_name(db: Session, name: str):
    return db.query(models.Role).filter(models.Role.name == name).first()

def get_active_policy(db: Session):
    return db.query(models.Policy).filter(models.Policy.is_active == True).first()

def create_audit_log(db: Session, log: dict):
    db_log = models.AuditLog(**log)
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def create_role(db: Session, role: schemas.RoleCreate):
    # Safety Check: Role cannot be its own parent
    if role.name in role.parent_names:
        raise HTTPException(status_code=400, detail="A role cannot inherit from itself (Cycle detected).")

    db_role = models.Role(name=role.name, description=role.description)
    
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
        return db_role
    except Exception:
        db.rollback()
        raise HTTPException(status_code=400, detail="Role already exists or invalid data.")


def create_policy(db: Session, policy: schemas.PolicyCreate):
    # Auto-Versioning Logic: Find the highest version and increment
    last_policy = db.query(models.Policy)\
        .filter(models.Policy.name == policy.name)\
        .order_by(desc(models.Policy.version))\
        .first()
    
    new_version = 1
    if last_policy:
        new_version = last_policy.version + 1

    db_policy = models.Policy(
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
    # Deactivate all policies first
    db.query(models.Policy).filter(models.Policy.is_active == True).update({models.Policy.is_active: False}, synchronize_session=False)
    db.commit()
    
    # Activate the target policy
    target_policy = db.query(models.Policy).filter(models.Policy.id == policy_id).first()
    if target_policy:
        target_policy.is_active = True
        db.commit()
        db.refresh(target_policy)
    return target_policy