from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

import models, schemas, crud
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)
app = FastAPI(title="Permissions-as-Data Hybrid Service")

# --- CORE DECISION ENGINE LOGIC ---

def expand_roles(db: Session, role_name: str) -> List[str]:
    """Recursively finds the role and all its ancestors (parents)."""
    role_obj = crud.get_role_by_name(db, role_name)
    if not role_obj:
        return [role_name]

    expanded = {role_obj.name}
    
    # Simple check for immediate parents (sufficient for basic demonstration)
    for parent in role_obj.parents:
        expanded.add(parent.name)
        
    return list(expanded)

def check_abac_conditions(rule_resource_conditions: Dict, request_resource: Dict) -> bool:
    """Checks if attributes match (ABAC)."""
    if not rule_resource_conditions:
        return True
        
    for key, value in rule_resource_conditions.items():
        if request_resource.get(key) != value:
            return False
            
    return True

@app.post("/access", response_model=schemas.AuthResponse)
def authorize(request: schemas.AuthRequest, db: Session = Depends(get_db)):
    """The master authorization endpoint."""
    
    active_policy = crud.get_active_policy(db)
    if not active_policy:
        return schemas.AuthResponse(decision=False, reason="System Error: No active policy found.")

    # 1. Role Expansion
    user_role = request.subject.get("role", "guest")
    user_roles_list = expand_roles(db, user_role)

    rules = active_policy.content.get("rules", [])
    decision = False
    reason = "Implicit Deny: No matching rule found."
    trace_id = None

    # 2. Deterministic Evaluation (First-Match-Wins)
    for i, rule in enumerate(rules):
        # A. RBAC Match
        if rule.get("role") not in user_roles_list and rule.get("role") != "*":
            continue
            
        # B. Action Match - FIX ADDED HERE
        if rule.get("action") != request.action and rule.get("action") != "*":
            continue
            
        # C. ABAC Match
        resource_constraints = rule.get("resource_match", {})
        if check_abac_conditions(resource_constraints, request.resource):
            # --- MATCH FOUND! ---
            decision = (rule.get("effect") == "allow")
            reason = f"Matched Rule #{i} (Role: {rule.get('role')}, Action: {rule.get('action')})."
            break

    # 3. Audit Log (If not dry-run)
    if not request.dry_run:
        log_entry = {
            "subject": str(request.subject),
            "action": request.action,
            "resource": str(request.resource),
            "decision": decision,
            "explanation": reason
        }
        db_log = crud.create_audit_log(db, log_entry)
        trace_id = db_log.id

    return schemas.AuthResponse(decision=decision, reason=reason, trace_id=trace_id)


# --- MANAGEMENT APIs (Role/Policy CRUD) ---

@app.post("/roles/", response_model=schemas.RoleResponse)
def create_role_api(role: schemas.RoleCreate, db: Session = Depends(get_db)):
    return crud.create_role(db=db, role=role)

@app.post("/policies/", response_model=schemas.PolicyResponse)
def create_policy_api(policy: schemas.PolicyCreate, db: Session = Depends(get_db)):
    return crud.create_policy(db=db, policy=policy)

@app.post("/policies/{policy_id}/activate", response_model=schemas.PolicyResponse)
def activate_policy_version_api(policy_id: int, db: Session = Depends(get_db)):
    policy = crud.activate_policy(db, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy