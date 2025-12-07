"""Integration tests for complete workflows."""
import pytest
from tests.conftest import client
from app.services.cache import ACTIVE_POLICY_CACHE

ADMIN_HEADERS = {"Authorization": "Bearer SUPER_SECRET_ADMIN_KEY_2404"}


class TestIntegrationWorkflows:
    """Test complete end-to-end workflows."""
    
    def test_complete_authorization_workflow(self):
        """Test complete workflow: create roles, policy, and authorize."""
        # Step 1: Create base role
        response = client.post("/roles/", json={
            "name": "base_user"
        }, headers=ADMIN_HEADERS)
        assert response.status_code == 200
        base_role_id = response.json()["id"]
        
        # Step 2: Create role with inheritance
        response = client.post("/roles/", json={
            "name": "admin_user",
            "parent_names": ["base_user"]
        }, headers=ADMIN_HEADERS)
        assert response.status_code == 200
        
        # Step 3: Create policy
        policy_content = {
            "rules": [
                {"role": "base_user", "action": "read", "effect": "allow"},
                {"role": "admin_user", "action": "write", "effect": "allow"}
            ]
        }
        response = client.post("/policies/", json={
            "name": "integration_test_policy",
            "content": policy_content
        }, headers=ADMIN_HEADERS)
        assert response.status_code == 200
        policy_id = response.json()["id"]
        
        # Step 4: Activate policy
        response = client.post(f"/policies/{policy_id}/activate", headers=ADMIN_HEADERS)
        assert response.status_code == 200
        assert response.json()["is_active"] == True
        
        # Step 5: Test authorization - base_user can read
        response = client.post("/access", json={
            "subject": {"role": "base_user"},
            "action": "read",
            "resource": {}
        })
        assert response.status_code == 200
        assert response.json()["decision"] == True
        
        # Step 6: Test authorization - admin_user inherits read from base_user
        response = client.post("/access", json={
            "subject": {"role": "admin_user"},
            "action": "read",
            "resource": {}
        })
        assert response.status_code == 200
        assert response.json()["decision"] == True
        
        # Step 7: Test authorization - admin_user can write
        response = client.post("/access", json={
            "subject": {"role": "admin_user"},
            "action": "write",
            "resource": {}
        })
        assert response.status_code == 200
        assert response.json()["decision"] == True
    
    def test_policy_versioning_workflow(self):
        """Test complete policy versioning workflow."""
        # Step 1: Create and activate v1
        policy_v1 = {
            "rules": [
                {"role": "employee", "action": "read", "effect": "allow"}
            ]
        }
        response = client.post("/policies/", json={
            "name": "versioned_policy",
            "content": policy_v1
        }, headers=ADMIN_HEADERS)
        v1_id = response.json()["id"]
        assert response.json()["version"] == 1
        
        response = client.post(f"/policies/{v1_id}/activate", headers=ADMIN_HEADERS)
        assert response.status_code == 200
        
        # Step 2: Create v2
        policy_v2 = {
            "rules": [
                {"role": "employee", "action": "read", "effect": "allow"},
                {"role": "employee", "action": "write", "effect": "allow"}
            ]
        }
        response = client.post("/policies/", json={
            "name": "versioned_policy",
            "content": policy_v2
        }, headers=ADMIN_HEADERS)
        v2_id = response.json()["id"]
        assert response.json()["version"] == 2
        
        # Step 3: Verify v1 is still active
        response = client.get("/policies/active", headers=ADMIN_HEADERS)
        assert response.json()["version"] == 1
        
        # Step 4: Activate v2
        response = client.post(f"/policies/{v2_id}/activate", headers=ADMIN_HEADERS)
        assert response.status_code == 200
        
        # Step 5: Verify v2 is now active
        response = client.get("/policies/active", headers=ADMIN_HEADERS)
        assert response.json()["version"] == 2
        assert response.json()["id"] == v2_id
        
        # Step 6: Rollback to v1
        response = client.post(f"/policies/{v1_id}/activate", headers=ADMIN_HEADERS)
        assert response.status_code == 200
        
        # Step 7: Verify v1 is active again
        response = client.get("/policies/active", headers=ADMIN_HEADERS)
        assert response.json()["version"] == 1
    
    def test_abac_workflow_with_multiple_conditions(self):
        """Test complete ABAC workflow with multiple attribute conditions."""
        # Step 1: Create role
        client.post("/roles/", json={"name": "manager"}, headers=ADMIN_HEADERS)
        
        # Step 2: Create policy with ABAC conditions
        policy_content = {
            "rules": [
                {
                    "role": "manager",
                    "action": "read",
                    "effect": "allow",
                    "resource_match": {"status": "DRAFT", "department": "sales"}
                }
            ]
        }
        response = client.post("/policies/", json={
            "name": "abac_test_policy",
            "content": policy_content
        }, headers=ADMIN_HEADERS)
        policy_id = response.json()["id"]
        
        # Step 3: Activate policy
        client.post(f"/policies/{policy_id}/activate", headers=ADMIN_HEADERS)
        
        # Step 4: Test - should ALLOW (all conditions match)
        response = client.post("/access", json={
            "subject": {"role": "manager"},
            "action": "read",
            "resource": {"status": "DRAFT", "department": "sales"}
        })
        assert response.status_code == 200
        assert response.json()["decision"] == True
        
        # Step 5: Test - should DENY (status doesn't match)
        response = client.post("/access", json={
            "subject": {"role": "manager"},
            "action": "read",
            "resource": {"status": "FINAL", "department": "sales"}
        })
        assert response.status_code == 200
        assert response.json()["decision"] == False
        
        # Step 6: Test - should DENY (department doesn't match)
        response = client.post("/access", json={
            "subject": {"role": "manager"},
            "action": "read",
            "resource": {"status": "DRAFT", "department": "hr"}
        })
        assert response.status_code == 200
        assert response.json()["decision"] == False
    
    def test_batch_authorization_workflow(self):
        """Test batch authorization with multiple requests."""
        # Setup: Create role and policy
        client.post("/roles/", json={"name": "batch_user"}, headers=ADMIN_HEADERS)
        policy_content = {
            "rules": [
                {"role": "batch_user", "action": "read", "effect": "allow"},
                {"role": "batch_user", "action": "write", "effect": "allow"}
            ]
        }
        response = client.post("/policies/", json={
            "name": "batch_test_policy",
            "content": policy_content
        }, headers=ADMIN_HEADERS)
        policy_id = response.json()["id"]
        client.post(f"/policies/{policy_id}/activate", headers=ADMIN_HEADERS)
        
        # Execute batch request
        batch_request = [
            {"subject": {"role": "batch_user"}, "action": "read", "resource": {}},
            {"subject": {"role": "batch_user"}, "action": "write", "resource": {}},
            {"subject": {"role": "batch_user"}, "action": "delete", "resource": {}},  # Should deny
            {"subject": {"role": "other_user"}, "action": "read", "resource": {}}  # Should deny
        ]
        
        response = client.post("/access/batch", json=batch_request)
        assert response.status_code == 200
        results = response.json()
        
        assert len(results) == 4
        assert results[0]["decision"] == True  # read allowed
        assert results[1]["decision"] == True  # write allowed
        assert results[2]["decision"] == False  # delete denied
        assert results[3]["decision"] == False  # other_user denied
    
    def test_audit_logging_workflow(self):
        """Test that audit logs are created for authorization decisions."""
        # Setup
        client.post("/roles/", json={"name": "audit_user"}, headers=ADMIN_HEADERS)
        policy_content = {
            "rules": [
                {"role": "audit_user", "action": "read", "effect": "allow"}
            ]
        }
        response = client.post("/policies/", json={
            "name": "audit_test_policy",
            "content": policy_content
        }, headers=ADMIN_HEADERS)
        policy_id = response.json()["id"]
        client.post(f"/policies/{policy_id}/activate", headers=ADMIN_HEADERS)
        
        # Make authorization request
        response = client.post("/access", json={
            "subject": {"role": "audit_user"},
            "action": "read",
            "resource": {}
        })
        assert response.status_code == 200
        trace_id = response.json().get("trace_id")
        
        # Verify trace_id exists (audit log was created)
        assert trace_id is not None
        assert trace_id > 0
        
        # Make another request and verify different trace_id
        response2 = client.post("/access", json={
            "subject": {"role": "audit_user"},
            "action": "read",
            "resource": {}
        })
        trace_id2 = response2.json().get("trace_id")
        assert trace_id2 != trace_id  # Should be different audit log entry
    
    def test_cache_invalidation_workflow(self):
        """Test that cache is properly invalidated when policy changes."""
        # Setup: Create and activate policy v1
        policy_v1 = {
            "rules": [
                {"role": "cache_user", "action": "read", "effect": "allow"}
            ]
        }
        response = client.post("/policies/", json={
            "name": "cache_test_policy",
            "content": policy_v1
        }, headers=ADMIN_HEADERS)
        v1_id = response.json()["id"]
        client.post(f"/policies/{v1_id}/activate", headers=ADMIN_HEADERS)
        
        # Verify cache has v1
        assert ACTIVE_POLICY_CACHE["policy"].id == v1_id
        
        # Create and activate v2
        policy_v2 = {
            "rules": [
                {"role": "cache_user", "action": "write", "effect": "allow"}
            ]
        }
        response = client.post("/policies/", json={
            "name": "cache_test_policy",
            "content": policy_v2
        }, headers=ADMIN_HEADERS)
        v2_id = response.json()["id"]
        client.post(f"/policies/{v2_id}/activate", headers=ADMIN_HEADERS)
        
        # Verify cache has been updated to v2
        assert ACTIVE_POLICY_CACHE["policy"].id == v2_id
        assert ACTIVE_POLICY_CACHE["policy"].version == 2

