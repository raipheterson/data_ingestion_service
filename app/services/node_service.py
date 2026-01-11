"""Service layer for node lifecycle management.

This service handles node state transitions and lifecycle operations.
In production, this would integrate with:
- Hardware provisioning APIs
- Configuration management systems
- Network management protocols (SNMP, NETCONF)
- Health check agents running on nodes
"""

from datetime import datetime
from sqlalchemy.orm import Session
from app.models.models import Node, NodeState, Event


class NodeService:
    """Service for managing node lifecycle."""
    
    @staticmethod
    def get_nodes_by_deployment(db: Session, deployment_id: int) -> list[Node]:
        """Get all nodes for a deployment.
        
        Args:
            db: Database session
            deployment_id: Deployment ID
            
        Returns:
            List of Node objects
        """
        return db.query(Node).filter(Node.deployment_id == deployment_id).all()
    
    @staticmethod
    def transition_node_state(
        db: Session,
        node: Node,
        new_state: NodeState,
        message: str = None
    ) -> Node:
        """Transition a node to a new state.
        
        Implements the state machine:
        PENDING -> PROVISIONING -> CONFIGURING -> RUNNING or FAILED
        
        Args:
            db: Database session
            node: Node to transition
            new_state: Target state
            message: Optional message for event log
            
        Returns:
            Updated Node object
        """
        old_state = node.state
        node.state = new_state.value
        node.state_changed_at = datetime.utcnow()
        
        # Log state transition
        event = Event(
            deployment_id=node.deployment_id,
            node_id=node.id,
            event_type="STATE_CHANGE",
            message=message or f"Node {node.node_id} transitioned from {old_state} to {new_state.value}",
        )
        db.add(event)
        
        db.commit()
        db.refresh(node)
        return node
    
    @staticmethod
    def get_node_by_id(db: Session, node_id: int) -> Node | None:
        """Get a node by its database ID.
        
        Args:
            db: Database session
            node_id: Node database ID
            
        Returns:
            Node object or None if not found
        """
        return db.query(Node).filter(Node.id == node_id).first()
