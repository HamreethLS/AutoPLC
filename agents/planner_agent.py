"""Planner agent for task decomposition and workflow planning."""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta

from agents.base_agent import LLMAgent
from models.schemas import AgentRole, AgentTask, TaskPlan, UserRequirement, PLCLanguage


class PlannerAgent(LLMAgent):
    """Agent responsible for decomposing requirements into structured task plans."""
    
    def __init__(self, llm=None):
        super().__init__(
            role=AgentRole.PLANNER,
            name="PLC Task Planner",
            description="Decomposes user requirements into structured, executable task plans",
            llm=llm
        )
        
        # Planning templates for different types of PLC tasks
        self.planning_templates = {
            "motor_control": {
                "steps": [
                    "Define input/output variables",
                    "Implement start/stop logic",
                    "Add safety interlocks",
                    "Include status feedback",
                    "Add error handling"
                ],
                "estimated_time": 180
            },
            "analog_processing": {
                "steps": [
                    "Define analog input variables",
                    "Implement scaling functions",
                    "Add filtering/averaging",
                    "Set alarm limits",
                    "Output processing"
                ],
                "estimated_time": 240
            },
            "sequence_control": {
                "steps": [
                    "Define sequence states",
                    "Implement state machine logic",
                    "Add transition conditions",
                    "Include manual overrides",
                    "Add sequence monitoring"
                ],
                "estimated_time": 300
            },
            "safety_function": {
                "steps": [
                    "Analyze safety requirements",
                    "Define safety inputs/outputs",
                    "Implement fail-safe logic",
                    "Add diagnostics",
                    "Validate safety integrity"
                ],
                "estimated_time": 420
            }
        }
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for the planner agent."""
        return """
You are a PLC Task Planning Agent specialized in decomposing complex automation requirements into structured, executable plans.

Your responsibilities:
1. Analyze user requirements and identify key components
2. Break down complex tasks into manageable subtasks
3. Determine optimal sequence and dependencies
4. Estimate time and resource requirements
5. Consider safety and compliance requirements
6. Plan validation and testing strategies

When creating plans:
- Follow IEC 61131-3 standards and best practices
- Consider safety integrity levels (SIL) requirements
- Break complex logic into modular components
- Plan for error handling and diagnostics
- Include testing and validation steps
- Consider maintenance and documentation needs

Planning principles:
- Start with safety-critical functions
- Use proven patterns and templates
- Plan for modularity and reusability
- Include comprehensive testing
- Consider operational requirements
- Plan for future modifications

