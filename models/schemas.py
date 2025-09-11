"""Data models and schemas for the PLC Agent System."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4


class AgentRole(str, Enum):
    """Enumeration of agent roles in the system."""
    RETRIEVAL = "retrieval"
    PLANNER = "planner"
    GENERATOR = "generator"
    VALIDATOR = "validator"
    DEBUGGER = "debugger"
    SIMULATOR = "simulator"
    MONITOR = "monitor"
    ORCHESTRATOR = "orchestrator"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ValidationLevel(str, Enum):
    """Validation levels for PLC code."""
    SYNTAX = "syntax"
    SEMANTIC = "semantic"
    SAFETY = "safety"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"


class PLCLanguage(str, Enum):
    """Supported PLC programming languages."""
    STRUCTURED_TEXT = "st"
    LADDER_DIAGRAM = "ld"
    FUNCTION_BLOCK = "fbd"
    INSTRUCTION_LIST = "il"
    SEQUENTIAL_FUNCTION_CHART = "sfc"


class UserRequirement(BaseModel):
    """User specification for PLC code generation."""
    id: UUID = Field(default_factory=uuid4)
    title: str
    description: str
    language: PLCLanguage = PLCLanguage.STRUCTURED_TEXT
    safety_level: int = Field(ge=1, le=4, description="Safety Integrity Level (SIL)")
    constraints: Dict[str, Any] = Field(default_factory=dict)
    test_scenarios: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentMessage(BaseModel):
    """Message passed between agents."""
    id: UUID = Field(default_factory=uuid4)
    sender: AgentRole
    receiver: AgentRole
    content: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[UUID] = None


class TaskPlan(BaseModel):
    """Structured plan for code generation task."""
    id: UUID = Field(default_factory=uuid4)
    requirement_id: UUID
    steps: List[Dict[str, Any]]
    estimated_duration: int  # seconds
    dependencies: List[UUID] = Field(default_factory=list)
    created_by: AgentRole = AgentRole.PLANNER
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GeneratedCode(BaseModel):
    """Generated PLC code with metadata."""
    id: UUID = Field(default_factory=uuid4)
    requirement_id: UUID
    plan_id: UUID
    language: PLCLanguage
    code: str
    variables: List[Dict[str, Any]] = Field(default_factory=list)
    functions: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    generated_by: AgentRole = AgentRole.GENERATOR
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ValidationResult(BaseModel):
    """Result of code validation."""
    id: UUID = Field(default_factory=uuid4)
    code_id: UUID
    level: ValidationLevel
    passed: bool
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    validated_by: AgentRole = AgentRole.VALIDATOR
    validated_at: datetime = Field(default_factory=datetime.utcnow)


class SimulationResult(BaseModel):
    """Result of code simulation."""
    id: UUID = Field(default_factory=uuid4)
    code_id: UUID
    scenario: str
    success: bool
    outputs: Dict[str, Any] = Field(default_factory=dict)
    performance_metrics: Dict[str, float] = Field(default_factory=dict)
    logs: List[str] = Field(default_factory=list)
    simulated_by: AgentRole = AgentRole.SIMULATOR
    simulated_at: datetime = Field(default_factory=datetime.utcnow)


class AgentTask(BaseModel):
    """Task assigned to an agent."""
    id: UUID = Field(default_factory=uuid4)
    agent_role: AgentRole
    task_type: str
    input_data: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout: int = 300  # seconds


class WorkflowState(BaseModel):
    """Current state of the agent workflow."""
    id: UUID = Field(default_factory=uuid4)
    requirement_id: UUID
    current_step: int = 0
    total_steps: int
    active_agents: List[AgentRole] = Field(default_factory=list)
    completed_tasks: List[UUID] = Field(default_factory=list)
    failed_tasks: List[UUID] = Field(default_factory=list)
    state_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TelemetryData(BaseModel):
    """Runtime telemetry data."""
    id: UUID = Field(default_factory=uuid4)
    source: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metrics: Dict[str, float] = Field(default_factory=dict)
    tags: Dict[str, str] = Field(default_factory=dict)
    alerts: List[str] = Field(default_factory=list)
