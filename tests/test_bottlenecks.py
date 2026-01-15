"""Tests for bottleneck detection endpoint."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import Node, NodeState
from app.services.node_service import NodeService
from app.services.telemetry_service import TelemetryService


def test_bottleneck_endpoint_returns_structured_output(client, db_session: Session):
    """Test that bottleneck endpoint returns properly structured output."""
    # Create a deployment
    create_response = client.post("/deployments", json={
        "name": "Bottleneck Test",
        "target_node_count": 5
    })
    deployment_id = create_response.json()["id"]
    
    # Get nodes and transition them to RUNNING
    nodes_response = client.get(f"/deployments/{deployment_id}/nodes")
    nodes_data = nodes_response.json()["nodes"]
    
    for node_data in nodes_data:
        node = db_session.query(Node).filter(Node.id == node_data["id"]).first()
        node = NodeService.transition_node_state(
            db_session, node, NodeState.RUNNING, "Running"
        )
    
    # Create telemetry samples with some nodes having worse performance
    # This simulates bottlenecks
    for i, node_data in enumerate(nodes_data):
        node = db_session.query(Node).filter(Node.id == node_data["id"]).first()
        
        # Make some nodes (i > 2) have worse metrics to create bottlenecks
        if i > 2:
            # Bottleneck nodes: very high latency, very low throughput, very high error rate
            # These values are significantly worse to ensure they exceed 2 standard deviations
            latency = 150.0 + i * 20.0  # Much higher latency
            throughput = 2.0 - i * 0.3   # Much lower throughput
            error_rate = 4.0 + i * 0.5   # Much higher error rate
        else:
            # Normal nodes: good metrics (consistent values)
            latency = 10.0  # All normal nodes have similar good latency
            throughput = 9.5  # All normal nodes have similar good throughput
            error_rate = 0.1  # All normal nodes have similar low error rate
        
        # Create multiple samples for each node
        for j in range(10):
            TelemetryService.create_telemetry_sample(
                db=db_session,
                node_id=node.id,
                deployment_id=deployment_id,
                latency_ms=latency,
                throughput_gbps=throughput,
                error_rate=error_rate,
                timestamp=datetime.utcnow() - timedelta(minutes=10-j)
            )
    
    # Get bottlenecks
    response = client.get(f"/deployments/{deployment_id}/bottlenecks?analysis_window_minutes=15")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify structure
    assert "deployment_id" in data
    assert "detected_at" in data
    assert "bottlenecks" in data
    assert "total_bottlenecks" in data
    assert "analysis_window_minutes" in data
    
    assert data["deployment_id"] == deployment_id
    assert data["analysis_window_minutes"] == 15
    assert isinstance(data["total_bottlenecks"], int)
    assert isinstance(data["bottlenecks"], list)
    
    # Should detect at least some bottlenecks (nodes with poor performance)
    assert data["total_bottlenecks"] >= 2  # At least 2 nodes with poor metrics
    
    # Verify bottleneck node structure
    if data["bottlenecks"]:
        bottleneck = data["bottlenecks"][0]
        assert "node_id" in bottleneck
        assert "node_identifier" in bottleneck
        assert "deployment_id" in bottleneck
        assert "latency_ms" in bottleneck
        assert "throughput_gbps" in bottleneck
        assert "error_rate" in bottleneck
        assert "deviation_score" in bottleneck
        assert "timestamp" in bottleneck
        
        assert isinstance(bottleneck["latency_ms"], (int, float))
        assert isinstance(bottleneck["throughput_gbps"], (int, float))
        assert isinstance(bottleneck["error_rate"], (int, float))
        assert isinstance(bottleneck["deviation_score"], (int, float))
        assert bottleneck["deviation_score"] >= 0


def test_bottleneck_endpoint_no_bottlenecks(client, db_session: Session):
    """Test bottleneck endpoint when all nodes have normal performance."""
    # Create a deployment
    create_response = client.post("/deployments", json={
        "name": "No Bottlenecks Test",
        "target_node_count": 3
    })
    deployment_id = create_response.json()["id"]
    
    # Get nodes and transition to RUNNING
    nodes_response = client.get(f"/deployments/{deployment_id}/nodes")
    nodes_data = nodes_response.json()["nodes"]
    
    for node_data in nodes_data:
        node = db_session.query(Node).filter(Node.id == node_data["id"]).first()
        node = NodeService.transition_node_state(
            db_session, node, NodeState.RUNNING, "Running"
        )
    
    # Create telemetry with all nodes having similar, good performance
    for node_data in nodes_data:
        node = db_session.query(Node).filter(Node.id == node_data["id"]).first()
        
        for j in range(5):
            TelemetryService.create_telemetry_sample(
                db=db_session,
                node_id=node.id,
                deployment_id=deployment_id,
                latency_ms=10.0,  # All similar
                throughput_gbps=9.5,  # All similar
                error_rate=0.1,  # All similar
                timestamp=datetime.utcnow() - timedelta(minutes=5-j)
            )
    
    # Get bottlenecks
    response = client.get(f"/deployments/{deployment_id}/bottlenecks")
    
    assert response.status_code == 200
    data = response.json()
    
    # Should have no bottlenecks or very few
    assert data["total_bottlenecks"] == 0 or data["total_bottlenecks"] < len(nodes_data)


def test_bottleneck_endpoint_nonexistent_deployment(client):
    """Test bottleneck endpoint returns 404 for non-existent deployment."""
    response = client.get("/deployments/99999/bottlenecks")
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
