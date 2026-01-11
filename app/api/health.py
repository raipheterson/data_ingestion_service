"""Health check endpoint."""

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.base import get_db
from app.schemas.schemas import HealthResponse
from app.services.deployment_service import DeploymentService
from app.workers.lifecycle_worker import lifecycle_worker
from app.workers.telemetry_worker import telemetry_worker

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint for monitoring and load balancers.
    
    Returns the status of the service, database connection, and background workers.
    """
    # Check database connection
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"
    
    # Count active deployments
    active_deployments = len(DeploymentService.list_deployments(db, limit=1000))
    
    # Check worker status
    workers_active = lifecycle_worker.running and telemetry_worker.running
    
    overall_status = "healthy" if db_status == "healthy" and workers_active else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        database=db_status,
        active_deployments=active_deployments,
        active_workers=workers_active,
    )
