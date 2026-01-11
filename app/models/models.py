"""Database models for the Network Deployment & Telemetry Orchestrator.

This module defines the core data models:
- Deployment: Represents a network deployment with multiple nodes
- Node: Individual network device (switch/router) with lifecycle state machine
- TelemetrySample: Time-series metrics collected from nodes
- Event: Audit log of state transitions and errors

The Node model implements a state machine:
PENDING -> PROVISIONING -> CONFIGURING -> RUNNING or FAILED

In production, you would:
- Add indexes on frequently queried fields (deployment_id, node_id, timestamp)
- Implement soft deletes for audit trails
- Add foreign key constraints with cascade rules
- Consider partitioning TelemetrySample by time for large-scale deployments
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base


class NodeState(str, Enum):
    """Node lifecycle states following a state machine pattern."""
    PENDING = "PENDING"
    PROVISIONING = "PROVISIONING"
    CONFIGURING = "CONFIGURING"
    RUNNING = "RUNNING"
    FAILED = "FAILED"


class Deployment(Base):
    """Represents a network deployment with multiple nodes.
    
    In production, this would include:
    - Tenant/organization isolation
    - Deployment templates/blueprints
    - Rollback capabilities
    - Multi-region support
    """
    __tablename__ = "deployments"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    target_node_count = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    nodes = relationship("Node", back_populates="deployment", cascade="all, delete-orphan")
    events = relationship("Event", back_populates="deployment", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Deployment(id={self.id}, name='{self.name}', nodes={len(self.nodes)})>"


class Node(Base):
    """Represents a single network node (switch/router) in a deployment.
    
    Implements a state machine for lifecycle management:
    PENDING -> PROVISIONING -> CONFIGURING -> RUNNING or FAILED
    
    In production, this would include:
    - Hardware model/serial number
    - Physical location/rack information
    - Network topology relationships
    - Configuration versioning
    - Agent connection status
    """
    __tablename__ = "nodes"
    
    id = Column(Integer, primary_key=True, index=True)
    deployment_id = Column(Integer, ForeignKey("deployments.id"), nullable=False, index=True)
    node_id = Column(String(100), nullable=False, index=True)  # Unique identifier within deployment
    state = Column(String(20), default=NodeState.PENDING.value, nullable=False, index=True)
    hostname = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)  # Supports IPv6
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    state_changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    deployment = relationship("Deployment", back_populates="nodes")
    telemetry_samples = relationship("TelemetrySample", back_populates="node", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Node(id={self.id}, node_id='{self.node_id}', state='{self.state}')>"


class TelemetrySample(Base):
    """Time-series telemetry data collected from nodes.
    
    Stores metrics like latency, throughput, and error rates.
    In production, you would:
    - Use a time-series database (InfluxDB, TimescaleDB) for better performance
    - Implement data retention policies
    - Add compression for historical data
    - Partition by time ranges for efficient queries
    - Consider downsampling for long-term storage
    """
    __tablename__ = "telemetry_samples"
    
    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=False, index=True)
    deployment_id = Column(Integer, ForeignKey("deployments.id"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Telemetry metrics
    latency_ms = Column(Float, nullable=False)  # Network latency in milliseconds
    throughput_gbps = Column(Float, nullable=False)  # Throughput in gigabits per second
    error_rate = Column(Float, nullable=False)  # Error rate as a percentage (0-100)
    
    # Relationships
    node = relationship("Node", back_populates="telemetry_samples")
    
    def __repr__(self):
        return f"<TelemetrySample(node_id={self.node_id}, latency={self.latency_ms}ms, throughput={self.throughput_gbps}Gbps)>"


class Event(Base):
    """Audit log of events and state transitions.
    
    In production, this would include:
    - User/actor information
    - Event severity levels
    - Correlation IDs for distributed tracing
    - Integration with centralized logging (ELK, Splunk)
    """
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True)
    deployment_id = Column(Integer, ForeignKey("deployments.id"), nullable=True, index=True)
    node_id = Column(Integer, ForeignKey("nodes.id"), nullable=True)
    event_type = Column(String(50), nullable=False, index=True)  # e.g., "STATE_CHANGE", "ERROR", "TELEMETRY_COLLECTED"
    message = Column(Text, nullable=False)
    metadata = Column(Text, nullable=True)  # JSON string for additional context
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    deployment = relationship("Deployment", back_populates="events")
    
    def __repr__(self):
        return f"<Event(id={self.id}, type='{self.event_type}', deployment_id={self.deployment_id})>"
