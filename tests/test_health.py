"""Tests for the health check endpoint."""

def test_health_endpoint(client):
    """Test that the health endpoint returns correct structure."""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert "timestamp" in data
    assert "database" in data
    assert "active_deployments" in data
    assert "active_workers" in data
    
    assert data["database"] in ["healthy", "unhealthy"]
    assert isinstance(data["active_deployments"], int)
    assert isinstance(data["active_workers"], bool)
