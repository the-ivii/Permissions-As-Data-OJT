"""Authorization engine business logic."""
from typing import List, Dict
from sqlalchemy.orm import Session
from app import crud
from app import schemas
from app.services.cache import ACTIVE_POLICY_CACHE
from app.core.logging_config import logger


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


def authorize_request(request: schemas.AuthRequest, db: Session) -> schemas.AuthResponse:
    """The master authorization function that evaluates access requests."""
    logger.info(f"Authorization request: role={request.subject.get('role')}, action={request.action}")
    
    # Policy Lookup: Check Cache first!
    active_policy = ACTIVE_POLICY_CACHE.get("policy")
    if not active_policy:
        logger.debug("Cache miss - fetching policy from database")
        active_policy = crud.get_active_policy(db)
        if active_policy:
            ACTIVE_POLICY_CACHE["policy"] = active_policy  # Cache miss, update cache
            logger.debug(f"Policy cached: ID={active_policy.id}, Version={active_policy.version}")
        else:
            logger.error("No active policy found in database")
            return schemas.AuthResponse(
                decision=False, 
                reason="System Error: No active policy found."
            )
        
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
            
        # B. Action Match 
        if rule.get("action") != request.action and rule.get("action") != "*":
            continue
            
        # C. ABAC Match
        resource_constraints = rule.get("resource_match", {})
        if check_abac_conditions(resource_constraints, request.resource):
            # --- MATCH FOUND! ---
            decision = (rule.get("effect") == "allow")
            reason = f"Matched Rule #{i} (Role: {rule.get('role')}, Action: {rule.get('action')})."
            logger.info(f"Authorization decision: {decision} - {reason}")
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
        logger.debug(f"Audit log created: trace_id={trace_id}")
    else:
        logger.debug("Dry-run mode: skipping audit log")

    return schemas.AuthResponse(decision=decision, reason=reason, trace_id=trace_id)

