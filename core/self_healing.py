"""Self-healing orchestrator with deployment policies and automated recovery."""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
from uuid import UUID, uuid4

from core.orchestrator import WorkflowOrchestrator
from agents.monitor_agent import MonitorAgent
from agents.debugger_agent import DebuggerAgent
from models.schemas import AgentRole, TelemetryData


class RecoveryAction(str, Enum):
    """Types of recovery actions."""
    RESTART_AGENT = "restart_agent"
    ROLLBACK_CODE = "rollback_code"
    SCALE_RESOURCES = "scale_resources"
    FAILOVER = "failover"
    MANUAL_INTERVENTION = "manual_intervention"
    PATCH_DEPLOYMENT = "patch_deployment"


class DeploymentStage(str, Enum):
    """Deployment stages for canary/staged deployment."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    CANARY = "canary"
    PRODUCTION = "production"


@dataclass
class RecoveryPolicy:
    """Policy for automated recovery actions."""
    name: str
    trigger_conditions: List[str]
    recovery_actions: List[RecoveryAction]
    max_attempts: int
    cooldown_period: int  # seconds
    requires_approval: bool
    severity_threshold: str


@dataclass
class DeploymentPolicy:
    """Policy for staged deployment and rollback."""
    name: str
    stages: List[DeploymentStage]
    stage_duration: Dict[DeploymentStage, int]  # seconds
    success_criteria: Dict[str, Any]
    rollback_triggers: List[str]
    auto_promote: bool


class SelfHealingOrchestrator:
    """Self-healing orchestrator with automated recovery and deployment policies."""
    
    def __init__(self, workflow_orchestrator: WorkflowOrchestrator):
        self.workflow_orchestrator = workflow_orchestrator
        self.logger = logging.getLogger("self_healing")
        
        # Recovery tracking
        self.recovery_attempts = {}
        self.active_recoveries = {}
        
        # Deployment tracking
        self.active_deployments = {}
        self.deployment_history = []
        
        # Recovery policies
        self.recovery_policies = [
            RecoveryPolicy(
                name="agent_failure_recovery",
                trigger_conditions=["agent_timeout", "agent_error", "agent_crash"],
                recovery_actions=[RecoveryAction.RESTART_AGENT],
                max_attempts=3,
                cooldown_period=60,
                requires_approval=False,
                severity_threshold="error"
            ),
            RecoveryPolicy(
                name="validation_failure_recovery",
                trigger_conditions=["validation_failed", "syntax_error"],
                recovery_actions=[RecoveryAction.PATCH_DEPLOYMENT],
                max_attempts=2,
                cooldown_period=30,
                requires_approval=False,
                severity_threshold="warning"
            ),
            RecoveryPolicy(
                name="critical_system_failure",
                trigger_conditions=["safety_fault", "critical_error", "system_crash"],
                recovery_actions=[RecoveryAction.ROLLBACK_CODE, RecoveryAction.FAILOVER],
                max_attempts=1,
                cooldown_period=300,
                requires_approval=True,
                severity_threshold="critical"
            ),
            RecoveryPolicy(
                name="performance_degradation",
                trigger_conditions=["high_cycle_time", "memory_leak", "cpu_overload"],
                recovery_actions=[RecoveryAction.SCALE_RESOURCES, RecoveryAction.RESTART_AGENT],
                max_attempts=2,
                cooldown_period=120,
                requires_approval=False,
                severity_threshold="warning"
            )
        ]
        
        # Deployment policies
        self.deployment_policies = [
            DeploymentPolicy(
                name="standard_deployment",
                stages=[DeploymentStage.DEVELOPMENT, DeploymentStage.STAGING, DeploymentStage.PRODUCTION],
                stage_duration={
                    DeploymentStage.DEVELOPMENT: 300,  # 5 minutes
                    DeploymentStage.STAGING: 1800,     # 30 minutes
                    DeploymentStage.PRODUCTION: 0      # Immediate
                },
                success_criteria={
                    "error_rate": 0.01,
                    "cycle_time_ms": 100,
                    "validation_passed": True
                },
                rollback_triggers=["critical_error", "safety_fault", "validation_failed"],
                auto_promote=True
            ),
            DeploymentPolicy(
                name="safety_critical_deployment",
                stages=[DeploymentStage.DEVELOPMENT, DeploymentStage.STAGING, DeploymentStage.CANARY, DeploymentStage.PRODUCTION],
                stage_duration={
                    DeploymentStage.DEVELOPMENT: 600,   # 10 minutes
                    DeploymentStage.STAGING: 3600,      # 1 hour
                    DeploymentStage.CANARY: 7200,       # 2 hours
                    DeploymentStage.PRODUCTION: 0
                },
                success_criteria={
                    "error_rate": 0.001,
                    "cycle_time_ms": 50,
                    "validation_passed": True,
                    "safety_tests_passed": True
                },
                rollback_triggers=["any_error", "safety_fault", "performance_degradation"],
                auto_promote=False  # Requires manual approval
            )
        ]
        
        # Monitoring integration
        self.monitor_agent = None
        self.debugger_agent = None
        
        # Self-healing enabled flag
        self.self_healing_enabled = True
        
        # Start background monitoring
        asyncio.create_task(self._monitoring_loop())
    
    async def start(self):
        """Start the self-healing orchestrator."""
        self.logger.info("Starting self-healing orchestrator")
        
        # Initialize monitor and debugger agents
        self.monitor_agent = MonitorAgent()
        self.debugger_agent = DebuggerAgent()
        
        # Register with workflow orchestrator
        self.workflow_orchestrator.register_agent(self.monitor_agent)
        self.workflow_orchestrator.register_agent(self.debugger_agent)
        
        self.logger.info("Self-healing orchestrator started successfully")
    
    async def deploy_code(self, code_version_id: UUID, deployment_policy: str = "standard_deployment") -> Dict[str, Any]:
        """Deploy code using staged deployment with self-healing."""
        
        policy = next((p for p in self.deployment_policies if p.name == deployment_policy), None)
        if not policy:
            raise ValueError(f"Unknown deployment policy: {deployment_policy}")
        
        deployment_id = uuid4()
        
        deployment = {
            "id": deployment_id,
            "code_version_id": code_version_id,
            "policy": policy,
            "current_stage": policy.stages[0],
            "stage_index": 0,
            "started_at": datetime.utcnow(),
            "status": "deploying",
            "stage_history": [],
            "health_checks": []
        }
        
        self.active_deployments[deployment_id] = deployment
        
        # Start deployment process
        asyncio.create_task(self._execute_deployment(deployment_id))
        
        return {
            "deployment_id": deployment_id,
            "policy_name": deployment_policy,
            "stages": [stage.value for stage in policy.stages],
            "estimated_duration": sum(policy.stage_duration.values()),
            "status": "started"
        }
    
    async def handle_system_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle system events and trigger recovery if needed."""
        
        event_type = event.get("type", "")
        severity = event.get("severity", "info")
        source = event.get("source", "")
        
        self.logger.info(f"Handling system event: {event_type} from {source} (severity: {severity})")
        
        # Find applicable recovery policies
        applicable_policies = []
        for policy in self.recovery_policies:
            if any(condition in event_type.lower() for condition in policy.trigger_conditions):
                if self._severity_meets_threshold(severity, policy.severity_threshold):
                    applicable_policies.append(policy)
        
        if not applicable_policies:
            return {"action": "no_recovery_needed", "event": event}
        
        # Execute recovery actions
        recovery_results = []
        for policy in applicable_policies:
            if self._can_attempt_recovery(policy.name):
                result = await self._execute_recovery_policy(policy, event)
                recovery_results.append(result)
        
        return {
            "event": event,
            "recovery_policies_triggered": len(applicable_policies),
            "recovery_results": recovery_results,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def rollback_deployment(self, deployment_id: UUID, reason: str) -> Dict[str, Any]:
        """Rollback a deployment to previous stable version."""
        
        deployment = self.active_deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment {deployment_id} not found")
        
        self.logger.warning(f"Rolling back deployment {deployment_id}: {reason}")
        
        # Mark deployment as failed
        deployment["status"] = "rolled_back"
        deployment["rollback_reason"] = reason
        deployment["rolled_back_at"] = datetime.utcnow()
        
        # Execute rollback actions
        rollback_result = await self._execute_rollback(deployment)
        
        # Move to deployment history
        self.deployment_history.append(deployment)
        del self.active_deployments[deployment_id]
        
        return {
            "deployment_id": deployment_id,
            "rollback_reason": reason,
            "rollback_result": rollback_result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health status."""
        
        if not self.monitor_agent:
            return {"status": "monitor_not_available"}
        
        # Get health report from monitor agent
        health_report = await self.monitor_agent._generate_health_report({})
        
        # Add self-healing status
        health_report["self_healing"] = {
            "enabled": self.self_healing_enabled,
            "active_recoveries": len(self.active_recoveries),
            "active_deployments": len(self.active_deployments),
            "recovery_policies": len(self.recovery_policies),
            "deployment_policies": len(self.deployment_policies)
        }
        
        return health_report
    
    async def _execute_deployment(self, deployment_id: UUID):
        """Execute staged deployment process."""
        
        deployment = self.active_deployments[deployment_id]
        policy = deployment["policy"]
        
        try:
            for stage_index, stage in enumerate(policy.stages):
                deployment["current_stage"] = stage
                deployment["stage_index"] = stage_index
                
                self.logger.info(f"Deploying to stage: {stage.value}")
                
                # Execute deployment to stage
                stage_result = await self._deploy_to_stage(deployment, stage)
                
                deployment["stage_history"].append({
                    "stage": stage.value,
                    "started_at": datetime.utcnow().isoformat(),
                    "result": stage_result,
                    "status": "completed" if stage_result["success"] else "failed"
                })
                
                if not stage_result["success"]:
                    # Stage failed - rollback
                    await self.rollback_deployment(deployment_id, f"Stage {stage.value} failed")
                    return
                
                # Wait for stage duration (except last stage)
                if stage_index < len(policy.stages) - 1:
                    stage_duration = policy.stage_duration.get(stage, 0)
                    if stage_duration > 0:
                        self.logger.info(f"Waiting {stage_duration}s for stage {stage.value} validation")
                        
                        # Monitor stage health during wait period
                        stage_healthy = await self._monitor_stage_health(deployment, stage, stage_duration)
                        
                        if not stage_healthy:
                            await self.rollback_deployment(deployment_id, f"Stage {stage.value} health check failed")
                            return
                
                # Check if auto-promotion is enabled and required
                if not policy.auto_promote and stage_index < len(policy.stages) - 1:
                    # Wait for manual approval
                    deployment["status"] = "waiting_approval"
                    self.logger.info(f"Waiting for manual approval to promote from {stage.value}")
                    # In a real implementation, this would wait for external approval
                    await asyncio.sleep(10)  # Simulate approval wait
            
            # Deployment completed successfully
            deployment["status"] = "completed"
            deployment["completed_at"] = datetime.utcnow()
            
            self.logger.info(f"Deployment {deployment_id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Deployment {deployment_id} failed: {str(e)}")
            await self.rollback_deployment(deployment_id, f"Deployment error: {str(e)}")
    
    async def _deploy_to_stage(self, deployment: Dict, stage: DeploymentStage) -> Dict[str, Any]:
        """Deploy code to a specific stage."""
        
        # Simulate deployment process
        self.logger.info(f"Deploying code version {deployment['code_version_id']} to {stage.value}")
        
        # In a real implementation, this would:
        # 1. Deploy code to target environment
        # 2. Run smoke tests
        # 3. Validate deployment
        # 4. Update routing/load balancer
        
        await asyncio.sleep(2)  # Simulate deployment time
        
        # Simulate deployment success/failure
        import random
        success = random.random() > 0.1  # 90% success rate
        
        return {
            "success": success,
            "stage": stage.value,
            "deployment_time": 2,
            "health_checks": ["smoke_test_passed", "connectivity_verified"] if success else ["smoke_test_failed"]
        }
    
    async def _monitor_stage_health(self, deployment: Dict, stage: DeploymentStage, duration: int) -> bool:
        """Monitor health of a deployment stage."""
        
        policy = deployment["policy"]
        
        # Monitor for the specified duration
        check_interval = min(30, duration // 10)  # Check every 30s or 10% of duration
        checks_passed = 0
        total_checks = duration // check_interval
        
        for i in range(total_checks):
            await asyncio.sleep(check_interval)
            
            # Simulate health check
            health_check = await self._perform_health_check(deployment, stage)
            
            deployment["health_checks"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "stage": stage.value,
                "check_index": i,
                "result": health_check
            })
            
            if health_check["healthy"]:
                checks_passed += 1
            else:
                # Check if this triggers rollback
                if any(trigger in health_check.get("issues", []) for trigger in policy.rollback_triggers):
                    self.logger.warning(f"Rollback trigger detected in stage {stage.value}: {health_check['issues']}")
                    return False
        
        # Require at least 80% of health checks to pass
        health_ratio = checks_passed / total_checks if total_checks > 0 else 1.0
        return health_ratio >= 0.8
    
    async def _perform_health_check(self, deployment: Dict, stage: DeploymentStage) -> Dict[str, Any]:
        """Perform health check for a deployment stage."""
        
        policy = deployment["policy"]
        
        # Simulate health metrics
        import random
        
        metrics = {
            "error_rate": random.uniform(0, 0.02),
            "cycle_time_ms": random.uniform(30, 120),
            "memory_usage": random.uniform(40, 90),
            "cpu_usage": random.uniform(20, 80)
        }
        
        # Check against success criteria
        issues = []
        healthy = True
        
        for criterion, threshold in policy.success_criteria.items():
            if criterion in metrics:
                if isinstance(threshold, (int, float)):
                    if metrics[criterion] > threshold:
                        issues.append(f"{criterion} ({metrics[criterion]}) exceeds threshold ({threshold})")
                        healthy = False
        
        return {
            "healthy": healthy,
            "metrics": metrics,
            "issues": issues,
            "stage": stage.value
        }
    
    async def _execute_recovery_policy(self, policy: RecoveryPolicy, event: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a recovery policy."""
        
        recovery_id = uuid4()
        
        recovery = {
            "id": recovery_id,
            "policy_name": policy.name,
            "event": event,
            "started_at": datetime.utcnow(),
            "status": "executing",
            "actions_completed": [],
            "actions_failed": []
        }
        
        self.active_recoveries[recovery_id] = recovery
        
        try:
            # Execute recovery actions in sequence
            for action in policy.recovery_actions:
                action_result = await self._execute_recovery_action(action, event)
                
                if action_result["success"]:
                    recovery["actions_completed"].append({
                        "action": action.value,
                        "result": action_result,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                else:
                    recovery["actions_failed"].append({
                        "action": action.value,
                        "result": action_result,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    # If action requires approval and failed, stop recovery
                    if policy.requires_approval:
                        break
            
            # Update recovery status
            recovery["status"] = "completed" if not recovery["actions_failed"] else "partial_failure"
            recovery["completed_at"] = datetime.utcnow()
            
            # Update recovery attempt counter
            self._update_recovery_attempts(policy.name)
            
            return recovery
            
        except Exception as e:
            recovery["status"] = "failed"
            recovery["error"] = str(e)
            recovery["completed_at"] = datetime.utcnow()
            
            self.logger.error(f"Recovery policy {policy.name} failed: {str(e)}")
            return recovery
        
        finally:
            # Remove from active recoveries after cooldown
            asyncio.create_task(self._cleanup_recovery(recovery_id, policy.cooldown_period))
    
    async def _execute_recovery_action(self, action: RecoveryAction, event: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific recovery action."""
        
        self.logger.info(f"Executing recovery action: {action.value}")
        
        try:
            if action == RecoveryAction.RESTART_AGENT:
                return await self._restart_agent(event)
            elif action == RecoveryAction.ROLLBACK_CODE:
                return await self._rollback_code(event)
            elif action == RecoveryAction.SCALE_RESOURCES:
                return await self._scale_resources(event)
            elif action == RecoveryAction.FAILOVER:
                return await self._failover(event)
            elif action == RecoveryAction.PATCH_DEPLOYMENT:
                return await self._patch_deployment(event)
            elif action == RecoveryAction.MANUAL_INTERVENTION:
                return await self._request_manual_intervention(event)
            else:
                return {"success": False, "error": f"Unknown recovery action: {action.value}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _restart_agent(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Restart a failed agent."""
        agent_role = event.get("agent_role", "")
        
        if agent_role:
            # In a real implementation, this would restart the specific agent
            self.logger.info(f"Restarting agent: {agent_role}")
            await asyncio.sleep(1)  # Simulate restart time
            
            return {
                "success": True,
                "action": "agent_restarted",
                "agent_role": agent_role,
                "restart_time": 1
            }
        
        return {"success": False, "error": "No agent role specified"}
    
    async def _rollback_code(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback to previous stable code version."""
        self.logger.info("Rolling back to previous stable version")
        
        # Simulate rollback process
        await asyncio.sleep(2)
        
        return {
            "success": True,
            "action": "code_rolled_back",
            "rollback_time": 2
        }
    
    async def _scale_resources(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Scale system resources."""
        self.logger.info("Scaling system resources")
        
        # Simulate resource scaling
        await asyncio.sleep(1)
        
        return {
            "success": True,
            "action": "resources_scaled",
            "scaling_time": 1
        }
    
    async def _failover(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Failover to backup system."""
        self.logger.info("Executing failover to backup system")
        
        # Simulate failover process
        await asyncio.sleep(3)
        
        return {
            "success": True,
            "action": "failover_completed",
            "failover_time": 3
        }
    
    async def _patch_deployment(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Apply automated patch to fix issues."""
        self.logger.info("Applying automated patch")
        
        if self.debugger_agent:
            # Use debugger agent to generate and apply fixes
            debug_result = await self.debugger_agent.process_task({
                "task_type": "fix_validation_errors",
                "input_data": {"event": event}
            })
            
            return {
                "success": True,
                "action": "patch_applied",
                "debug_result": debug_result
            }
        
        return {"success": False, "error": "Debugger agent not available"}
    
    async def _request_manual_intervention(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Request manual intervention."""
        self.logger.critical(f"Manual intervention required for event: {event}")
        
        # In a real implementation, this would:
        # 1. Send alerts to operations team
        # 2. Create incident tickets
        # 3. Escalate to on-call engineers
        
        return {
            "success": True,
            "action": "manual_intervention_requested",
            "escalation_level": "critical"
        }
    
    async def _execute_rollback(self, deployment: Dict) -> Dict[str, Any]:
        """Execute rollback actions for a deployment."""
        
        # Simulate rollback process
        self.logger.info(f"Executing rollback for deployment {deployment['id']}")
        
        rollback_actions = [
            "stop_new_deployments",
            "restore_previous_version",
            "update_routing",
            "verify_rollback"
        ]
        
        completed_actions = []
        
        for action in rollback_actions:
            await asyncio.sleep(0.5)  # Simulate action time
            completed_actions.append({
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                "success": True
            })
        
        return {
            "rollback_completed": True,
            "actions": completed_actions,
            "rollback_duration": len(rollback_actions) * 0.5
        }
    
    async def _monitoring_loop(self):
        """Background monitoring loop for self-healing."""
        
        while self.self_healing_enabled:
            try:
                # Check active deployments
                for deployment_id, deployment in list(self.active_deployments.items()):
                    if deployment["status"] == "deploying":
                        # Check if deployment is taking too long
                        elapsed = (datetime.utcnow() - deployment["started_at"]).total_seconds()
                        if elapsed > 3600:  # 1 hour timeout
                            await self.rollback_deployment(deployment_id, "Deployment timeout")
                
                # Clean up old recovery attempts
                current_time = datetime.utcnow()
                for policy_name in list(self.recovery_attempts.keys()):
                    attempts = self.recovery_attempts[policy_name]
                    # Remove attempts older than 1 hour
                    self.recovery_attempts[policy_name] = [
                        attempt for attempt in attempts 
                        if (current_time - attempt).total_seconds() < 3600
                    ]
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {str(e)}")
                await asyncio.sleep(30)
    
    async def _cleanup_recovery(self, recovery_id: UUID, cooldown_period: int):
        """Clean up recovery after cooldown period."""
        await asyncio.sleep(cooldown_period)
        
        if recovery_id in self.active_recoveries:
            del self.active_recoveries[recovery_id]
    
    def _can_attempt_recovery(self, policy_name: str) -> bool:
        """Check if recovery can be attempted based on policy limits."""
        
        policy = next((p for p in self.recovery_policies if p.name == policy_name), None)
        if not policy:
            return False
        
        # Check attempt count within cooldown period
        if policy_name not in self.recovery_attempts:
            self.recovery_attempts[policy_name] = []
        
        current_time = datetime.utcnow()
        recent_attempts = [
            attempt for attempt in self.recovery_attempts[policy_name]
            if (current_time - attempt).total_seconds() < policy.cooldown_period
        ]
        
        return len(recent_attempts) < policy.max_attempts
    
    def _update_recovery_attempts(self, policy_name: str):
        """Update recovery attempt counter."""
        if policy_name not in self.recovery_attempts:
            self.recovery_attempts[policy_name] = []
        
        self.recovery_attempts[policy_name].append(datetime.utcnow())
    
    def _severity_meets_threshold(self, event_severity: str, threshold_severity: str) -> bool:
        """Check if event severity meets policy threshold."""
        severity_levels = {"info": 1, "warning": 2, "error": 3, "critical": 4}
        
        event_level = severity_levels.get(event_severity.lower(), 1)
        threshold_level = severity_levels.get(threshold_severity.lower(), 1)
        
        return event_level >= threshold_level
