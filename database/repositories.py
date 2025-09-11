"""Repository classes for database operations."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_

from database.models import (
    Project, Requirement, TaskPlan, CodeVersion, ValidationResult,
    SimulationResult, WorkflowExecution, AgentTask, KnowledgeDocument,
    TelemetryData, DeploymentRecord, AuditLog
)


class BaseRepository:
    """Base repository with common CRUD operations."""
    
    def __init__(self, session: Session, model_class):
        self.session = session
        self.model_class = model_class
        self.logger = logging.getLogger(f"repository.{model_class.__name__.lower()}")
    
    def create(self, **kwargs) -> Any:
        """Create a new record."""
        try:
            instance = self.model_class(**kwargs)
            self.session.add(instance)
            self.session.flush()
            return instance
        except Exception as e:
            self.logger.error(f"Failed to create {self.model_class.__name__}: {str(e)}")
            raise
    
    def get_by_id(self, id: UUID) -> Optional[Any]:
        """Get record by ID."""
        return self.session.query(self.model_class).filter(self.model_class.id == id).first()
    
    def get_all(self, limit: int = 100, offset: int = 0) -> List[Any]:
        """Get all records with pagination."""
        return self.session.query(self.model_class).offset(offset).limit(limit).all()
    
    def update(self, id: UUID, **kwargs) -> Optional[Any]:
        """Update a record by ID."""
        try:
            instance = self.get_by_id(id)
            if instance:
                for key, value in kwargs.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                if hasattr(instance, 'updated_at'):
                    instance.updated_at = datetime.utcnow()
                self.session.flush()
            return instance
        except Exception as e:
            self.logger.error(f"Failed to update {self.model_class.__name__}: {str(e)}")
            raise
    
    def delete(self, id: UUID) -> bool:
        """Delete a record by ID."""
        try:
            instance = self.get_by_id(id)
            if instance:
                self.session.delete(instance)
                self.session.flush()
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete {self.model_class.__name__}: {str(e)}")
            raise


class ProjectRepository(BaseRepository):
    """Repository for Project operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, Project)
    
    def get_by_name(self, name: str) -> Optional[Project]:
        """Get project by name."""
        return self.session.query(Project).filter(Project.name == name).first()
    
    def get_active_projects(self) -> List[Project]:
        """Get all active projects."""
        return self.session.query(Project).filter(Project.status == "active").all()
    
    def get_projects_by_user(self, user_id: str) -> List[Project]:
        """Get projects created by a specific user."""
        return self.session.query(Project).filter(Project.created_by == user_id).all()


class RequirementRepository(BaseRepository):
    """Repository for Requirement operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, Requirement)
    
    def get_by_project(self, project_id: UUID) -> List[Requirement]:
        """Get requirements for a project."""
        return self.session.query(Requirement).filter(Requirement.project_id == project_id).all()
    
    def get_by_safety_level(self, safety_level: int) -> List[Requirement]:
        """Get requirements by safety level."""
        return self.session.query(Requirement).filter(Requirement.safety_level == safety_level).all()
    
    def search_by_description(self, search_term: str) -> List[Requirement]:
        """Search requirements by description."""
        return self.session.query(Requirement).filter(
            Requirement.description.ilike(f"%{search_term}%")
        ).all()


class TaskPlanRepository(BaseRepository):
    """Repository for TaskPlan operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, TaskPlan)
    
    def get_by_requirement(self, requirement_id: UUID) -> List[TaskPlan]:
        """Get task plans for a requirement."""
        return self.session.query(TaskPlan).filter(TaskPlan.requirement_id == requirement_id).all()
    
    def get_pending_plans(self) -> List[TaskPlan]:
        """Get all pending task plans."""
        return self.session.query(TaskPlan).filter(TaskPlan.status == "pending").all()
    
    def get_by_status(self, status: str) -> List[TaskPlan]:
        """Get task plans by status."""
        return self.session.query(TaskPlan).filter(TaskPlan.status == status).all()


