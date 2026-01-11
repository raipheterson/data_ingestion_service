"""Background worker for generating telemetry data.

This worker simulates telemetry collection from running nodes.
In production, this would:
- Poll agents running on actual hardware
- Receive push notifications from nodes
- Integrate with SNMP, NETCONF, or gRPC collectors
- Handle network partitions and retries
- Support multiple telemetry collection frequencies
"""

import asyncio
import math
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.base import SessionLocal
from app.models.models import Node, NodeState
from app.services.telemetry_service import TelemetryService


class TelemetryWorker:
    """Worker that generates telemetry data for running nodes."""
    
    def __init__(self, collection_interval_seconds: int = 5):
        """Initialize telemetry worker.
        
        Args:
            collection_interval_seconds: How often to collect telemetry (default: 5 seconds)
        """
        self.running = False
        self.task = None
        self.collection_interval = collection_interval_seconds
    
    async def start(self):
        """Start the telemetry worker."""
        self.running = True
        self.task = asyncio.create_task(self._run())
    
    async def stop(self):
        """Stop the telemetry worker."""
        self.running = False
        if self.task:
            await self.task
    
    async def _run(self):
        """Main worker loop that generates telemetry."""
        while self.running:
            try:
                await self._collect_telemetry()
                await asyncio.sleep(self.collection_interval)
            except Exception as e:
                # In production, log to centralized logging system
                print(f"Telemetry worker error: {e}")
                await asyncio.sleep(5)
    
    async def _collect_telemetry(self):
        """Collect telemetry for all running nodes."""
        db: Session = SessionLocal()
        try:
            # Get all nodes in RUNNING state
            running_nodes = db.query(Node).filter(
                Node.state == NodeState.RUNNING.value
            ).all()
            
            for node in running_nodes:
                # Generate deterministic but realistic telemetry
                # In production: Query actual hardware metrics
                telemetry = self._generate_telemetry(node)
                
                TelemetryService.create_telemetry_sample(
                    db=db,
                    node_id=node.id,
                    deployment_id=node.deployment_id,
                    latency_ms=telemetry["latency_ms"],
                    throughput_gbps=telemetry["throughput_gbps"],
                    error_rate=telemetry["error_rate"],
                )
        finally:
            db.close()
    
    def _generate_telemetry(self, node: Node) -> dict:
        """Generate deterministic telemetry metrics for a node.
        
        Uses node ID and time to create realistic but reproducible metrics.
        Some nodes will have higher latency/lower throughput to simulate bottlenecks.
        
        Args:
            node: Node to generate telemetry for
            
        Returns:
            Dictionary with latency_ms, throughput_gbps, and error_rate
        """
        # Use node ID and current time to create deterministic patterns
        time_factor = datetime.utcnow().timestamp() / 100  # Slow time progression
        node_factor = node.id % 10
        
        # Base metrics with some variation
        # Some nodes (node_factor > 7) will have worse performance
        if node_factor > 7:
            # Simulate bottleneck nodes
            base_latency = 50.0 + (node_factor - 7) * 20.0
            base_throughput = 8.0 - (node_factor - 7) * 1.5
            base_error_rate = 0.5 + (node_factor - 7) * 0.3
        else:
            # Normal nodes
            base_latency = 10.0 + node_factor * 2.0
            base_throughput = 9.5 - node_factor * 0.1
            base_error_rate = 0.1 + node_factor * 0.02
        
        # Add time-based variation (sine wave for realistic fluctuations)
        time_variation = math.sin(time_factor + node.id) * 0.3
        
        latency_ms = base_latency * (1.0 + time_variation * 0.2)
        throughput_gbps = base_throughput * (1.0 + time_variation * 0.1)
        error_rate = max(0.0, base_error_rate + time_variation * 0.1)
        
        # Ensure reasonable bounds
        latency_ms = max(1.0, min(200.0, latency_ms))
        throughput_gbps = max(1.0, min(10.0, throughput_gbps))
        error_rate = max(0.0, min(5.0, error_rate))
        
        return {
            "latency_ms": round(latency_ms, 2),
            "throughput_gbps": round(throughput_gbps, 2),
            "error_rate": round(error_rate, 2),
        }


# Global worker instance
telemetry_worker = TelemetryWorker(collection_interval_seconds=5)
