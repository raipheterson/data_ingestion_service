"""Service layer for bottleneck detection and analytics.

This service implements statistical analysis to detect network bottlenecks
based on latency and throughput deviations from baseline metrics.

In production, this would integrate with:
- Machine learning models for anomaly detection
- Real-time alerting systems (PagerDuty, OpsGenie)
- Advanced analytics platforms (Spark, Flink)
- Historical trend analysis
"""

from datetime import datetime, timedelta
from typing import List
from statistics import mean, stdev
from sqlalchemy.orm import Session
from app.models.models import TelemetrySample, Node
from app.schemas.schemas import BottleneckNode, BottleneckResponse
from app.services.telemetry_service import TelemetryService


class AnalyticsService:
    """Service for analytics and bottleneck detection."""
    
    @staticmethod
    def detect_bottlenecks(
        db: Session,
        deployment_id: int,
        analysis_window_minutes: int = 10,
        deviation_threshold: float = 2.0  # Standard deviations from mean
    ) -> BottleneckResponse:
        """Detect bottlenecks in a deployment based on telemetry data.
        
        A bottleneck is identified when a node's metrics deviate significantly
        from the deployment's baseline (mean + threshold * standard deviation).
        
        Args:
            db: Database session
            deployment_id: Deployment ID
            analysis_window_minutes: Time window for analysis (default: 10 minutes)
            deviation_threshold: Number of standard deviations to consider a bottleneck
            
        Returns:
            BottleneckResponse with detected bottlenecks
        """
        cutoff_time = datetime.utcnow() - timedelta(minutes=analysis_window_minutes)
        
        # Get all recent telemetry samples for the deployment
        samples = db.query(TelemetrySample).filter(
            TelemetrySample.deployment_id == deployment_id,
            TelemetrySample.timestamp >= cutoff_time
        ).all()
        
        if not samples:
            return BottleneckResponse(
                deployment_id=deployment_id,
                detected_at=datetime.utcnow(),
                bottlenecks=[],
                total_bottlenecks=0,
                analysis_window_minutes=analysis_window_minutes,
            )
        
        # Calculate baseline statistics for the deployment
        latencies = [s.latency_ms for s in samples]
        throughputs = [s.throughput_gbps for s in samples]
        error_rates = [s.error_rate for s in samples]
        
        latency_mean = mean(latencies)
        latency_std = stdev(latencies) if len(latencies) > 1 else 0.0
        
        throughput_mean = mean(throughputs)
        throughput_std = stdev(throughputs) if len(throughputs) > 1 else 0.0
        
        error_rate_mean = mean(error_rates)
        error_rate_std = stdev(error_rates) if len(error_rates) > 1 else 0.0
        
        # Group samples by node to find node-level issues
        node_samples = {}
        for sample in samples:
            if sample.node_id not in node_samples:
                node_samples[sample.node_id] = []
            node_samples[sample.node_id].append(sample)
        
        bottlenecks = []
        
        # Check each node for deviations
        for node_id, node_sample_list in node_samples.items():
            # Get average metrics for this node in the time window
            node_latency = mean([s.latency_ms for s in node_sample_list])
            node_throughput = mean([s.throughput_gbps for s in node_sample_list])
            node_error_rate = mean([s.error_rate for s in node_sample_list])
            
            # Calculate deviation scores
            latency_deviation = (
                (node_latency - latency_mean) / latency_std
                if latency_std > 0 else 0.0
            )
            throughput_deviation = (
                (throughput_mean - node_throughput) / throughput_std
                if throughput_std > 0 else 0.0
            )
            error_rate_deviation = (
                (node_error_rate - error_rate_mean) / error_rate_std
                if error_rate_std > 0 else 0.0
            )
            
            # Combined deviation score (weighted)
            # Higher latency, lower throughput, or higher error rate = bottleneck
            deviation_score = (
                max(0, latency_deviation) * 0.4 +
                max(0, throughput_deviation) * 0.4 +
                max(0, error_rate_deviation) * 0.2
            )
            
            # Check if this node is a bottleneck
            is_bottleneck = (
                latency_deviation >= deviation_threshold or
                throughput_deviation >= deviation_threshold or
                error_rate_deviation >= deviation_threshold
            )
            
            if is_bottleneck:
                # Get node details
                node = db.query(Node).filter(Node.id == node_id).first()
                if node:
                    bottlenecks.append(BottleneckNode(
                        node_id=node.id,
                        node_identifier=node.node_id,
                        deployment_id=deployment_id,
                        latency_ms=node_latency,
                        throughput_gbps=node_throughput,
                        error_rate=node_error_rate,
                        deviation_score=deviation_score,
                        timestamp=max([s.timestamp for s in node_sample_list]),
                    ))
        
        # Sort by deviation score (worst first)
        bottlenecks.sort(key=lambda x: x.deviation_score, reverse=True)
        
        return BottleneckResponse(
            deployment_id=deployment_id,
            detected_at=datetime.utcnow(),
            bottlenecks=bottlenecks,
            total_bottlenecks=len(bottlenecks),
            analysis_window_minutes=analysis_window_minutes,
        )
