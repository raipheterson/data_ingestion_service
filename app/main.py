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

import logging
import os
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.db.base import Base, engine
from app.api import deployments, health
from app.workers.lifecycle_worker import lifecycle_worker
from app.workers.telemetry_worker import telemetry_worker


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and filename-only logger names."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def format(self, record):
        # Extract filename from logger name (e.g., 'app.api.deployments' -> 'deployments')
        logger_name = record.name
        if '.' in logger_name:
            filename = logger_name.split('.')[-1]
        else:
            filename = logger_name
        
        # Get color for log level
        level_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset_color = self.COLORS['RESET']
        
        # Format the message
        record.name = filename
        record.levelname = f"{level_color}{record.levelname}{reset_color}"
        
        return super().format(record)


# Configure logging with colors
def setup_logging():
    """Configure logging with colored output and filename-only names."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(ColoredFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [handler]

setup_logging()
logger = logging.getLogger(__name__)


# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan: startup and shutdown events.
    
    Starts background workers on startup and stops them on shutdown.
    """
    # Startup: Start background workers
    logger.info("Starting background workers: lifecycle_worker and telemetry_worker")
    await lifecycle_worker.start()
    await telemetry_worker.start()
    logger.info("Application started successfully")
    yield
    # Shutdown: Stop background workers
    logger.info("Stopping background workers")
    await lifecycle_worker.stop()
    await telemetry_worker.stop()
    logger.info("Application shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Network Deployment & Telemetry Orchestrator",
    description="Internal infrastructure service for simulating large-scale network deployments",
    version="1.0.0",
    lifespan=lifespan,
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
