# Branch: feat/management-apis
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

# Setup temporary database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Overrides dependency from main.py
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Temporary imports and app setup
import models
# IMPORTANT: Need to import all parts of the app
from main import app, get_db, authorize, create_role_api, create_policy_api, activate_policy_version_api
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app=app)

# --- GLOBAL VARIABLES TO STORE IDs FOR SEQUENTIAL TESTING ---
policy_id = 0
global_trace_id = 0

# Setup: Create and drop tables for clean testing environment
@pytest.fixture(scope="module", autouse=True)
def setup_db():
    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)


# ----------------------------------------------------------------------
# 1. INITIAL TEST (From previous branch)
# ----------------------------------------------------------------------

def test_initial_deny_no_policy():
    """System should implicitly deny if no policy is active."""
    response = client.post("/access", json={
        "subject": {"role": "guest"},
        "action": "test",
        "resource": {}
    })
    assert response.status_code == 200
    assert response.json()["decision"] == False
    assert "No active policy" in response.json()["reason"]


# ----------------------------------------------------------------------
# 2. MANAGEMENT API TESTS (New for this branch)
# ----------------------------------------------------------------------

def test_a_create_roles_and_check_cycle():
    """Tests POST /roles and cycle detection."""
    # Create Base Role
    response = client.post("/roles/", json={"name": "employee", "description": "Base role"})
    assert response.status_code == 200
    assert response.json()["name"] == "employee"

    # Create Manager Role (Inherits employee)
    response = client.post("/roles/", json={"name": "manager", "parent_names": ["employee"]})
    assert response.status_code == 200
    assert response.json()["name"] == "manager"

    # Test Cycle Detection (Attempting to inherit self)
    response = client.post("/roles/", json={"name": "cycler", "parent_names": ["cycler"]})
    assert response.status_code == 400
    assert "Cycle detected" in response.json()["detail"]


def test_b_create_policy_and_activate():
    """Tests POST /policies and activation endpoint."""
    global policy_id
    
    # 1. Define Policy Rules
    policy_content = {
        "rules": [
            # Rule 0 (ABAC): Managers can read reports if status is DRAFT
            {"role": "manager", "action": "read", "effect": "allow", "resource_match": {"status": "DRAFT"}},
            # Rule 1 (RBAC): Employees can write reports
            {"role": "employee", "action": "write", "effect": "allow"},
            # Rule 2 (Deny Rule): Catch-all for financial data
            {"role": "*", "action": "*", "effect": "deny", "resource_match": {"category": "finance"}}
        ]
    }

    # 2. Create the Policy
    response = client.post("/policies/", json={"name": "Initial_Policy", "content": policy_content})
    assert response.status_code == 200
    assert response.json()["version"] == 1
    policy_id = response.json()["id"]

    # 3. Activate the Policy
    response = client.post(f"/policies/{policy_id}/activate")
    assert response.status_code == 200
    assert response.json()["is_active"] == True


# ----------------------------------------------------------------------
# 3. CORE EVALUATION TESTS
# ----------------------------------------------------------------------

def test_c_rbac_allow_deny_check():
    """Tests basic RBAC and inheritance."""
    global global_trace_id
    
    # Test 1: Inheritance Allow (Manager inherits Employee's rights) - EXPECTED ALLOW
    # ... (code for Test 1 is correct) ...

    # Test 2: Final Deny (Implicit Deny) - EXPECTED DENY
    response = client.post("/access", json={
        "subject": {"role": "manager"},
        "action": "delete",
        "resource": {}
    })
    # THIS LINE WAS FAILING: The error states the actual response was True (ALLOW)
    assert response.json()["decision"] == False
    assert "Implicit Deny" in response.json()["reason"]
    
    # CAPTURE TRACE ID HERE AFTER THE SUCCESSFUL DENY CHECK
    global_trace_id = response.json()["trace_id"]
    

def test_d_abac_conditional_check():
    """Tests ABAC attribute matching logic."""

    # Test 1: ABAC ALLOW (Matches Rule 0)
    response = client.post("/access", json={
        "subject": {"role": "manager"},
        "action": "read",
        "resource": {"status": "DRAFT", "category": "sales"} 
    })
    assert response.json()["decision"] == True
    assert "Matched Rule #0" in response.json()["reason"]

    # Test 2: ABAC DENY (Fails Rule 0 condition)
    response = client.post("/access", json={
        "subject": {"role": "manager"},
        "action": "read",
        "resource": {"status": "FINAL"} # Fails DRAFT check
    })
    assert response.json()["decision"] == False
    assert "Implicit Deny" in response.json()["reason"] # Fails Rule 0, falls to Implicit Deny

    # Test 3: Explicit Deny (Matches Rule 2)
    response = client.post("/access", json={
        "subject": {"role": "employee"},
        "action": "read",
        "resource": {"category": "finance"}
    })
    assert response.json()["decision"] == False
    assert "Matched Rule #2" in response.json()["reason"]


def test_e_audit_log_existence():
    """Verifies that audit logging is actually working."""
    global global_trace_id
    # We rely on the log ID captured in test_c_rbac_allow_deny_check
    assert global_trace_id is not None
    assert global_trace_id > 0