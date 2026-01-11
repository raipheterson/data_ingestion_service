"""Pytest configuration and fixtures.

This module provides shared fixtures for testing, including:
- Test database setup (in-memory SQLite for speed)
- FastAPI TestClient
- Application instance without background workers (for deterministic tests)
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base, get_db
from app.main import app


# Create in-memory SQLite database for tests
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test.
    
    Creates tables, yields session, then drops tables for cleanup.
    """
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create session
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # Drop all tables for clean state
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Create a FastAPI TestClient with test database dependency override.
    
    Overrides the database dependency to use the test database instead of
    the production database. Background workers are not started for tests
    to keep them deterministic and fast.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session cleanup handled by db_session fixture
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up dependency override
    app.dependency_overrides.clear()
