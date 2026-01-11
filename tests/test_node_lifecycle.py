"""Tests for node lifecycle state transitions.

These tests verify that nodes progress through the state machine:
PENDING -> PROVISIONING -> CONFIGURING -> RUNNING (or FAILED)
"""

import time
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.models import Node, NodeState
from app.services.node_service import NodeService


def test_node_lifecycle_transitions(client, db_session: Session):
    """Test that nodes can transition through lifecycle states."""
    # Create a deployment
    create_response = client.post("/deployments", json={
        "name": "Lifecycle Test",
        "target_node_count": 2
    })
    deployment_id = create_response.json()["id"]
    
    # Get nodes
    nodes_response = client.get(f"/deployments/{deployment_id}/nodes")
    nodes = nodes_response.json()["nodes"]
    
    assert len(nodes) == 2
    node_data = nodes[0]
    
    # Initially, nodes should be in PENDING state
    assert node_data["state"] == NodeState.PENDING.value
    
    # Get the node from database
    node = db_session.query(Node).filter(Node.id == node_data["id"]).first()
    assert node.state == NodeState.PENDING.value
    
    # Manually transition through states (simulating worker behavior)
    # PENDING -> PROVISIONING
    node = NodeService.transition_node_state(
        db_session, node, NodeState.PROVISIONING, "Starting provisioning"
    )
    assert node.state == NodeState.PROVISIONING.value
    
    # Update state_changed_at to simulate time passing
    node.state_changed_at = datetime.utcnow() - timedelta(seconds=5)
    db_session.commit()
    
    # PROVISIONING -> CONFIGURING
    node = NodeService.transition_node_state(
        db_session, node, NodeState.CONFIGURING, "Starting configuration"
    )
    assert node.state == NodeState.CONFIGURING.value
    
    # Update state_changed_at
    node.state_changed_at = datetime.utcnow() - timedelta(seconds=6)
    db_session.commit()
    
    # CONFIGURING -> RUNNING
    node = NodeService.transition_node_state(
        db_session, node, NodeState.RUNNING, "Node is running"
    )
    assert node.state == NodeState.RUNNING.value
    
    # Verify final state via API
    nodes_response = client.get(f"/deployments/{deployment_id}/nodes")
    updated_node = next(n for n in nodes_response.json()["nodes"] if n["id"] == node_data["id"])
    assert updated_node["state"] == NodeState.RUNNING.value


def test_node_failure_state(client, db_session: Session):
    """Test that nodes can transition to FAILED state."""
    # Create a deployment
    create_response = client.post("/deployments", json={
        "name": "Failure Test",
        "target_node_count": 1
    })
    deployment_id = create_response.json()["id"]
    
    # Get node
    nodes_response = client.get(f"/deployments/{deployment_id}/nodes")
    node_data = nodes_response.json()["nodes"][0]
    
    node = db_session.query(Node).filter(Node.id == node_data["id"]).first()
    
    # Transition to CONFIGURING first
    node = NodeService.transition_node_state(
        db_session, node, NodeState.CONFIGURING, "Configuring"
    )
    
    # Then transition to FAILED
    node = NodeService.transition_node_state(
        db_session, node, NodeState.FAILED, "Configuration failed"
    )
    
    assert node.state == NodeState.FAILED.value
    
    # Verify via API
    nodes_response = client.get(f"/deployments/{deployment_id}/nodes")
    updated_node = nodes_response.json()["nodes"][0]
    assert updated_node["state"] == NodeState.FAILED.value
