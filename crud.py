from sqlalchemy.orm import Session
from sqlalchemy import desc
from fastapi import HTTPException
import models, schemas

# This file will be populated in the next branch (feat/management-apis)
# We add helper imports here to avoid circular imports later.

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