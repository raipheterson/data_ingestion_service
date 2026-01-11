"""Tests for telemetry endpoints."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import Node, NodeState
from app.services.node_service import NodeService
from app.services.telemetry_service import TelemetryService


def test_telemetry_endpoint_returns_data(client, db_session: Session):
    """Test that telemetry endpoint returns data for nodes with telemetry."""
    # Create a deployment
    create_response = client.post("/deployments", json={
        "name": "Telemetry Test",
        "target_node_count": 3
    })
    deployment_id = create_response.json()["id"]
    
    # Get nodes and transition one to RUNNING
    nodes_response = client.get(f"/deployments/{deployment_id}/nodes")
    node_data = nodes_response.json()["nodes"][0]
    
    node = db_session.query(Node).filter(Node.id == node_data["id"]).first()
    
    # Transition node to RUNNING
    node = NodeService.transition_node_state(
        db_session, node, NodeState.PROVISIONING, "Provisioning"
    )
    node = NodeService.transition_node_state(
        db_session, node, NodeState.CONFIGURING, "Configuring"
    )
    node = NodeService.transition_node_state(
        db_session, node, NodeState.RUNNING, "Running"
    )
    
    # Create some telemetry samples
    for i in range(5):
        TelemetryService.create_telemetry_sample(
            db=db_session,
            node_id=node.id,
            deployment_id=deployment_id,
            latency_ms=10.0 + i,
            throughput_gbps=9.5 - i * 0.1,
            error_rate=0.1 + i * 0.01,
            timestamp=datetime.utcnow() - timedelta(seconds=5-i)
        )
    
    # Get telemetry via API
    response = client.get(f"/deployments/{deployment_id}/telemetry")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "samples" in data
    assert "total" in data
    assert data["total"] == 5
    assert len(data["samples"]) == 5
    
    # Verify sample structure
    sample = data["samples"][0]
    assert "id" in sample
    assert "node_id" in sample
    assert "deployment_id" in sample
    assert "timestamp" in sample
    assert "latency_ms" in sample
    assert "throughput_gbps" in sample
    assert "error_rate" in sample
    
    assert sample["deployment_id"] == deployment_id
    assert sample["node_id"] == node.id
    assert isinstance(sample["latency_ms"], (int, float))
    assert isinstance(sample["throughput_gbps"], (int, float))
    assert isinstance(sample["error_rate"], (int, float))


def test_telemetry_endpoint_with_node_filter(client, db_session: Session):
    """Test telemetry endpoint with node_id filter."""
    # Create a deployment
    create_response = client.post("/deployments", json={
        "name": "Filter Test",
        "target_node_count": 2
    })
    deployment_id = create_response.json()["id"]
    
    # Get nodes
    nodes_response = client.get(f"/deployments/{deployment_id}/nodes")
    nodes = nodes_response.json()["nodes"]
    
    # Transition both nodes to RUNNING
    for node_data in nodes:
        node = db_session.query(Node).filter(Node.id == node_data["id"]).first()
        node = NodeService.transition_node_state(
            db_session, node, NodeState.RUNNING, "Running"
        )
    
    # Create telemetry for both nodes
    for i, node_data in enumerate(nodes):
        TelemetryService.create_telemetry_sample(
            db=db_session,
            node_id=node_data["id"],
            deployment_id=deployment_id,
            latency_ms=10.0 + i,
            throughput_gbps=9.0,
            error_rate=0.1,
        )
    
    # Get telemetry filtered by first node
    first_node_id = nodes[0]["id"]
    response = client.get(f"/deployments/{deployment_id}/telemetry?node_id={first_node_id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 1
    assert len(data["samples"]) == 1
    assert data["samples"][0]["node_id"] == first_node_id


def test_telemetry_endpoint_empty_when_no_data(client):
    """Test telemetry endpoint returns empty list when no telemetry exists."""
    # Create a deployment
    create_response = client.post("/deployments", json={
        "name": "Empty Test",
        "target_node_count": 2
    })
    deployment_id = create_response.json()["id"]
    
    # Get telemetry (should be empty)
    response = client.get(f"/deployments/{deployment_id}/telemetry")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "samples" in data
    assert "total" in data
    assert data["total"] == 0
    assert len(data["samples"]) == 0
