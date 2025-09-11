"""Core orchestrator for managing agent workflows."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from langchain.schema import BaseMessage
from langgraph import StateGraph, END
from langgraph.graph import MessageGraph

from models.schemas import (
    AgentRole, AgentTask, AgentMessage, TaskStatus, WorkflowState,
    UserRequirement, TaskPlan, GeneratedCode, ValidationResult
)
from agents.base_agent import BaseAgent


class WorkflowOrchestrator:
    """Orchestrates multi-agent workflows for PLC code generation."""
    
    def __init__(self):
        self.agents: Dict[AgentRole, BaseAgent] = {}
        self.active_workflows: Dict[UUID, WorkflowState] = {}
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self.logger = logging.getLogger("orchestrator")
        self.is_running = False
        
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the orchestrator."""
        self.agents[agent.role] = agent
        self.logger.info(f"Registered agent: {agent.role.value} ({agent.name})")
    
    async def start(self):
        """Start the orchestrator and begin processing workflows."""
        self.is_running = True
        self.logger.info("Starting workflow orchestrator")
        
        # Start background tasks
        asyncio.create_task(self._process_messages())
        asyncio.create_task(self._process_tasks())
        asyncio.create_task(self._monitor_workflows())
    
    async def stop(self):
        """Stop the orchestrator."""
        self.is_running = False
        self.logger.info("Stopping workflow orchestrator")
    
    async def create_workflow(self, requirement: UserRequirement) -> UUID:
        """Create a new workflow for a user requirement."""
        workflow_id = uuid4()
        
        # Define the standard PLC code generation workflow
        workflow_steps = [
            {"agent": AgentRole.RETRIEVAL, "task": "retrieve_knowledge", "timeout": 60},
            {"agent": AgentRole.PLANNER, "task": "create_plan", "timeout": 120},
            {"agent": AgentRole.GENERATOR, "task": "generate_code", "timeout": 300},
            {"agent": AgentRole.VALIDATOR, "task": "validate_code", "timeout": 180},
            {"agent": AgentRole.SIMULATOR, "task": "simulate_code", "timeout": 240}
        ]
        
        workflow_state = WorkflowState(
            id=workflow_id,
            requirement_id=requirement.id,
            total_steps=len(workflow_steps),
            state_data={
                "requirement": requirement.dict(),
                "workflow_steps": workflow_steps,
                "current_step_data": {}
            }
        )
        
        self.active_workflows[workflow_id] = workflow_state
        self.logger.info(f"Created workflow {workflow_id} for requirement {requirement.id}")
        
        # Start the workflow
        await self._execute_workflow(workflow_id)
        
        return workflow_id
    
    async def _execute_workflow(self, workflow_id: UUID):
        """Execute a workflow step by step."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            self.logger.error(f"Workflow {workflow_id} not found")
            return
        
        workflow_steps = workflow.state_data["workflow_steps"]
        
        while workflow.current_step < len(workflow_steps):
            step = workflow_steps[workflow.current_step]
            agent_role = step["agent"]
            task_type = step["task"]
            timeout = step.get("timeout", 300)
            
            self.logger.info(f"Executing step {workflow.current_step + 1}/{len(workflow_steps)}: {task_type}")
            
            # Create task for the agent
            task = AgentTask(
                agent_role=agent_role,
                task_type=task_type,
                input_data={
                    "workflow_id": workflow_id,
                    "requirement": workflow.state_data["requirement"],
                    "previous_results": workflow.state_data.get("current_step_data", {})
                },
                timeout=timeout
            )
            
            # Execute the task
            try:
                result = await self._execute_agent_task(task)
                
                if result.status == TaskStatus.COMPLETED:
                    # Store result and move to next step
                    workflow.state_data["current_step_data"][task_type] = result.result
                    workflow.completed_tasks.append(result.id)
                    workflow.current_step += 1
                    workflow.updated_at = datetime.utcnow()
                    
                    self.logger.info(f"Step {workflow.current_step}/{len(workflow_steps)} completed")
                    
                elif result.status == TaskStatus.FAILED:
                    # Handle failure - try debugging or fail the workflow
                    workflow.failed_tasks.append(result.id)
                    
                    if await self._handle_task_failure(workflow_id, result):
                        # Retry the step
                        continue
                    else:
                        # Fail the workflow
                        self.logger.error(f"Workflow {workflow_id} failed at step {workflow.current_step + 1}")
                        break
                        
            except Exception as e:
                self.logger.error(f"Error executing workflow step: {str(e)}")
                break
        
        # Workflow completed
        if workflow.current_step >= len(workflow_steps):
            self.logger.info(f"Workflow {workflow_id} completed successfully")
            await self._finalize_workflow(workflow_id)
    
    async def _execute_agent_task(self, task: AgentTask) -> AgentTask:
        """Execute a task using the appropriate agent."""
        agent = self.agents.get(task.agent_role)
        if not agent:
            raise ValueError(f"Agent {task.agent_role.value} not registered")
        
        # Add task to queue and wait for completion
        await self.task_queue.put(task)
        
        # Wait for task completion with timeout
        timeout = task.timeout
        start_time = datetime.utcnow()
        
        while task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
            if (datetime.utcnow() - start_time).total_seconds() > timeout:
                task.status = TaskStatus.FAILED
                task.error = "Task timeout"
                break
            
            await asyncio.sleep(1)  # Check every second
        
        return task
    
    async def _handle_task_failure(self, workflow_id: UUID, failed_task: AgentTask) -> bool:
        """Handle task failure by attempting debugging/recovery."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return False
        
        # Check if we have a debugger agent
        debugger = self.agents.get(AgentRole.DEBUGGER)
        if not debugger:
            return False
        
        # Create debugging task
        debug_task = AgentTask(
            agent_role=AgentRole.DEBUGGER,
            task_type="debug_failure",
            input_data={
                "failed_task": failed_task.dict(),
                "workflow_context": workflow.state_data
            }
        )
        
        try:
            debug_result = await self._execute_agent_task(debug_task)
            
            if debug_result.status == TaskStatus.COMPLETED:
                # Apply suggested fixes and retry
                fixes = debug_result.result.get("suggested_fixes", [])
                if fixes:
                    self.logger.info(f"Applying {len(fixes)} fixes for failed task")
                    # Apply fixes to workflow state
                    workflow.state_data["debug_fixes"] = fixes
                    return True
            
        except Exception as e:
            self.logger.error(f"Debugging failed: {str(e)}")
        
        return False
    
    async def _finalize_workflow(self, workflow_id: UUID):
        """Finalize a completed workflow."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return
        
        # Extract final results
        step_data = workflow.state_data.get("current_step_data", {})
        
        # Create final output
        final_result = {
            "workflow_id": workflow_id,
            "requirement_id": workflow.requirement_id,
            "generated_code": step_data.get("generate_code"),
            "validation_results": step_data.get("validate_code"),
            "simulation_results": step_data.get("simulate_code"),
            "completed_at": datetime.utcnow(),
            "total_duration": (datetime.utcnow() - workflow.created_at).total_seconds()
        }
        
        # Store results (would typically go to database)
        workflow.state_data["final_result"] = final_result
        
        self.logger.info(f"Workflow {workflow_id} finalized with results")
    
    async def _process_messages(self):
        """Background task to process inter-agent messages."""
        while self.is_running:
            try:
                # Get message from queue (with timeout)
                message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                
                # Route message to appropriate agent
                receiver_agent = self.agents.get(message.receiver)
                if receiver_agent:
                    await receiver_agent.receive_message(message)
                else:
                    self.logger.warning(f"No agent found for role: {message.receiver.value}")
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing message: {str(e)}")
    
    async def _process_tasks(self):
        """Background task to process agent tasks."""
        while self.is_running:
            try:
                # Get task from queue (with timeout)
                task = await asyncio.wait_for(self.task_queue.get(), timeout=1.0)
                
                # Execute task with appropriate agent
                agent = self.agents.get(task.agent_role)
                if agent:
                    # Execute task in background
                    asyncio.create_task(agent.execute_task(task))
                else:
                    task.status = TaskStatus.FAILED
                    task.error = f"No agent found for role: {task.agent_role.value}"
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"Error processing task: {str(e)}")
    
    async def _monitor_workflows(self):
        """Background task to monitor workflow health and timeouts."""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                
                for workflow_id, workflow in list(self.active_workflows.items()):
                    # Check for stalled workflows
                    if (current_time - workflow.updated_at).total_seconds() > 600:  # 10 minutes
                        self.logger.warning(f"Workflow {workflow_id} appears stalled")
                        # Could implement recovery logic here
                    
                    # Clean up completed workflows after 1 hour
                    if workflow.current_step >= workflow.total_steps:
                        if (current_time - workflow.updated_at).total_seconds() > 3600:
                            del self.active_workflows[workflow_id]
                            self.logger.info(f"Cleaned up completed workflow {workflow_id}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error monitoring workflows: {str(e)}")
    
    def get_workflow_status(self, workflow_id: UUID) -> Optional[Dict[str, Any]]:
        """Get the current status of a workflow."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            return None
        
        return {
            "id": workflow_id,
            "requirement_id": workflow.requirement_id,
            "current_step": workflow.current_step,
            "total_steps": workflow.total_steps,
            "progress": (workflow.current_step / workflow.total_steps) * 100,
            "active_agents": workflow.active_agents,
            "completed_tasks": len(workflow.completed_tasks),
            "failed_tasks": len(workflow.failed_tasks),
            "created_at": workflow.created_at,
            "updated_at": workflow.updated_at
        }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        return {
            "is_running": self.is_running,
            "registered_agents": list(self.agents.keys()),
            "active_workflows": len(self.active_workflows),
            "message_queue_size": self.message_queue.qsize(),
            "task_queue_size": self.task_queue.qsize()
        }
