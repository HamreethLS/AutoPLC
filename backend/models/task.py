"""
Database models for AutoPLC Enhanced
"""

from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Float, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class AgentRole(str, Enum):
    PLANNER = "planner"
    KNOWLEDGE = "knowledge"
    RETRIEVAL = "retrieval"
    CODER = "coder"
    VALIDATOR = "validator"
    SUPERVISOR = "supervisor"

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    prompt = Column(Text, nullable=False)
    user_id = Column(String(100), nullable=False, default="default")
    status = Column(SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING)
    
    # Progress and timing
    progress = Column(Float, default=0.0)
    current_agent = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Results
    generated_code = Column(Text)
    quality_score = Column(Float)
    error_message = Column(Text)
    
    # Metadata
    context = Column(JSON, default=dict)
    retry_count = Column(Integer, default=0)
    
    # Relationships
    messages = relationship("AgentMessage", back_populates="task", cascade="all, delete-orphan")
    feedback_sessions = relationship("FeedbackSession", back_populates="task", cascade="all, delete-orphan")

class AgentMessage(Base):
    __tablename__ = "agent_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    agent_role = Column(SQLEnum(AgentRole), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Metadata for analysis
    meta = Column(JSON, default=dict)  # response_time, token_count, etc.
    
    # Relationships
    task = relationship("Task", back_populates="messages")

class FeedbackSession(Base):
    __tablename__ = "feedback_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    user_id = Column(String(100), nullable=False)
    feedback_text = Column(Text, nullable=False)
    
    # Results of feedback processing
    original_code = Column(Text)
    improved_code = Column(Text)
    improvement_score = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    
    # Relationships
    task = relationship("Task", back_populates="feedback_sessions")

class AgentPerformance(Base):
    __tablename__ = "agent_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    agent_role = Column(SQLEnum(AgentRole), nullable=False)
    
    # Performance metrics
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    avg_response_time = Column(Float, default=0.0)
    avg_quality_score = Column(Float, default=0.0)
    
    # Tracking period
    date = Column(DateTime, default=datetime.utcnow)
    
class KnowledgeBaseEntry(Base):
    __tablename__ = "knowledge_base_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="text")  # text, pdf, code, etc.
    
    # Vector embedding info (stored in ChromaDB, referenced here)
    chunk_id = Column(String(100), unique=True)
    embedding_model = Column(String(100), default="all-MiniLM-L6-v2")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