class CodeVersionRepository(BaseRepository):
    """Repository for CodeVersion operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, CodeVersion)
    
    def get_by_requirement(self, requirement_id: UUID) -> List[CodeVersion]:
        """Get code versions for a requirement."""
        return self.session.query(CodeVersion).filter(
            CodeVersion.requirement_id == requirement_id
        ).order_by(desc(CodeVersion.version_number)).all()
    
    def get_latest_version(self, requirement_id: UUID) -> Optional[CodeVersion]:
        """Get the latest code version for a requirement."""
        return self.session.query(CodeVersion).filter(
            CodeVersion.requirement_id == requirement_id
        ).order_by(desc(CodeVersion.version_number)).first()
    
    def get_active_versions(self) -> List[CodeVersion]:
        """Get all active code versions."""
        return self.session.query(CodeVersion).filter(CodeVersion.is_active == True).all()
    
    def get_by_project(self, project_id: UUID) -> List[CodeVersion]:
        """Get code versions for a project."""
        return self.session.query(CodeVersion).filter(CodeVersion.project_id == project_id).all()
    
    def create_new_version(self, requirement_id: UUID, **kwargs) -> CodeVersion:
        """Create a new code version with auto-incremented version number."""
        latest = self.get_latest_version(requirement_id)
        version_number = (latest.version_number + 1) if latest else 1
        
        return self.create(
            requirement_id=requirement_id,
            version_number=version_number,
            **kwargs
        )


class ValidationResultRepository(BaseRepository):
    """Repository for ValidationResult operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, ValidationResult)
    
    def get_by_code_version(self, code_version_id: UUID) -> List[ValidationResult]:
        """Get validation results for a code version."""
        return self.session.query(ValidationResult).filter(
            ValidationResult.code_version_id == code_version_id
        ).all()
    
    def get_by_level(self, level: str) -> List[ValidationResult]:
        """Get validation results by level."""
        return self.session.query(ValidationResult).filter(ValidationResult.level == level).all()
    
    def get_failed_validations(self) -> List[ValidationResult]:
        """Get all failed validation results."""
        return self.session.query(ValidationResult).filter(ValidationResult.passed == False).all()


class SimulationResultRepository(BaseRepository):
    """Repository for SimulationResult operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, SimulationResult)
    
    def get_by_code_version(self, code_version_id: UUID) -> List[SimulationResult]:
        """Get simulation results for a code version."""
        return self.session.query(SimulationResult).filter(
            SimulationResult.code_version_id == code_version_id
        ).all()
    
    def get_by_scenario(self, scenario: str) -> List[SimulationResult]:
        """Get simulation results by scenario."""
        return self.session.query(SimulationResult).filter(SimulationResult.scenario == scenario).all()
    
    def get_successful_simulations(self) -> List[SimulationResult]:
        """Get all successful simulation results."""
        return self.session.query(SimulationResult).filter(SimulationResult.success == True).all()
    
    def get_performance_metrics(self, code_version_id: UUID) -> Dict[str, Any]:
        """Get aggregated performance metrics for a code version."""
        results = self.get_by_code_version(code_version_id)
        
        if not results:
            return {}
        
        total_cycles = sum(r.cycle_count or 0 for r in results)
        total_duration = sum(r.duration or 0 for r in results)
        max_cycle_time = max(r.max_cycle_time or 0 for r in results)
        success_rate = sum(1 for r in results if r.success) / len(results) * 100
        
        return {
            "total_simulations": len(results),
            "total_cycles": total_cycles,
            "total_duration": total_duration,
            "max_cycle_time": max_cycle_time,
            "success_rate": success_rate,
            "avg_duration": total_duration / len(results) if results else 0
        }


class WorkflowExecutionRepository(BaseRepository):
    """Repository for WorkflowExecution operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, WorkflowExecution)
    
    def get_by_requirement(self, requirement_id: UUID) -> List[WorkflowExecution]:
        """Get workflow executions for a requirement."""
        return self.session.query(WorkflowExecution).filter(
            WorkflowExecution.requirement_id == requirement_id
        ).order_by(desc(WorkflowExecution.started_at)).all()
    
    def get_active_workflows(self) -> List[WorkflowExecution]:
        """Get all active workflow executions."""
        return self.session.query(WorkflowExecution).filter(
            WorkflowExecution.status.in_(["pending", "running"])
        ).all()
    
    def get_by_status(self, status: str) -> List[WorkflowExecution]:
        """Get workflow executions by status."""
        return self.session.query(WorkflowExecution).filter(WorkflowExecution.status == status).all()
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get workflow execution statistics."""
        total = self.session.query(WorkflowExecution).count()
        completed = self.session.query(WorkflowExecution).filter(WorkflowExecution.status == "completed").count()
        failed = self.session.query(WorkflowExecution).filter(WorkflowExecution.status == "failed").count()
        running = self.session.query(WorkflowExecution).filter(WorkflowExecution.status == "running").count()
        
        return {
            "total_workflows": total,
            "completed": completed,
            "failed": failed,
            "running": running,
            "success_rate": (completed / total * 100) if total > 0 else 0
        }


class AgentTaskRepository(BaseRepository):
    """Repository for AgentTask operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, AgentTask)
    
    def get_by_workflow(self, workflow_id: UUID) -> List[AgentTask]:
        """Get agent tasks for a workflow."""
        return self.session.query(AgentTask).filter(AgentTask.workflow_id == workflow_id).all()
    
    def get_by_agent_role(self, agent_role: str) -> List[AgentTask]:
        """Get tasks by agent role."""
        return self.session.query(AgentTask).filter(AgentTask.agent_role == agent_role).all()
    
    def get_pending_tasks(self) -> List[AgentTask]:
        """Get all pending tasks."""
        return self.session.query(AgentTask).filter(AgentTask.status == "pending").all()
    
    def get_failed_tasks(self) -> List[AgentTask]:
        """Get all failed tasks."""
        return self.session.query(AgentTask).filter(AgentTask.status == "failed").all()
    
    def get_task_statistics(self) -> Dict[str, Any]:
        """Get task execution statistics."""
        total = self.session.query(AgentTask).count()
        completed = self.session.query(AgentTask).filter(AgentTask.status == "completed").count()
        failed = self.session.query(AgentTask).filter(AgentTask.status == "failed").count()
        pending = self.session.query(AgentTask).filter(AgentTask.status == "pending").count()
        
        return {
            "total_tasks": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "success_rate": (completed / total * 100) if total > 0 else 0
        }


