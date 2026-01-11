"""Tests for deployment endpoints."""

import time
from app.models.models import NodeState


def test_create_deployment(client):
    """Test creating a new deployment."""
    deployment_data = {
        "name": "Test Deployment",
        "description": "A test deployment",
        "target_node_count": 5
    }
    
    response = client.post("/deployments", json=deployment_data)
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["name"] == deployment_data["name"]
    assert data["description"] == deployment_data["description"]
    assert data["target_node_count"] == deployment_data["target_node_count"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_get_deployment(client):
    """Test retrieving a deployment by ID."""
    # Create a deployment first
    deployment_data = {
        "name": "Test Deployment",
        "target_node_count": 3
    }
    create_response = client.post("/deployments", json=deployment_data)
    deployment_id = create_response.json()["id"]
    
    # Get the deployment
    response = client.get(f"/deployments/{deployment_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == deployment_id
    assert data["name"] == deployment_data["name"]
    assert data["target_node_count"] == 3
    assert "current_node_count" in data
    assert data["current_node_count"] == 3


def test_get_nonexistent_deployment(client):
    """Test retrieving a non-existent deployment returns 404."""
    response = client.get("/deployments/99999")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_list_deployments(client):
    """Test listing all deployments."""
    # Create multiple deployments
    for i in range(3):
        client.post("/deployments", json={
            "name": f"Deployment {i+1}",
            "target_node_count": 2
        })
    
    response = client.get("/deployments")
    
    assert response.status_code == 200
    data = response.json()
    
    assert len(data) == 3
    assert all("id" in d and "name" in d for d in data)


def test_get_deployment_nodes(client):
    """Test retrieving nodes for a deployment."""
    # Create a deployment
    create_response = client.post("/deployments", json={
        "name": "Test Deployment",
        "target_node_count": 4
    })
    deployment_id = create_response.json()["id"]
    
    # Get nodes
    response = client.get(f"/deployments/{deployment_id}/nodes")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "nodes" in data
    assert "total" in data
    assert data["total"] == 4
    assert len(data["nodes"]) == 4
    
    # Verify node structure
    node = data["nodes"][0]
    assert "id" in node
    assert "node_id" in node
    assert "state" in node
    assert "deployment_id" in node
    assert node["state"] == NodeState.PENDING.value
    assert node["deployment_id"] == deployment_id
