"""Main FastAPI application entry point.

This module sets up the FastAPI application, includes routers, and manages
background workers for node lifecycle and telemetry collection.

In production, you would:
- Add authentication/authorization middleware
- Configure CORS policies
- Set up request logging and monitoring
- Add rate limiting
- Implement graceful shutdown
- Use a process manager (systemd, supervisord) or container orchestration
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.base import Base, engine
from app.api import deployments, health
from app.workers.lifecycle_worker import lifecycle_worker
from app.workers.telemetry_worker import telemetry_worker


# Create database tables
# In production, use Alembic for migrations instead
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: startup and shutdown events.
    
    Starts background workers on startup and stops them on shutdown.
    """
    # Startup: Start background workers
    await lifecycle_worker.start()
    await telemetry_worker.start()
    yield
    # Shutdown: Stop background workers
    await lifecycle_worker.stop()
    await telemetry_worker.stop()


# Create FastAPI application
app = FastAPI(
    title="Network Deployment & Telemetry Orchestrator",
    description="Internal infrastructure service for simulating large-scale network deployments",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS (in production, restrict to specific origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(deployments.router)
app.include_router(health.router)


@app.get("/")
def root():
    """Root endpoint with API information."""
    return {
        "service": "Network Deployment & Telemetry Orchestrator",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