class KnowledgeDocumentRepository(BaseRepository):
    """Repository for KnowledgeDocument operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, KnowledgeDocument)
    
    def get_active_documents(self) -> List[KnowledgeDocument]:
        """Get all active knowledge documents."""
        return self.session.query(KnowledgeDocument).filter(KnowledgeDocument.is_active == True).all()
    
    def get_by_type(self, document_type: str) -> List[KnowledgeDocument]:
        """Get documents by type."""
        return self.session.query(KnowledgeDocument).filter(
            KnowledgeDocument.document_type == document_type
        ).all()
    
    def search_by_content(self, search_term: str) -> List[KnowledgeDocument]:
        """Search documents by content."""
        return self.session.query(KnowledgeDocument).filter(
            or_(
                KnowledgeDocument.title.ilike(f"%{search_term}%"),
                KnowledgeDocument.content.ilike(f"%{search_term}%")
            )
        ).all()
    
    def get_by_tags(self, tags: List[str]) -> List[KnowledgeDocument]:
        """Get documents by tags."""
        return self.session.query(KnowledgeDocument).filter(
            KnowledgeDocument.tags.op('@>')([tags])
        ).all()


class TelemetryDataRepository(BaseRepository):
    """Repository for TelemetryData operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, TelemetryData)
    
    def get_by_source(self, source: str, limit: int = 100) -> List[TelemetryData]:
        """Get telemetry data by source."""
        return self.session.query(TelemetryData).filter(
            TelemetryData.source == source
        ).order_by(desc(TelemetryData.timestamp)).limit(limit).all()
    
    def get_by_severity(self, severity: str) -> List[TelemetryData]:
        """Get telemetry data by severity."""
        return self.session.query(TelemetryData).filter(TelemetryData.severity == severity).all()
    
    def get_recent_data(self, hours: int = 24) -> List[TelemetryData]:
        """Get recent telemetry data."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return self.session.query(TelemetryData).filter(
            TelemetryData.timestamp >= cutoff_time
        ).order_by(desc(TelemetryData.timestamp)).all()
    
    def get_alerts(self) -> List[TelemetryData]:
        """Get telemetry data with alerts."""
        return self.session.query(TelemetryData).filter(
            TelemetryData.alerts != []
        ).order_by(desc(TelemetryData.timestamp)).all()


class AuditLogRepository(BaseRepository):
    """Repository for AuditLog operations."""
    
    def __init__(self, session: Session):
        super().__init__(session, AuditLog)
    
    def get_by_user(self, user_id: str, limit: int = 100) -> List[AuditLog]:
        """Get audit logs by user."""
        return self.session.query(AuditLog).filter(
            AuditLog.user_id == user_id
        ).order_by(desc(AuditLog.timestamp)).limit(limit).all()
    
    def get_by_action(self, action: str) -> List[AuditLog]:
        """Get audit logs by action."""
        return self.session.query(AuditLog).filter(AuditLog.action == action).all()
    
    def get_by_resource(self, resource_type: str, resource_id: UUID) -> List[AuditLog]:
        """Get audit logs for a specific resource."""
        return self.session.query(AuditLog).filter(
            and_(
                AuditLog.resource_type == resource_type,
                AuditLog.resource_id == resource_id
            )
        ).order_by(desc(AuditLog.timestamp)).all()
    
    def log_action(self, user_id: str, action: str, resource_type: str = None, 
                   resource_id: UUID = None, details: Dict = None, **kwargs) -> AuditLog:
        """Log an action to the audit trail."""
        return self.create(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            **kwargs
        )
