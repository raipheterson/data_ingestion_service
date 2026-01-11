"""Pydantic schemas for API request and response validation.

These schemas provide:
- Type validation for incoming requests
- Serialization for API responses
- Clear API contracts

In production, you would:
- Add more detailed validation rules
- Include pagination schemas
- Add filtering/sorting parameters
- Implement versioning (v1, v2)
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


# Deployment Schemas
class DeploymentCreate(BaseModel):
    """Schema for creating a new deployment."""
    name: str = Field(..., min_length=1, max_length=255, description="Deployment name")
    description: Optional[str] = Field(None, description="Optional deployment description")
    target_node_count: int = Field(..., ge=1, le=1000, description="Number of nodes to deploy")


class DeploymentResponse(BaseModel):
    """Schema for deployment response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    name: str
    description: Optional[str]
    target_node_count: int
    created_at: datetime
    updated_at: datetime


class DeploymentDetail(DeploymentResponse):
    """Extended deployment schema with node count."""
    current_node_count: int = Field(..., description="Current number of nodes in deployment")


# Node Schemas
class NodeResponse(BaseModel):
    """Schema for node response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    deployment_id: int
    node_id: str
    state: str
    hostname: Optional[str]
    ip_address: Optional[str]
    created_at: datetime
    updated_at: datetime
    state_changed_at: datetime


class NodeListResponse(BaseModel):
    """Schema for list of nodes."""
    nodes: List[NodeResponse]
    total: int


# Telemetry Schemas
class TelemetrySampleResponse(BaseModel):
    """Schema for telemetry sample response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    node_id: int
    deployment_id: int
    timestamp: datetime
    latency_ms: float
    throughput_gbps: float
    error_rate: float


class TelemetryQueryParams(BaseModel):
    """Query parameters for telemetry endpoint."""
    node_id: Optional[int] = Field(None, description="Filter by specific node ID")
    start_time: Optional[datetime] = Field(None, description="Start time for time range")
    end_time: Optional[datetime] = Field(None, description="End time for time range")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of samples to return")


class TelemetryListResponse(BaseModel):
    """Schema for telemetry list response."""
    samples: List[TelemetrySampleResponse]
    total: int


# Bottleneck Schemas
class BottleneckNode(BaseModel):
    """Schema for a node identified as a bottleneck."""
    node_id: int
    node_identifier: str
    deployment_id: int
    latency_ms: float
    throughput_gbps: float
    error_rate: float
    deviation_score: float = Field(..., description="Statistical deviation from baseline")
    timestamp: datetime


class BottleneckResponse(BaseModel):
    """Schema for bottleneck detection response."""
    deployment_id: int
    detected_at: datetime
    bottlenecks: List[BottleneckNode]
    total_bottlenecks: int
    analysis_window_minutes: int = Field(..., description="Time window used for analysis")


# Health Check Schema
class HealthResponse(BaseModel):
    """Schema for health check response."""
    status: str
    timestamp: datetime
    database: str = Field(..., description="Database connection status")
    active_deployments: int
    active_workers: bool
