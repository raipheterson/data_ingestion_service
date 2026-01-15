"""API routes for deployment management."""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.base import get_db

logger = logging.getLogger(__name__)
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
    logger.info(f"Creating deployment: name='{deployment_data.name}', target_node_count={deployment_data.target_node_count}")
    deployment = DeploymentService.create_deployment(db, deployment_data)
    logger.info(f"Deployment created successfully: id={deployment.id}, name='{deployment.name}'")
    logger.debug(f"Deployment details: {deployment_data.model_dump()}")
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
    logger.info(f"Fetching deployment: id={deployment_id}")
    deployment = DeploymentService.get_deployment(db, deployment_id)
    if not deployment:
        logger.warning(f"Deployment not found: id={deployment_id}")
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    node_count = DeploymentService.get_deployment_node_count(db, deployment_id)
    logger.info(f"Deployment retrieved: id={deployment_id}, name='{deployment.name}', node_count={node_count}")
    
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
    logger.info(f"Fetching nodes for deployment: id={deployment_id}")
    # Verify deployment exists
    deployment = DeploymentService.get_deployment(db, deployment_id)
    if not deployment:
        logger.warning(f"Deployment not found when fetching nodes: id={deployment_id}")
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    nodes = NodeService.get_nodes_by_deployment(db, deployment_id)
    logger.info(f"Retrieved {len(nodes)} nodes for deployment: id={deployment_id}")
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
    logger.info(f"Fetching telemetry for deployment: id={deployment_id}, node_id={node_id}, limit={limit}")
    # Verify deployment exists
    deployment = DeploymentService.get_deployment(db, deployment_id)
    if not deployment:
        logger.warning(f"Deployment not found when fetching telemetry: id={deployment_id}")
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
    logger.info(f"Retrieved {len(samples)} telemetry samples for deployment: id={deployment_id}")
    
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
    logger.info(f"Analyzing bottlenecks for deployment: id={deployment_id}, window={analysis_window_minutes} minutes")
    # Verify deployment exists
    deployment = DeploymentService.get_deployment(db, deployment_id)
    if not deployment:
        logger.warning(f"Deployment not found when analyzing bottlenecks: id={deployment_id}")
        raise HTTPException(status_code=404, detail="Deployment not found")
    
    bottlenecks = AnalyticsService.detect_bottlenecks(
        db=db,
        deployment_id=deployment_id,
        analysis_window_minutes=analysis_window_minutes,
    )
    logger.info(f"Bottleneck analysis complete: deployment_id={deployment_id}, detected={bottlenecks.total_bottlenecks} bottlenecks")
    
    return bottlenecks
