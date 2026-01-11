# Network Deployment & Telemetry Orchestrator

A production-style backend service that simulates large-scale network deployments (100-200 switches) for orchestration, monitoring, and bottleneck detection. The hardware is simulated, but the architecture, workflows, and data handling are realistic and production-oriented.

## Overview

This service provides a REST API for managing network deployments, tracking node lifecycles, collecting telemetry data, and detecting performance bottlenecks. It's designed as an internal infrastructure service that demonstrates production-grade patterns for:

- **Deployment Orchestration**: Create and manage network deployments with multiple nodes
- **Node Lifecycle Management**: State machine-based lifecycle (PENDING → PROVISIONING → CONFIGURING → RUNNING/FAILED)
- **Telemetry Collection**: Time-series metrics (latency, throughput, error rate) with periodic background collection
- **Bottleneck Detection**: Statistical analysis to identify nodes with abnormal performance
- **Separation of Concerns**: Clean architecture with distinct layers for API, services, workers, and data models

## Architecture

### Project Structure

```
app/
├── main.py              # FastAPI application entry point
├── api/                 # API route handlers
│   ├── deployments.py   # Deployment endpoints
│   └── health.py        # Health check endpoint
├── services/            # Business logic layer
│   ├── deployment_service.py
│   ├── node_service.py
│   ├── telemetry_service.py
│   └── analytics_service.py
├── workers/             # Background async workers
│   ├── lifecycle_worker.py  # Node state transitions
│   └── telemetry_worker.py  # Telemetry generation
├── models/              # SQLAlchemy ORM models
│   └── models.py
├── schemas/             # Pydantic request/response schemas
│   └── schemas.py
└── db/                  # Database configuration
    └── base.py
```

### Core Components

#### 1. **Database Models**
- **Deployment**: Represents a network deployment with multiple nodes
- **Node**: Individual network device with lifecycle state machine
- **TelemetrySample**: Time-series metrics (latency, throughput, error rate)
- **Event**: Audit log of state transitions and errors

#### 2. **State Machine**
Nodes progress through a deterministic state machine:
```
PENDING → PROVISIONING → CONFIGURING → RUNNING (or FAILED)
```

State transitions are managed by the `LifecycleWorker` background task, which simulates realistic provisioning and configuration timing.

#### 3. **Background Workers**
- **LifecycleWorker**: Manages node state transitions with deterministic timing based on node IDs
- **TelemetryWorker**: Generates telemetry data every 5 seconds for all RUNNING nodes

#### 4. **Analytics**
The bottleneck detection algorithm uses statistical deviation analysis:
- Calculates baseline metrics (mean, standard deviation) for the deployment
- Identifies nodes with metrics >2 standard deviations from baseline
- Returns nodes sorted by deviation score

## API Endpoints

### Deployments
- `POST /deployments` - Create a new deployment with N nodes
- `GET /deployments` - List all deployments
- `GET /deployments/{deployment_id}` - Get deployment details
- `GET /deployments/{deployment_id}/nodes` - Get all nodes for a deployment
- `GET /deployments/{deployment_id}/telemetry` - Get telemetry data (with optional filters)
- `GET /deployments/{deployment_id}/bottlenecks` - Detect bottlenecks in a deployment

### Health
- `GET /health` - Health check endpoint

### Documentation
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

## Installation & Setup

### Prerequisites
- Python 3.9+
- pip

### Installation

1. **Clone the repository** (or navigate to the project directory)

