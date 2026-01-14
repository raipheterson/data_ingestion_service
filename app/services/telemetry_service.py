"""Service layer for telemetry data management.

This service handles storing and querying telemetry samples.
In production, this would integrate with:
- Time-series databases (InfluxDB, TimescaleDB) for better performance
- Streaming data pipelines (Kafka, RabbitMQ)
- Real-time monitoring systems (Prometheus, Grafana)
- Data aggregation and downsampling services
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.models import TelemetrySample, Node


class TelemetryService:
    """Service for managing telemetry data."""
    
    @staticmethod
    def create_telemetry_sample(
        db: Session,
        node_id: int,
        deployment_id: int,
        latency_ms: float,
        throughput_gbps: float,
        error_rate: float,
        timestamp: Optional[datetime] = None
    ) -> TelemetrySample:
        """Create a new telemetry sample.
        
        Args:
            db: Database session
            node_id: Node database ID
            deployment_id: Deployment ID
            latency_ms: Latency in milliseconds
            throughput_gbps: Throughput in gigabits per second
            error_rate: Error rate percentage (0-100)
            timestamp: Optional timestamp (defaults to now)
            
        Returns:
            Created TelemetrySample object
        """
        sample = TelemetrySample(
            node_id=node_id,
            deployment_id=deployment_id,
            latency_ms=latency_ms,
            throughput_gbps=throughput_gbps,
            error_rate=error_rate,
            timestamp=timestamp or datetime.utcnow(),
        )
        db.add(sample)
        db.commit()
        db.refresh(sample)
        return sample
    
    @staticmethod
    def get_telemetry_for_deployment(
        db: Session,
        deployment_id: int,
        node_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> list[TelemetrySample]:
        """Get telemetry samples for a deployment with optional filters.
        
        Args:
            db: Database session
            deployment_id: Deployment ID
            node_id: Optional node ID filter
            start_time: Optional start time filter
            end_time: Optional end time filter
            limit: Maximum number of samples to return
            
        Returns:
            List of TelemetrySample objects, ordered by timestamp descending
        """
        query = db.query(TelemetrySample).filter(
            TelemetrySample.deployment_id == deployment_id
        )
        
        if node_id:
            query = query.filter(TelemetrySample.node_id == node_id)
        
        if start_time:
            query = query.filter(TelemetrySample.timestamp >= start_time)
        
        if end_time:
            query = query.filter(TelemetrySample.timestamp <= end_time)
        
        return query.order_by(desc(TelemetrySample.timestamp)).limit(limit).all()
    
    @staticmethod
    def get_recent_telemetry_for_node(
        db: Session,
        node_id: int,
        minutes: int = 5
    ) -> list[TelemetrySample]:
        """Get recent telemetry samples for a specific node.
        
        Args:
            db: Database session
            node_id: Node database ID
            minutes: Number of minutes to look back
            
        Returns:
            List of TelemetrySample objects
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
        return db.query(TelemetrySample).filter(
            TelemetrySample.node_id == node_id,
            TelemetrySample.timestamp >= cutoff_time
        ).order_by(TelemetrySample.timestamp).all()
