"""
Dynamic Supervisor - Updated to use 'meta' column instead of 'metadata'
"""

import asyncio
import time
import re
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum

from sqlalchemy import select
from backend.models.task import Task, AgentMessage, AgentRole, TaskStatus
from backend.core.database import AsyncSessionLocal
from backend.agents.planner_agent import PlannerAgent
from backend.agents.knowledge_agent import KnowledgeAgent
from backend.agents.retrieval_agent import RetrievalAgent
from backend.agents.coder_agent import CoderAgent
from backend.agents.validator_agent import ValidatorAgent

class WorkflowState(str, Enum):
    PLANNING = "planning"
    KNOWLEDGE_GATHERING = "knowledge_gathering"
    RESEARCH = "research"
    CODING = "coding"
    VALIDATION = "validation"
    REFINEMENT = "refinement"
    COMPLETED = "completed"
    FAILED = "failed"

class AgentResponse:
    def __init__(self, content: str, success: bool = True, metadata: Dict = None):
        self.content = content
        self.success = success
        self.metadata = metadata or {}
        self.quality_score = self.metadata.get("quality_score", 0.5)
        self.response_time = self.metadata.get("response_time", 0.0)

class DynamicSupervisor:
    """Intelligent supervisor that dynamically routes between agents based on context"""

    def __init__(self):
        self.agents = {
            AgentRole.PLANNER: PlannerAgent(),
            AgentRole.KNOWLEDGE: KnowledgeAgent(),
            AgentRole.RETRIEVAL: RetrievalAgent(),
            AgentRole.CODER: CoderAgent(),
            AgentRole.VALIDATOR: ValidatorAgent()
        }
        self.performance_tracker = {}
        self.retry_limits = {
            AgentRole.PLANNER: 2,
            AgentRole.CODER: 5,
            AgentRole.VALIDATOR: 1
        }

    async def execute_workflow(
        self,
        task_id: str,
        prompt: str,
        context: Dict[str, Any],
        progress_callback: Optional[Callable] = None,
        agent_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """Execute the dynamic workflow with intelligent routing"""
        
        workflow_context = {
            "task_id": task_id,
            "original_prompt": prompt,
            "user_context": context,
            "state": WorkflowState.KNOWLEDGE_GATHERING,
            "plan": None,
            "knowledge": None,
            "research_data": None,
            "generated_code": None,
            "validation_result": None,
            "best_code": None,
            "best_score": -1.0,
            "retry_counts": {role: 0 for role in self.retry_limits},
            "agent_history": []
        }

        try:
            while workflow_context["state"] not in [WorkflowState.COMPLETED, WorkflowState.FAILED]:
                # Update progress
                progress = self._calculate_progress(workflow_context["state"])
                if progress_callback:
                    await progress_callback(progress, f"State: {workflow_context['state'].value}")

                # Route to next agent
                next_agent = self._route_next_agent(workflow_context)
                if not next_agent:
                    break

                # Notify frontend that an agent is starting
                if agent_callback:
                    await agent_callback(next_agent, "active", f"Starting {next_agent.value}...")

                # Execute agent
                response = await self._execute_agent(next_agent, workflow_context)

                # Notify frontend of the agent's result
                if agent_callback:
                    await agent_callback(next_agent, "completed" if response.success else "error", response.content)

                # Process response and update state
                self._update_workflow_state(workflow_context, next_agent, response)

                # Store agent message in database
                await self._store_agent_message(task_id, next_agent, response)

            # Return final results
            return self._prepare_final_result(workflow_context)

        except Exception as e:
            workflow_context["state"] = WorkflowState.FAILED
            return {
                "success": False,
                "error": str(e),
                "code": None,
                "quality_score": 0.0
            }

    def _route_next_agent(self, context: Dict[str, Any]) -> Optional[AgentRole]:
        """Intelligently determine the next agent based on current state and context"""
        current_state = context["state"]

        if current_state == WorkflowState.KNOWLEDGE_GATHERING:
            return AgentRole.KNOWLEDGE

        elif current_state == WorkflowState.RESEARCH:
            if self._needs_external_research(context):
                return AgentRole.RETRIEVAL
            else:
                # If no research is needed, skip directly to planning
                context["state"] = WorkflowState.PLANNING
                return AgentRole.PLANNER

        elif current_state == WorkflowState.PLANNING:
            return AgentRole.PLANNER

        elif current_state == WorkflowState.CODING:
            return AgentRole.CODER

        elif current_state == WorkflowState.VALIDATION:
            return AgentRole.VALIDATOR

        elif current_state == WorkflowState.REFINEMENT:
            if context["retry_counts"][AgentRole.CODER] < self.retry_limits[AgentRole.CODER]:
                context["retry_counts"][AgentRole.CODER] += 1
                return AgentRole.CODER
            else:
                # Retry limit hit, force failure
                context["state"] = WorkflowState.FAILED
                context["validation_result"] = "Workflow failed: Coder agent hit maximum refinement retries."
                return None

        return None

    def _needs_external_research(self, context: Dict[str, Any]) -> bool:
        """Determine if external research is needed"""
        prompt = context["original_prompt"].lower()
        research_indicators = [
            "specific model", "datasheet", "protocol", "communication",
            "modbus", "profinet", "ethernet/ip", "specifications"
        ]
        return any(indicator in prompt for indicator in research_indicators)

    async def _execute_agent(self, agent_role: AgentRole, context: Dict[str, Any]) -> AgentResponse:
        """Execute a specific agent with context"""
        agent = self.agents[agent_role]
        start_time = time.time()

        try:
            agent_input = self._prepare_agent_input(agent_role, context)

            if agent_role == AgentRole.PLANNER:
                # Combine knowledge and research for the planner
                knowledge_context = []
                if context.get("knowledge"):
                    knowledge_context.append(f"INTERNAL KNOWLEDGE:\n{context['knowledge']}")
                if context.get("research_data"):
                    knowledge_context.append(f"EXTERNAL RESEARCH:\n{context['research_data']}")
                
                full_knowledge = "\n\n---\n\n".join(knowledge_context)
                response = await agent.create_plan(agent_input, full_knowledge if full_knowledge else None)
            elif agent_role == AgentRole.KNOWLEDGE:
                response = await agent.query_knowledge(agent_input)
            elif agent_role == AgentRole.RETRIEVAL:
                response = await agent.search_external(agent_input)
            elif agent_role == AgentRole.CODER:
                if context["state"] == WorkflowState.REFINEMENT:
                    # This is a refinement call, use refine_code
                    response = await agent.refine_code(
                        original_code=context["generated_code"],
                        feedback="The previous code failed validation. Please review the report and fix the errors.",
                        validation_report=context["validation_result"]
                    )
                else:
                    # This is the initial generation call
                    response = await agent.generate_code(
                        context["plan"],
                        context.get("knowledge"),
                        context.get("research_data")
                    )
            elif agent_role == AgentRole.VALIDATOR:
                # Combine knowledge and research for the validator
                knowledge_context = []
                if context.get("knowledge"):
                    knowledge_context.append(f"INTERNAL KNOWLEDGE:\n{context['knowledge']}")
                if context.get("research_data"):
                    knowledge_context.append(f"EXTERNAL RESEARCH:\n{context['research_data']}")
                full_knowledge = "\n\n---\n\n".join(knowledge_context)
                response = await agent.validate_code(context["generated_code"], full_knowledge if full_knowledge else None, context.get("plan"))
            else:
                raise ValueError(f"Unknown agent role: {agent_role}")

            response_time = time.time() - start_time
            quality_score = self._evaluate_response_quality(agent_role, response)

            return AgentResponse(
                content=response,
                success=True,
                metadata={
                    "response_time": response_time,
                    "quality_score": quality_score,
                    "agent_role": agent_role.value
                }
            )

        except Exception as e:
            response_time = time.time() - start_time
            return AgentResponse(
                content=f"Agent error: {str(e)}",
                success=False,
                metadata={
                    "response_time": response_time,
                    "quality_score": 0.0,
                    "agent_role": agent_role.value,
                    "error": str(e)
                }
            )

    def _prepare_agent_input(self, agent_role: AgentRole, context: Dict[str, Any]) -> str:
        """Prepare input for specific agent based on workflow context"""
        if agent_role == AgentRole.PLANNER:
            return context["original_prompt"]
        elif agent_role == AgentRole.KNOWLEDGE:
            return f"IEC 61131-3 requirements for: {context['original_prompt']}"
        elif agent_role == AgentRole.RETRIEVAL:
            return f"Hardware specifications for: {context['original_prompt']}"
        elif agent_role == AgentRole.CODER:
            return context["plan"]
        elif agent_role == AgentRole.VALIDATOR:
            return context["generated_code"]
        
        return context["original_prompt"]

    def _update_workflow_state(self, context: Dict[str, Any], agent_role: AgentRole, response: AgentResponse):
        """Update workflow state based on agent response"""
        context["agent_history"].append({
            "agent": agent_role.value,
            "success": response.success,
            "quality": response.quality_score,
            "timestamp": datetime.now().isoformat()
        })

        if not response.success:
            if agent_role in self.retry_limits and context["retry_counts"][agent_role] < self.retry_limits[agent_role]:
                context["retry_counts"][agent_role] += 1
                return
            else:
                context["state"] = WorkflowState.FAILED
                return

        # Update state based on successful agent execution
        if agent_role == AgentRole.KNOWLEDGE:
            context["knowledge"] = response.content
            context["state"] = WorkflowState.RESEARCH

        elif agent_role == AgentRole.RETRIEVAL:
            context["research_data"] = response.content
            context["state"] = WorkflowState.PLANNING

        elif agent_role == AgentRole.PLANNER:
            context["plan"] = response.content
            context["state"] = WorkflowState.CODING

        elif agent_role == AgentRole.CODER:
            context["generated_code"] = response.content
            # The coder agent is responsible for extracting and cleaning.
            # We just check if the result looks like a valid program.
            if response.content and "PROGRAM" in response.content.upper() and "END_PROGRAM" in response.content.upper():
                context["state"] = WorkflowState.VALIDATION
            else:
                # If coder returns empty or invalid string, go to refinement/retry
                context["state"] = WorkflowState.REFINEMENT

        elif agent_role == AgentRole.VALIDATOR:
            context["validation_result"] = response.content
            
            # Track the best code based on validator score
            current_score = response.quality_score
            if current_score > context["best_score"]:
                context["best_score"] = current_score
                context["best_code"] = context["generated_code"]
                
            if "VALIDATION PASSED" in response.content or ("successful" in response.content.lower() or "passed" in response.content.lower()):
                context["state"] = WorkflowState.COMPLETED
            else:
                context["state"] = WorkflowState.REFINEMENT

    def _evaluate_response_quality(self, agent_role: AgentRole, response: str) -> float:
        """Evaluate the quality of an agent response"""
        import re
        if not response or len(response.strip()) < 10:
            return 0.1

        if agent_role == AgentRole.VALIDATOR:
            # Try to parse the numeric score from the validator's report string
            match = re.search(r"Overall Quality Score:\s*([0-9.]+)/1.0", response)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    pass  # Fallback to pattern matching if parsing fails

        quality_patterns = {
            AgentRole.PLANNER: ['step', 'plan', 'implementation', 'variable', 'logic'],
            AgentRole.KNOWLEDGE: ['IEC', '61131-3', 'standard', 'rule', 'syntax'],
            AgentRole.RETRIEVAL: ['specification', 'datasheet', 'model', 'protocol'],
            AgentRole.CODER: ['PROGRAM', 'VAR', 'BEGIN', 'END_PROGRAM', ':='],
            AgentRole.VALIDATOR: ['compilation', 'successful', 'error', 'warning', 'passed']
        }

        patterns = quality_patterns.get(agent_role, [])
        matches = sum(1 for pattern in patterns if pattern.lower() in response.lower())
        return min(1.0, matches / max(1, len(patterns)) + 0.2)

    async def _store_agent_message(self, task_id: str, agent_role: AgentRole, response: AgentResponse):
        """Store agent message in database"""
        async with AsyncSessionLocal() as db:
            try:
                message = AgentMessage(
                    task_id=int(task_id),
                    agent_role=agent_role,
                    content=response.content,
                    meta=response.metadata  # FIXED: Changed from metadata to meta
                )
                db.add(message)
                await db.commit()
            except Exception as e:
                print(f"Error storing agent message: {e}")

    def _calculate_progress(self, state: WorkflowState) -> float:
        """Calculate workflow progress based on current state"""
        progress_map = {
            WorkflowState.KNOWLEDGE_GATHERING: 0.1,
            WorkflowState.RESEARCH: 0.25,
            WorkflowState.PLANNING: 0.4,
            WorkflowState.CODING: 0.7,
            WorkflowState.VALIDATION: 0.9,
            WorkflowState.REFINEMENT: 0.8,
            WorkflowState.COMPLETED: 1.0,
            WorkflowState.FAILED: 1.0
        }
        return progress_map.get(state, 0.0)

    def _prepare_final_result(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare the final workflow result"""
        success = context["state"] == WorkflowState.COMPLETED
        
        # Use the best score from the validator as the primary quality score
        quality_score = context.get("best_score", 0.0)
        if quality_score < 0: # if it was never set
            # Calculate a score for failed tasks based on progress
            agent_scores = [h["quality"] for h in context["agent_history"] if h["success"]]
            avg_agent_score = sum(agent_scores) / len(agent_scores) if agent_scores else 0.0
            quality_score = avg_agent_score * 0.5  # Max 0.5 score for failed tasks

        # Return the best code found during the workflow
        final_code = context.get("best_code")
        if not final_code:
            # If no best_code was ever set, it means no version was good. Return the last attempt.
            final_code = context.get("generated_code", "")
        return {
            "success": success,
            "code": final_code,
            "quality_score": quality_score,
            "plan": context.get("plan"),
            "validation_result": context.get("validation_result"),
            "agent_history": context["agent_history"],
            "error": None if success else "Workflow failed. Review validation report and logs."
        }

    async def process_feedback(
        self,
        task_id: str,
        original_code: str,
        feedback: str,
        validator_report: str
    ) -> Dict[str, Any]:
        """Process user feedback for iterative improvement by revising the plan first."""
        try:
            async with AsyncSessionLocal() as db:
                # 1. Fetch the original plan from the database
                result = await db.execute(
                    select(AgentMessage).where(
                        AgentMessage.task_id == int(task_id),
                        AgentMessage.agent_role == AgentRole.PLANNER
                    ).order_by(AgentMessage.timestamp.desc()).limit(1)
                )
                latest_plan_message = result.scalars().first()
                if not latest_plan_message:
                    return {"success": False, "error": "Original plan not found for this task."}
                original_plan = latest_plan_message.content

            # 2. Revise the plan
            planner = self.agents[AgentRole.PLANNER]
            await self._store_agent_message(task_id, AgentRole.SUPERVISOR, AgentResponse(content=f"Revising plan based on user feedback: {feedback}"))
            
            revision_context = {"user_feedback": feedback, "previous_code": original_code}
            revised_plan = await planner.revise_plan(original_plan, feedback, revision_context)
            await self._store_agent_message(task_id, AgentRole.PLANNER, AgentResponse(content=revised_plan, metadata={"source": "feedback_revision"}))

            # 3. Generate new code from the revised plan
            coder = self.agents[AgentRole.CODER]
            await self._store_agent_message(task_id, AgentRole.SUPERVISOR, AgentResponse(content="Generating new code from revised plan..."))
            new_code = await coder.generate_code(plan=revised_plan)
            await self._store_agent_message(task_id, AgentRole.CODER, AgentResponse(content=new_code, metadata={"source": "feedback_generation"}))

            # 4. Validate the new code
            validator = self.agents[AgentRole.VALIDATOR]
            await self._store_agent_message(task_id, AgentRole.SUPERVISOR, AgentResponse(content="Validating new code..."))
            validation_result = await validator.validate_code(new_code)
            
            quality_score = self._evaluate_response_quality(AgentRole.VALIDATOR, validation_result)
            success = "successful" in validation_result.lower() or "passed" in validation_result.lower()

            return {
                "success": success,
                "code": new_code,
                "quality_score": quality_score,
                "validation_result": validation_result,
                "error": None if success else "Refinement failed validation"
            }
        except Exception as e:
            return {
                "success": False,
                "code": original_code,
                "quality_score": 0.0,
                "error": f"Feedback processing error: {str(e)}"
            }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics for all agents"""
        metrics = {}
        
        for role, agent in self.agents.items():
            metrics[role.value] = {
                "total_calls": self.performance_tracker.get(f"{role.value}_calls", 0),
                "avg_response_time": self.performance_tracker.get(f"{role.value}_avg_time", 0.0),
                "success_rate": self.performance_tracker.get(f"{role.value}_success_rate", 1.0),
                "retry_limit": self.retry_limits.get(role, 1)
            }
        
        return metrics

    def reset_performance_metrics(self):
        """Reset all performance tracking metrics"""
        self.performance_tracker.clear()

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all agents"""
        health_status = {
            "supervisor": "healthy",
            "agents": {},
            "timestamp": datetime.now().isoformat()
        }

        for role, agent in self.agents.items():
            try:
                # Simple health check - try to call a basic method
                if hasattr(agent, 'health_check'):
                    agent_health = await agent.health_check()
                else:
                    agent_health = "healthy"  # Assume healthy if no health check method
                
                health_status["agents"][role.value] = agent_health
            except Exception as e:
                health_status["agents"][role.value] = f"error: {str(e)}"

        # Check if any agent is unhealthy
        if any("error" in status for status in health_status["agents"].values()):
            health_status["supervisor"] = "degraded"

        return health_status

    def update_agent_config(self, agent_role: AgentRole, config: Dict[str, Any]):
        """Update configuration for a specific agent"""
        agent = self.agents.get(agent_role)
        if agent and hasattr(agent, 'update_config'):
            agent.update_config(config)
        else:
            print(f"Agent {agent_role.value} does not support configuration updates")

    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get statistics about workflow execution"""
        return {
            "states_defined": len(WorkflowState),
            "agents_configured": len(self.agents),
            "retry_limits": self.retry_limits,
            "performance_metrics": self.get_performance_metrics()
        }