2. **Create a virtual environment** (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Run the application**:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Quick Start Example

1. **Create a deployment**:
```bash
curl -X POST "http://localhost:8000/deployments" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Network",
    "description": "Main production deployment",
    "target_node_count": 50
  }'
```

2. **Check deployment status**:
```bash
curl "http://localhost:8000/deployments/1"
```

3. **View nodes**:
```bash
curl "http://localhost:8000/deployments/1/nodes"
```

4. **Get telemetry** (after nodes reach RUNNING state):
```bash
curl "http://localhost:8000/deployments/1/telemetry"
```

5. **Detect bottlenecks**:
```bash
curl "http://localhost:8000/deployments/1/bottlenecks?analysis_window_minutes=10"
```

## Testing

The project includes a minimal pytest test suite that covers all core functionality.

### Running Tests

1. **Install test dependencies** (already included in requirements.txt):
```bash
pip install -r requirements.txt
```

2. **Run all tests**:
```bash
pytest
```

3. **Run with verbose output**:
```bash
pytest -v
```

4. **Run a specific test file**:
```bash
pytest tests/test_deployments.py
```

### Test Coverage

The test suite includes:
- **Health endpoint** (`test_health.py`): Verifies health check structure
- **Deployment endpoints** (`test_deployments.py`): Tests deployment creation, retrieval, and listing
- **Node lifecycle** (`test_node_lifecycle.py`): Verifies state machine transitions
- **Telemetry endpoints** (`test_telemetry.py`): Tests telemetry data retrieval and filtering
- **Bottleneck detection** (`test_bottlenecks.py`): Verifies bottleneck analysis output structure

### Test Design

- **Deterministic**: Tests use in-memory SQLite database for fast, isolated execution
- **No mocking**: Tests use actual services and database operations
- **Fast execution**: In-memory database and no background workers in test mode
- **Clean state**: Each test gets a fresh database session

## Design Decisions & Tradeoffs

### Database Choice: SQLite → PostgreSQL
- **Current**: SQLite for simplicity and zero-configuration
- **Production**: Easily replaceable with PostgreSQL by changing the connection string in `app/db/base.py`
- **Tradeoff**: SQLite is sufficient for development/testing but lacks:
  - Concurrent write performance
  - Advanced indexing strategies
  - Time-series optimizations

### Telemetry Storage
- **Current**: Stored in relational tables (SQLAlchemy)
- **Production Recommendation**: Use a time-series database (InfluxDB, TimescaleDB) for:
  - Better query performance on time-range queries
  - Automatic data retention policies
  - Compression and downsampling
  - Higher write throughput

### Deterministic Simulation
- **Approach**: Telemetry and state transitions use deterministic algorithms based on node IDs
- **Benefit**: Reproducible results for testing and debugging
- **Production**: Would be replaced with actual hardware APIs and real-time data collection

### Background Workers
- **Current**: Simple asyncio tasks running in the same process
- **Production**: Consider:
  - Separate worker processes (Celery, RQ)
  - Distributed task queues (RabbitMQ, Redis)
  - Horizontal scaling of workers
  - Worker health monitoring and auto-restart

### Bottleneck Detection Algorithm
- **Current**: Statistical deviation (mean ± 2σ)
- **Limitations**: Simple threshold-based approach
- **Production Enhancements**:
  - Machine learning models for anomaly detection
  - Historical trend analysis
  - Multi-metric correlation
  - Real-time alerting integration

### Error Handling
- **Current**: Basic exception handling with HTTP status codes
- **Production**: Add:
  - Structured logging (JSON logs)
  - Error tracking (Sentry, Rollbar)
  - Retry mechanisms with exponential backoff
  - Circuit breakers for external dependencies

## Production Considerations

### Where Real Integration Would Happen

1. **Hardware Provisioning** (`app/workers/lifecycle_worker.py`):
   - Replace simulation with cloud provider APIs (AWS EC2, Azure VMs, GCP Compute)
   - Integrate with infrastructure-as-code tools (Terraform, Ansible)

2. **Configuration Management** (`app/services/node_service.py`):
   - NETCONF/YANG for network device configuration
   - Ansible playbooks for automated setup
   - Configuration versioning and rollback

3. **Telemetry Collection** (`app/workers/telemetry_worker.py`):
   - SNMP polling for network devices
   - gRPC/HTTP agents running on nodes
   - Streaming data pipelines (Kafka, RabbitMQ)

4. **Monitoring & Alerting** (`app/services/analytics_service.py`):
   - Integration with Prometheus, Grafana
   - PagerDuty/OpsGenie for alerts
   - Real-time dashboards

### Missing Production Features (Intentionally Excluded)

- **Authentication/Authorization**: Add OAuth2, JWT tokens, or API keys
- **Docker**: Containerization for deployment
- **Database Migrations**: Use Alembic for schema versioning
- **Caching**: Redis for frequently accessed data
- **Rate Limiting**: Protect API from abuse
- **API Versioning**: Support multiple API versions simultaneously

## Testing

While not included in this implementation, production code should include:
- Unit tests for services and workers
- Integration tests for API endpoints
- Load testing for telemetry ingestion
- End-to-end tests for deployment workflows

## License

Internal infrastructure service - not for external distribution.
