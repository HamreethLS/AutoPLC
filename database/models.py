"""Database models for the PLC Agent System."""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class Project(Base):
    """Project entity for organizing PLC code generation tasks."""
    
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255))
    status = Column(String(50), default="active")
    
    # Relationships
    requirements = relationship("Requirement", back_populates="project", cascade="all, delete-orphan")
    code_versions = relationship("CodeVersion", back_populates="project", cascade="all, delete-orphan")


class Requirement(Base):
    """User requirements for PLC code generation."""
    
    __tablename__ = "requirements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    language = Column(String(10), default="st")
    safety_level = Column(Integer, default=1)
    constraints = Column(JSON, default=dict)
    test_scenarios = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="requirements")
    task_plans = relationship("TaskPlan", back_populates="requirement", cascade="all, delete-orphan")
    code_versions = relationship("CodeVersion", back_populates="requirement", cascade="all, delete-orphan")


class TaskPlan(Base):
    """Structured plans for code generation tasks."""
    
    __tablename__ = "task_plans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requirement_id = Column(UUID(as_uuid=True), ForeignKey("requirements.id"), nullable=False)
    steps = Column(JSON, nullable=False)
    estimated_duration = Column(Integer)  # seconds
    dependencies = Column(JSON, default=list)
    created_by = Column(String(50), default="planner")
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="pending")
    
    # Relationships
    requirement = relationship("Requirement", back_populates="task_plans")
    code_versions = relationship("CodeVersion", back_populates="task_plan")


class CodeVersion(Base):
    """Generated PLC code versions with metadata."""
    
    __tablename__ = "code_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False)
    requirement_id = Column(UUID(as_uuid=True), ForeignKey("requirements.id"), nullable=False)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("task_plans.id"))
    version_number = Column(Integer, nullable=False)
    language = Column(String(10), nullable=False)
    code = Column(Text, nullable=False)
    variables = Column(JSON, default=list)
    functions = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    generated_by = Column(String(50), default="generator")
    generated_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    project = relationship("Project", back_populates="code_versions")
    requirement = relationship("Requirement", back_populates="code_versions")
    task_plan = relationship("TaskPlan", back_populates="code_versions")
    validation_results = relationship("ValidationResult", back_populates="code_version", cascade="all, delete-orphan")
    simulation_results = relationship("SimulationResult", back_populates="code_version", cascade="all, delete-orphan")


class ValidationResult(Base):
    """Results of code validation processes."""
    
    __tablename__ = "validation_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_version_id = Column(UUID(as_uuid=True), ForeignKey("code_versions.id"), nullable=False)
    level = Column(String(50), nullable=False)  # syntax, semantic, safety, etc.
    passed = Column(Boolean, nullable=False)
    issues = Column(JSON, default=list)
    suggestions = Column(JSON, default=list)
    validated_by = Column(String(50), default="validator")
    validated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    code_version = relationship("CodeVersion", back_populates="validation_results")


class SimulationResult(Base):
    """Results of code simulation and testing."""
    
    __tablename__ = "simulation_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_version_id = Column(UUID(as_uuid=True), ForeignKey("code_versions.id"), nullable=False)
    scenario = Column(String(255), nullable=False)
    environment = Column(String(100), nullable=False)
    success = Column(Boolean, nullable=False)
    duration = Column(Float)  # seconds
    cycle_count = Column(Integer)
    max_cycle_time = Column(Float)  # milliseconds
    outputs = Column(JSON, default=dict)
    performance_metrics = Column(JSON, default=dict)
    errors = Column(JSON, default=list)
    warnings = Column(JSON, default=list)
    simulation_log = Column(JSON, default=list)
    simulated_by = Column(String(50), default="simulator")
    simulated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    code_version = relationship("CodeVersion", back_populates="simulation_results")


class WorkflowExecution(Base):
    """Execution history of agent workflows."""
    
    __tablename__ = "workflow_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    requirement_id = Column(UUID(as_uuid=True), ForeignKey("requirements.id"), nullable=False)
    workflow_type = Column(String(100), default="code_generation")
    status = Column(String(50), nullable=False)  # pending, running, completed, failed
    current_step = Column(Integer, default=0)
    total_steps = Column(Integer, nullable=False)
    active_agents = Column(JSON, default=list)
    completed_tasks = Column(JSON, default=list)
    failed_tasks = Column(JSON, default=list)
    state_data = Column(JSON, default=dict)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    
    # Relationships
    requirement = relationship("Requirement")
    agent_tasks = relationship("AgentTask", back_populates="workflow", cascade="all, delete-orphan")


class AgentTask(Base):
    """Individual tasks executed by agents."""
    
    __tablename__ = "agent_tasks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workflow_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=False)
    agent_role = Column(String(50), nullable=False)
    task_type = Column(String(100), nullable=False)
    input_data = Column(JSON, default=dict)
    status = Column(String(50), default="pending")
    result = Column(JSON)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    timeout = Column(Integer, default=300)  # seconds
    retry_count = Column(Integer, default=0)
    
    # Relationships
    workflow = relationship("WorkflowExecution", back_populates="agent_tasks")


class KnowledgeDocument(Base):
    """Domain knowledge documents for RAG system."""
    
    __tablename__ = "knowledge_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    document_type = Column(String(100))  # standard, example, pattern, etc.
    tags = Column(JSON, default=list)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class TelemetryData(Base):
    """Runtime telemetry and monitoring data."""
    
    __tablename__ = "telemetry_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(String(255), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    metrics = Column(JSON, default=dict)
    tags = Column(JSON, default=dict)
    alerts = Column(JSON, default=list)
    severity = Column(String(20), default="info")  # info, warning, error, critical


class DeploymentRecord(Base):
    """Records of code deployments to PLC systems."""
    
    __tablename__ = "deployment_records"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_version_id = Column(UUID(as_uuid=True), ForeignKey("code_versions.id"), nullable=False)
    target_system = Column(String(255), nullable=False)
    deployment_type = Column(String(50), default="production")  # development, staging, production
    status = Column(String(50), nullable=False)  # pending, deployed, failed, rolled_back
    deployed_at = Column(DateTime)
    rolled_back_at = Column(DateTime)
    deployment_metadata = Column(JSON, default=dict)
    health_checks = Column(JSON, default=list)
    
    # Relationships
    code_version = relationship("CodeVersion")


class AuditLog(Base):
    """Audit log for system activities."""
    
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255))
    agent_role = Column(String(50))
    action = Column(String(100), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(UUID(as_uuid=True))
    details = Column(JSON, default=dict)
    timestamp = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))
    user_agent = Column(Text)


class SystemConfiguration(Base):
    """System configuration settings."""
    
    __tablename__ = "system_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(255), unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    description = Column(Text)
    category = Column(String(100))
    is_sensitive = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String(255))