Always create detailed, actionable plans that other agents can execute effectively.
"""
    
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process a planning task."""
        task_type = task.task_type
        input_data = task.input_data
        
        if task_type == "create_plan":
            return await self._create_plan(input_data)
        elif task_type == "refine_plan":
            return await self._refine_plan(input_data)
        elif task_type == "estimate_complexity":
            return await self._estimate_complexity(input_data)
        elif task_type == "validate_plan":
            return await self._validate_plan(input_data)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
    
    async def _create_plan(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a detailed task plan from requirements."""
        requirement = input_data.get("requirement", {})
        retrieved_knowledge = input_data.get("previous_results", {}).get("retrieve_knowledge", {})
        
        # Extract requirement details
        description = requirement.get("description", "")
        language = requirement.get("language", "st")
        safety_level = requirement.get("safety_level", 1)
        constraints = requirement.get("constraints", {})
        
        # Identify task type from description
        task_type = self._identify_task_type(description)
        
        # Get base template
        template = self.planning_templates.get(task_type, self.planning_templates["motor_control"])
        
        # Create detailed plan
        plan_steps = []
        
        # 1. Analysis and Design Phase
        plan_steps.extend([
            {
                "phase": "analysis",
                "step": "Analyze requirements",
                "description": "Parse and understand user requirements",
                "inputs": ["user_requirement", "domain_knowledge"],
                "outputs": ["requirement_analysis"],
                "estimated_time": 30,
                "agent": "planner"
            },
            {
                "phase": "analysis",
                "step": "Define system architecture",
                "description": "Define overall system structure and interfaces",
                "inputs": ["requirement_analysis"],
                "outputs": ["system_architecture"],
                "estimated_time": 45,
                "agent": "planner"
            }
        ])
        
        # 2. Code Generation Phase
        for i, step_desc in enumerate(template["steps"]):
            plan_steps.append({
                "phase": "generation",
                "step": f"Generate {step_desc.lower()}",
                "description": step_desc,
                "inputs": ["system_architecture", "domain_knowledge"],
                "outputs": [f"code_component_{i+1}"],
                "estimated_time": template["estimated_time"] // len(template["steps"]),
                "agent": "generator"
            })
        
        # 3. Validation Phase
        plan_steps.extend([
            {
                "phase": "validation",
                "step": "Syntax validation",
                "description": "Check code syntax and structure",
                "inputs": ["generated_code"],
                "outputs": ["syntax_validation_result"],
                "estimated_time": 30,
                "agent": "validator"
            },
            {
                "phase": "validation",
                "step": "Semantic validation",
                "description": "Validate code logic and semantics",
                "inputs": ["generated_code", "requirement_analysis"],
                "outputs": ["semantic_validation_result"],
                "estimated_time": 45,
                "agent": "validator"
            }
        ])
        
        # 4. Safety Validation (if required)
        if safety_level > 1:
            plan_steps.append({
                "phase": "safety",
                "step": "Safety validation",
                "description": f"Validate SIL {safety_level} safety requirements",
                "inputs": ["generated_code", "safety_requirements"],
                "outputs": ["safety_validation_result"],
                "estimated_time": 60 * safety_level,
                "agent": "validator"
            })
        
        # 5. Testing Phase
        plan_steps.extend([
            {
                "phase": "testing",
                "step": "Unit testing",
                "description": "Test individual code components",
                "inputs": ["generated_code", "test_scenarios"],
                "outputs": ["unit_test_results"],
                "estimated_time": 60,
                "agent": "simulator"
            },
            {
                "phase": "testing",
                "step": "Integration testing",
                "description": "Test complete system integration",
                "inputs": ["generated_code", "system_architecture"],
                "outputs": ["integration_test_results"],
                "estimated_time": 90,
                "agent": "simulator"
            }
        ])
        
        # Calculate total estimated time
        total_time = sum(step["estimated_time"] for step in plan_steps)
        
        # Create task plan
        task_plan = TaskPlan(
            requirement_id=requirement.get("id"),
            steps=plan_steps,
            estimated_duration=total_time
        )
        
        return {
            "task_plan": task_plan.dict(),
            "task_type": task_type,
            "total_steps": len(plan_steps),
            "estimated_duration": total_time,
            "safety_level": safety_level,
            "complexity_score": self._calculate_complexity_score(requirement),
            "planning_metadata": {
                "template_used": task_type,
                "knowledge_context": bool(retrieved_knowledge),
                "created_at": datetime.utcnow().isoformat()
            }
        }
    
    async def _refine_plan(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Refine an existing plan based on feedback or new information."""
        existing_plan = input_data.get("existing_plan", {})
        feedback = input_data.get("feedback", {})
        new_requirements = input_data.get("new_requirements", {})
        
        # Extract current plan steps
        current_steps = existing_plan.get("steps", [])
        
        # Apply refinements based on feedback
        refined_steps = []
        for step in current_steps:
            refined_step = step.copy()
            
            # Adjust based on feedback
            if feedback.get("increase_testing"):
                if step["phase"] == "testing":
                    refined_step["estimated_time"] = int(step["estimated_time"] * 1.5)
            
            if feedback.get("add_safety_checks") and step["phase"] == "validation":
                refined_step["description"] += " with enhanced safety checks"
                refined_step["estimated_time"] = int(step["estimated_time"] * 1.2)
            
            refined_steps.append(refined_step)
        
        # Add new steps if required
        if new_requirements.get("add_documentation"):
            refined_steps.append({
                "phase": "documentation",
                "step": "Generate documentation",
                "description": "Create comprehensive code documentation",
                "inputs": ["generated_code", "validation_results"],
                "outputs": ["documentation"],
                "estimated_time": 45,
                "agent": "generator"
            })
        
        # Recalculate total time
        total_time = sum(step["estimated_time"] for step in refined_steps)
        
        return {
            "refined_plan": {
                "steps": refined_steps,
                "total_steps": len(refined_steps),
                "estimated_duration": total_time
            },
            "changes_made": {
                "steps_modified": len([s for s in refined_steps if s != current_steps[refined_steps.index(s)] if refined_steps.index(s) < len(current_steps)]),
                "steps_added": len(refined_steps) - len(current_steps),
                "time_adjustment": total_time - existing_plan.get("estimated_duration", 0)
            }
        }
    
    async def _estimate_complexity(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate the complexity of a requirement."""
        requirement = input_data.get("requirement", {})
        
        complexity_score = self._calculate_complexity_score(requirement)
        
        # Determine complexity level
        if complexity_score < 3:
            level = "Low"
            description = "Simple automation task with basic logic"
        elif complexity_score < 6:
            level = "Medium"
            description = "Moderate complexity with multiple components"
        elif complexity_score < 9:
            level = "High"
            description = "Complex system with advanced features"
        else:
            level = "Very High"
            description = "Highly complex system requiring extensive planning"
        
        return {
            "complexity_score": complexity_score,
            "complexity_level": level,
            "description": description,
            "estimated_development_time": complexity_score * 60,  # minutes
            "recommended_team_size": min(max(1, complexity_score // 3), 5),
            "risk_factors": self._identify_risk_factors(requirement)
        }
    
    async def _validate_plan(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a task plan for completeness and feasibility."""
        plan = input_data.get("plan", {})
        
        validation_results = {
            "is_valid": True,
            "issues": [],
            "recommendations": [],
            "completeness_score": 0
        }
        
        steps = plan.get("steps", [])
        
        # Check for required phases
        phases = set(step.get("phase", "") for step in steps)
        required_phases = {"analysis", "generation", "validation", "testing"}
        
        missing_phases = required_phases - phases
        if missing_phases:
            validation_results["issues"].append(f"Missing phases: {', '.join(missing_phases)}")
            validation_results["is_valid"] = False
        
        # Check step dependencies
        outputs = set()
        for step in steps:
            step_inputs = step.get("inputs", [])
            for inp in step_inputs:
                if inp not in outputs and inp not in ["user_requirement", "domain_knowledge"]:
                    validation_results["issues"].append(f"Missing dependency: {inp} for step {step.get('step', 'unknown')}")
            
            outputs.update(step.get("outputs", []))
        
        # Calculate completeness score
        completeness_factors = [
            len(phases) >= 4,  # Has main phases
            any(step.get("phase") == "safety" for step in steps) if plan.get("safety_level", 1) > 1 else True,
            sum(step.get("estimated_time", 0) for step in steps) > 0,  # Has time estimates
            all(step.get("agent") for step in steps)  # All steps have assigned agents
        ]
        
        validation_results["completeness_score"] = sum(completeness_factors) / len(completeness_factors) * 100
        
        # Add recommendations
        if validation_results["completeness_score"] < 80:
            validation_results["recommendations"].append("Plan needs more detailed steps and dependencies")
        
        if not any(step.get("phase") == "documentation" for step in steps):
            validation_results["recommendations"].append("Consider adding documentation phase")
        
        return validation_results
    
    def _identify_task_type(self, description: str) -> str:
        """Identify the type of PLC task from description."""
        description_lower = description.lower()
        
        if any(word in description_lower for word in ["motor", "pump", "fan", "drive"]):
            return "motor_control"
        elif any(word in description_lower for word in ["analog", "temperature", "pressure", "flow"]):
            return "analog_processing"
        elif any(word in description_lower for word in ["sequence", "batch", "recipe", "step"]):
            return "sequence_control"
        elif any(word in description_lower for word in ["safety", "emergency", "interlock", "sil"]):
            return "safety_function"
        else:
            return "motor_control"  # Default
    
    def _calculate_complexity_score(self, requirement: Dict[str, Any]) -> int:
        """Calculate complexity score for a requirement."""
        score = 0
        
        description = requirement.get("description", "").lower()
        safety_level = requirement.get("safety_level", 1)
        constraints = requirement.get("constraints", {})
        
        # Base complexity from description length and keywords
        score += min(len(description.split()) // 10, 3)
        
        # Safety level impact
        score += safety_level
        
        # Complex keywords
        complex_keywords = ["pid", "control", "algorithm", "communication", "network", "database"]
        score += sum(1 for keyword in complex_keywords if keyword in description)
        
        # Constraints impact
        score += len(constraints)
        
        # Multiple systems/interfaces
        if any(word in description for word in ["interface", "communication", "multiple", "system"]):
            score += 2
        
        return min(score, 10)  # Cap at 10
    
    def _identify_risk_factors(self, requirement: Dict[str, Any]) -> List[str]:
        """Identify potential risk factors in the requirement."""
        risks = []
        
        description = requirement.get("description", "").lower()
        safety_level = requirement.get("safety_level", 1)
        
        if safety_level > 2:
            risks.append("High safety integrity level requirements")
        
        if "real-time" in description or "critical" in description:
            risks.append("Real-time or time-critical requirements")
        
        if "communication" in description or "network" in description:
            risks.append("Network communication complexity")
        
        if "legacy" in description or "existing" in description:
            risks.append("Integration with legacy systems")
        
        if len(description.split()) > 100:
            risks.append("Complex or unclear requirements")
        
        return risks
