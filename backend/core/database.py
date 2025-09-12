"""
Database configuration and session management
"""

import os
from typing import Generator, AsyncGenerator

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.models.task import Base
from backend.core.config import get_settings

settings = get_settings()

# --- Async Engine (for FastAPI endpoints) ---
async_db_url = settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
async_engine = create_async_engine(
    async_db_url,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if "sqlite" in async_db_url else {}
)
AsyncSessionLocal = async_sessionmaker(async_engine, class_=AsyncSession, expire_on_commit=False)

# --- Sync Engine (for scripts or non-async parts) ---
# Using connect_args for SQLite is standard practice with FastAPI
sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
connect_args = {"check_same_thread": False} if "sqlite" in sync_db_url else {}
sync_engine = create_engine(
    sync_db_url,
    poolclass=StaticPool if "sqlite" in sync_db_url else None,
    echo=settings.DEBUG,
    connect_args=connect_args
)

# --- Session Makers ---
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

async def init_db():
    """Initialize the database with all tables"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database initialized successfully")

def get_db() -> Generator[Session, None, None]:
    """Dependency to get database session (sync)"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get an async database session."""
    async with AsyncSessionLocal() as session:
        yield session
