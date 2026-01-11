"""API routes for deployment management."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.schemas.schemas import (
    DeploymentCreate,
    DeploymentResponse,
    DeploymentDetail,
    NodeResponse,
    NodeListResponse,
    TelemetryListResponse,
    TelemetrySampleResponse,
    BottleneckResponse,
    TelemetryQueryParams,
)
from app.services.deployment_service import DeploymentService
from app.services.node_service import NodeService
from app.services.telemetry_service import TelemetryService
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/deployments", tags=["deployments"])


@router.post("", response_model=DeploymentResponse, status_code=201)
def create_deployment(
    deployment_data: DeploymentCreate,
    db: Session = Depends(get_db)
):
    """Create a new network deployment with N nodes.
    
    The nodes will start in PENDING state and be processed by background workers.
    """
    deployment = DeploymentService.create_deployment(db, deployment_data)
    return deployment


@router.get("", response_model=List[DeploymentResponse])
def list_deployments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List all deployments."""
    deployments = DeploymentService.list_deployments(db, skip=skip, limit=limit)
    return deployments


@router.get("/{deployment_id}", response_model=DeploymentDetail)
def get_deployment(
    deployment_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific deployment by ID."""
    deployment = DeploymentService.get_deployment(db, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    node_count = DeploymentService.get_deployment_node_count(db, deployment_id)
    
    return {
        **DeploymentResponse.model_validate(deployment).model_dump(),
        "current_node_count": node_count,
    }


@router.get("/{deployment_id}/nodes", response_model=NodeListResponse)
def get_deployment_nodes(
    deployment_id: int,
    db: Session = Depends(get_db)
):
    """Get all nodes for a specific deployment."""
    # Verify deployment exists
    deployment = DeploymentService.get_deployment(db, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    nodes = NodeService.get_nodes_by_deployment(db, deployment_id)
    return NodeListResponse(
        nodes=[NodeResponse.model_validate(node) for node in nodes],
        total=len(nodes),
    )


@router.get("/{deployment_id}/telemetry", response_model=TelemetryListResponse)
def get_deployment_telemetry(
    deployment_id: int,
    node_id: int = Query(None, description="Filter by node ID"),
    start_time: str = Query(None, description="Start time (ISO format)"),
    end_time: str = Query(None, description="End time (ISO format)"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get telemetry data for a deployment.
    
    Supports optional filtering by node ID and time range.
    """
    # Verify deployment exists
    deployment = DeploymentService.get_deployment(db, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    # Parse datetime strings if provided
    from datetime import datetime
    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00")) if start_time else None
    end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00")) if end_time else None
    
    samples = TelemetryService.get_telemetry_for_deployment(
        db=db,
        deployment_id=deployment_id,
        node_id=node_id,
        start_time=start_dt,
        end_time=end_dt,
        limit=limit,
    )
    
    return TelemetryListResponse(
        samples=[TelemetrySampleResponse.model_validate(s) for s in samples],
        total=len(samples),
    )


@router.get("/{deployment_id}/bottlenecks", response_model=BottleneckResponse)
def get_deployment_bottlenecks(
    deployment_id: int,
    analysis_window_minutes: int = Query(10, ge=1, le=60, description="Analysis time window in minutes"),
    db: Session = Depends(get_db)
):
    """Detect bottlenecks in a deployment based on telemetry analysis.
    
    Uses statistical deviation analysis to identify nodes with abnormal
    latency, throughput, or error rates.
    """
    # Verify deployment exists
    deployment = DeploymentService.get_deployment(db, deployment_id)
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    bottlenecks = AnalyticsService.detect_bottlenecks(
        db=db,
        deployment_id=deployment_id,
        analysis_window_minutes=analysis_window_minutes,
    )
    
    return bottlenecks
