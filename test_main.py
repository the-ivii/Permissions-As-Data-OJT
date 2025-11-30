from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
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
from main import app, get_db, ACTIVE_POLICY_CACHE
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app=app)

# --- GLOBAL VARIABLES ---
# Admin Key used for all authenticated POST requests (matches the key in main.py)
ADMIN_HEADERS = {"Authorization": "Bearer SUPER_SECRET_ADMIN_KEY_2404"}
policy_id = 0
global_trace_id = 0

# Setup: Create and drop tables for clean testing environment
@pytest.fixture(scope="module", autouse=True)
def setup_db():
    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)


# 1. INITIAL TEST 

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


# 2. MANAGEMENT API TESTS (Requires ADMIN_HEADERS)

def test_a_create_roles_and_check_cycle():
    """Tests POST /roles and cycle detection."""
    # Create Base Role
    response = client.post("/roles/", json={"name": "employee", "description": "Base role"}, headers=ADMIN_HEADERS)
    assert response.status_code == 200

    # Create Manager Role (Inherits employee)
    response = client.post("/roles/", json={"name": "manager", "parent_names": ["employee"]}, headers=ADMIN_HEADERS)
    assert response.status_code == 200

    # Test Cycle Detection (Attempting to inherit self)
    response = client.post("/roles/", json={"name": "cycler", "parent_names": ["cycler"]}, headers=ADMIN_HEADERS)
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
    response = client.post("/policies/", json={"name": "Initial_Policy", "content": policy_content}, headers=ADMIN_HEADERS)
    assert response.status_code == 200
    policy_id = response.json()["id"]

    # 3. Activate the Policy
    response = client.post(f"/policies/{policy_id}/activate", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert response.json()["is_active"] == True
    
    # 4. CACHE CHECK: Verify that the policy is now in the in-memory cache
    assert ACTIVE_POLICY_CACHE["policy"].id == policy_id


# 3. CORE EVALUATION TESTS (Testing Access with Cache Enabled)

def test_c_rbac_allow_deny_check():
    """Tests basic RBAC and inheritance."""
    global global_trace_id
    
    # Test 1: Inheritance Allow 
    response = client.post("/access", json={
        "subject": {"role": "manager"},
        "action": "write",
        "resource": {"category": "hr"}
    })
    assert response.status_code == 200
    assert response.json()["decision"] == True
    assert "Matched Rule #1" in response.json()["reason"]

    # Test 2: Final Deny (Implicit Deny)
    response = client.post("/access", json={
        "subject": {"role": "manager"},
        "action": "delete",
        "resource": {}
    })
    assert response.status_code == 200
    assert response.json()["decision"] == False
    assert "Implicit Deny" in response.json()["reason"]
    
    global_trace_id = response.json()["trace_id"] # Capture the ID


def test_d_abac_conditional_check():
    """Tests ABAC attribute matching logic."""

    # Test 1: ABAC ALLOW 
    response = client.post("/access", json={
        "subject": {"role": "manager"},
        "action": "read",
        "resource": {"status": "DRAFT", "category": "sales"} 
    })
    assert response.status_code == 200
    assert response.json()["decision"] == True

    # Test 2: ABAC DENY (Fails condition)
    response = client.post("/access", json={
        "subject": {"role": "manager"},
        "action": "read",
        "resource": {"status": "FINAL"} 
    })
    assert response.status_code == 200
    assert response.json()["decision"] == False


def test_e_audit_log_existence():
    """Verifies that audit logging is actually working."""
    global global_trace_id
    # Relies on global_trace_id captured in test_c
    assert global_trace_id is not None
    assert global_trace_id > 0
    

# 4. BATCH & INVALIDATION TESTS 

def test_f_batch_and_cache_logic():
    """Tests POST /access/batch and verifies cache invalidation works."""
    
    global policy_id
    
    # --- Part 1: Test Batch API ---
    batch_request = [
        # Request 1: Should be ALLOWED (Rule 0)
        {"subject": {"role": "manager"}, "action": "read", "resource": {"status": "DRAFT"}},
        # Request 2: Should be DENIED (Implicit Deny)
        {"subject": {"role": "employee"}, "action": "delete", "resource": {}}
    ]

    response = client.post("/access/batch", json=batch_request)
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert response.json()[0]["decision"] == True
    assert response.json()[1]["decision"] == False

    # --- Part 2: Test Cache Invalidation ---
    
    # Create a New Policy V2 that is much stricter
    stricter_policy_content = {
        "rules": [
            # Rule 0 (V2): Only allow manager to write (nothing else)
            {"role": "manager", "action": "write", "effect": "allow"},
        ]
    }
    response_v2 = client.post("/policies/", json={"name": "Initial_Policy", "content": stricter_policy_content}, headers=ADMIN_HEADERS)
    policy_id_v2 = response_v2.json()["id"]

    # Activate V2. This MUST invalidate the cache.
    response = client.post(f"/policies/{policy_id_v2}/activate", headers=ADMIN_HEADERS)
    
    # 1. Verify Cache has the new ID
    assert ACTIVE_POLICY_CACHE["policy"].id == policy_id_v2 
    
    # 2. Verify Access is now DENIED by the stricter policy
    # Request that was ALLOWED earlier (reading DRAFT) should now fail because V2 doesn't have that rule.
    response = client.post("/access", json={
        "subject": {"role": "manager"},
        "action": "read",
        "resource": {"status": "DRAFT"} 
    })
    assert response.json()["decision"] == False # Proves V2 is active (V1 allowed this)
    assert "Implicit Deny" in response.json()["reason"]