"""Edge case and error handling tests."""
import pytest
from fastapi import status
from tests.conftest import client
from app.services.cache import ACTIVE_POLICY_CACHE

ADMIN_HEADERS = {"Authorization": "Bearer SUPER_SECRET_ADMIN_KEY_2404"}


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_invalid_json_payload(self):
        """Test handling of invalid JSON payload."""
        response = client.post(
            "/access",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields in request."""
        # Missing 'action' field
        response = client.post("/access", json={
            "subject": {"role": "employee"},
            "resource": {}
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_empty_subject(self):
        """Test authorization with empty subject."""
        response = client.post("/access", json={
            "subject": {},
            "action": "read",
            "resource": {}
        })
        assert response.status_code == 200
        # Should default to "guest" role and deny
        assert response.json()["decision"] == False
    
    def test_nonexistent_role(self):
        """Test authorization with non-existent role."""
        response = client.post("/access", json={
            "subject": {"role": "nonexistent_role_12345"},
            "action": "read",
            "resource": {}
        })
        assert response.status_code == 200
        # Should deny access for non-existent role
        assert response.json()["decision"] == False
    
    def test_invalid_policy_id(self):
        """Test activating non-existent policy."""
        response = client.post("/policies/99999/activate", headers=ADMIN_HEADERS)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()
    
    def test_create_role_with_nonexistent_parent(self):
        """Test creating role with non-existent parent."""
        response = client.post("/roles/", json={
            "name": "child_role",
            "parent_names": ["nonexistent_parent_123"]
        }, headers=ADMIN_HEADERS)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()
    
    def test_create_duplicate_role(self):
        """Test creating duplicate role."""
        # Create first role
        response1 = client.post("/roles/", json={
            "name": "unique_role_test"
        }, headers=ADMIN_HEADERS)
        assert response1.status_code == 200
        
        # Try to create duplicate
        response2 = client.post("/roles/", json={
            "name": "unique_role_test"
        }, headers=ADMIN_HEADERS)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_empty_batch_request(self):
        """Test batch request with empty list."""
        response = client.post("/access/batch", json=[])
        assert response.status_code == 200
        assert response.json() == []
    
    def test_batch_request_with_mixed_valid_invalid(self):
        """Test batch request with mix of valid and invalid requests."""
        batch_request = [
            {"subject": {"role": "employee"}, "action": "read", "resource": {}},  # Valid
            {"subject": {}, "action": "read", "resource": {}},  # Valid but empty subject
            {"subject": {"role": "employee"}}  # Invalid - missing action
        ]
        response = client.post("/access/batch", json=batch_request)
        # Should handle gracefully - first two succeed, third fails validation
        assert response.status_code in [200, 422]
    
    def test_dry_run_no_audit_log(self):
        """Test that dry-run requests don't create audit logs."""
        # Make a dry-run request
        response = client.post("/access", json={
            "subject": {"role": "employee"},
            "action": "read",
            "resource": {},
            "dry_run": True
        })
        assert response.status_code == 200
        # Should not have trace_id (no audit log created)
        assert response.json().get("trace_id") is None
    
    def test_very_long_role_name(self):
        """Test handling of very long role name."""
        long_name = "a" * 500  # Very long name
        response = client.post("/roles/", json={
            "name": long_name
        }, headers=ADMIN_HEADERS)
        # Should either succeed or fail with validation error, not crash
        assert response.status_code in [200, 400, 422]
    
    def test_special_characters_in_role_name(self):
        """Test handling of special characters in role name."""
        response = client.post("/roles/", json={
            "name": "role@#$%^&*()"
        }, headers=ADMIN_HEADERS)
        # Should handle gracefully
        assert response.status_code in [200, 400, 422]
    
    def test_empty_policy_content(self):
        """Test creating policy with empty content."""
        response = client.post("/policies/", json={
            "name": "empty_policy_test",
            "content": {}
        }, headers=ADMIN_HEADERS)
        # Should either succeed or validate
        assert response.status_code in [200, 400, 422]
    
    def test_policy_with_invalid_rules_structure(self):
        """Test creating policy with invalid rules structure."""
        response = client.post("/policies/", json={
            "name": "invalid_policy",
            "content": {
                "rules": "not a list"  # Should be a list
            }
        }, headers=ADMIN_HEADERS)
        # Should create policy but rules won't work correctly
        assert response.status_code == 200
    
    def test_unauthorized_access_to_management_endpoints(self):
        """Test accessing management endpoints without API key."""
        response = client.post("/roles/", json={"name": "test_role"})
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_invalid_api_key(self):
        """Test accessing management endpoints with invalid API key."""
        response = client.post(
            "/roles/",
            json={"name": "test_role"},
            headers={"Authorization": "Bearer invalid_key_12345"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
    
    def test_malformed_authorization_header(self):
        """Test with malformed authorization header."""
        response = client.post(
            "/roles/",
            json={"name": "test_role"},
            headers={"Authorization": "InvalidFormat key"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

