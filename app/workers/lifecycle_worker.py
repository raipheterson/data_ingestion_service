"""Background worker for managing node lifecycle state transitions.

This worker simulates the provisioning and configuration process for nodes.
In production, this would:
- Make actual API calls to cloud providers or hardware controllers
- Poll for provisioning status
- Handle retries and error recovery
- Integrate with configuration management systems
- Support cancellation and rollback
"""

import asyncio
import random
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.models.models import Node, NodeState, Event
from app.services.node_service import NodeService


class LifecycleWorker:
    """Worker that manages node lifecycle state transitions."""
    
    def __init__(self):
        self.running = False
        self.task = None
    
    async def start(self):
        """Start the lifecycle worker."""
        self.running = True
        self.task = asyncio.create_task(self._run())
    
    async def stop(self):
        """Stop the lifecycle worker."""
        self.running = False
        if self.task:
            await self.task
    
    async def _run(self):
        """Main worker loop that processes node state transitions."""
        while self.running:
            try:
                await self._process_pending_nodes()
                await asyncio.sleep(2)  # Check every 2 seconds
            except Exception as e:
                # In production, log to centralized logging system
                print(f"Lifecycle worker error: {e}")
                await asyncio.sleep(5)
    
    async def _process_pending_nodes(self):
        """Process nodes that need state transitions."""
        db: Session = SessionLocal()
        try:
            # Get nodes that are not in terminal states
            pending_nodes = db.query(Node).filter(
                Node.state.in_([NodeState.PENDING.value, NodeState.PROVISIONING.value, NodeState.CONFIGURING.value])
            ).all()
            
            for node in pending_nodes:
                await self._transition_node(db, node)
        finally:
            db.close()
    
    async def _transition_node(self, db: Session, node: Node):
        """Transition a node through its lifecycle states.
        
        Simulates deterministic but realistic timing:
        - PENDING -> PROVISIONING: Immediate
        - PROVISIONING -> CONFIGURING: 3-8 seconds
        - CONFIGURING -> RUNNING: 5-12 seconds (or FAILED with 5% probability)
        """
        current_state = NodeState(node.state)
        
        if current_state == NodeState.PENDING:
            # Start provisioning immediately
            # In production: Call cloud API to provision hardware
            NodeService.transition_node_state(
                db, node, NodeState.PROVISIONING,
                f"Starting hardware provisioning for {node.node_id}"
            )
            # Simulate IP assignment
            node.ip_address = f"10.0.{node.deployment_id}.{node.id % 255}"
            db.commit()
        
        elif current_state == NodeState.PROVISIONING:
            # Check if provisioning is complete
            # Use deterministic timing based on node ID for reproducibility
            state_age = (datetime.utcnow() - node.state_changed_at).total_seconds()
            required_time = 3 + (node.id % 5)  # 3-8 seconds based on node ID
            
            if state_age >= required_time:
                # In production: Verify provisioning status via API
                NodeService.transition_node_state(
                    db, node, NodeState.CONFIGURING,
                    f"Hardware provisioned, starting configuration for {node.node_id}"
                )
        
        elif current_state == NodeState.CONFIGURING:
            # Check if configuration is complete
            state_age = (datetime.utcnow() - node.state_changed_at).total_seconds()
            required_time = 5 + (node.id % 7)  # 5-12 seconds based on node ID
            
            if state_age >= required_time:
                # 5% chance of failure (deterministic based on node ID)
                # In production: Verify configuration via health checks
                if (node.id + node.deployment_id) % 20 == 0:  # ~5% failure rate
                    NodeService.transition_node_state(
                        db, node, NodeState.FAILED,
                        f"Configuration failed for {node.node_id}"
                    )
                else:
                    NodeService.transition_node_state(
                        db, node, NodeState.RUNNING,
                        f"Node {node.node_id} is now running"
                    )


# Global worker instance
lifecycle_worker = LifecycleWorker()
