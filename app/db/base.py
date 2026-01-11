"""Database base configuration and session management.

This module provides the SQLAlchemy engine, session factory, and base model class.
The database is configured to use SQLite by default, but can be easily replaced
with PostgreSQL by changing the connection string in the engine configuration.

In production, you would:
- Use PostgreSQL or another production-grade database
- Configure connection pooling
- Set up database migrations (Alembic)
- Add read replicas for analytics queries
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# SQLite configuration with connection pooling for async operations
# In production, replace with PostgreSQL connection string:
# DATABASE_URL = "postgresql://user:password@localhost/dbname"
DATABASE_URL = "sqlite:///./network_orchestrator.db"

# SQLite requires StaticPool for thread-safe operations
# PostgreSQL would use NullPool or QueuePool
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    poolclass=StaticPool if "sqlite" in DATABASE_URL else None,
    echo=False,  # Set to True for SQL query logging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency for FastAPI to get database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
