"""Database connection and session management."""

import logging
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from core.config import settings
from database.models import Base


class DatabaseManager:
    """Manages database connections and sessions."""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.logger = logging.getLogger("database")
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize the database engine."""
        try:
            # Create engine with connection pooling
            self.engine = create_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,  # 1 hour
                echo=settings.debug  # Log SQL queries in debug mode
            )
            
            # Create session factory
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Add connection event listeners
            self._setup_event_listeners()
            
            self.logger.info("Database engine initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database engine: {str(e)}")
            raise
    
    def _setup_event_listeners(self):
        """Setup database event listeners for monitoring."""
        
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set SQLite pragmas if using SQLite."""
            if "sqlite" in settings.database_url:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Log connection checkout."""
            self.logger.debug("Connection checked out from pool")
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Log connection checkin."""
            self.logger.debug("Connection checked in to pool")
    
    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            self.logger.info("Database tables created successfully")
        except Exception as e:
            self.logger.error(f"Failed to create database tables: {str(e)}")
            raise
    
    def drop_tables(self):
        """Drop all database tables."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            self.logger.info("Database tables dropped successfully")
        except Exception as e:
            self.logger.error(f"Failed to drop database tables: {str(e)}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            self.logger.error(f"Database session error: {str(e)}")
            raise
        finally:
            session.close()
    
    def get_session_sync(self) -> Session:
        """Get a database session for synchronous use."""
        return self.SessionLocal()
    
    def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            self.logger.error(f"Database health check failed: {str(e)}")
            return False
    
    def get_connection_info(self) -> dict:
        """Get database connection information."""
        return {
            "url": settings.database_url.split("@")[-1] if "@" in settings.database_url else settings.database_url,
            "pool_size": self.engine.pool.size() if self.engine else 0,
            "checked_in": self.engine.pool.checkedin() if self.engine else 0,
            "checked_out": self.engine.pool.checkedout() if self.engine else 0,
            "overflow": self.engine.pool.overflow() if self.engine else 0
        }


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions."""
    with db_manager.get_session() as session:
        yield session


# Convenience functions
def get_session() -> Generator[Session, None, None]:
    """Get a database session context manager."""
    return db_manager.get_session()


def create_all_tables():
    """Create all database tables."""
    db_manager.create_tables()


def drop_all_tables():
    """Drop all database tables."""
    db_manager.drop_tables()


def check_database_health() -> bool:
    """Check database health."""
    return db_manager.health_check()
