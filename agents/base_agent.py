"""Base agent class for the PLC Agent System."""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain.schema import BaseMessage
from langchain.agents import AgentExecutor
from langchain.memory import ConversationBufferMemory

from models.schemas import AgentRole, AgentTask, AgentMessage, TaskStatus


class BaseAgent(ABC):
    """Abstract base class for all agents in the system."""
    
    def __init__(
        self,
        role: AgentRole,
        name: str,
        description: str,
        llm=None,
        tools: Optional[List] = None,
        memory: Optional[ConversationBufferMemory] = None
    ):
        self.role = role
        self.name = name
        self.description = description
        self.llm = llm
        self.tools = tools or []
        self.memory = memory or ConversationBufferMemory()
        self.logger = logging.getLogger(f"agent.{role.value}")
        self.is_active = False
        self.current_task: Optional[AgentTask] = None
        
    @abstractmethod
    async def process_task(self, task: AgentTask) -> Dict[str, Any]:
        """Process a task assigned to this agent."""
        pass
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        pass
    
    async def execute_task(self, task: AgentTask) -> AgentTask:
        """Execute a task and update its status."""
        self.logger.info(f"Starting task {task.id} of type {task.task_type}")
        
        try:
            self.current_task = task
            self.is_active = True
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.utcnow()
            
            # Process the task
            result = await self.process_task(task)
            
            # Update task with result
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            
            self.logger.info(f"Completed task {task.id} successfully")
            
        except Exception as e:
            self.logger.error(f"Task {task.id} failed: {str(e)}")
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.utcnow()
            
        finally:
            self.is_active = False
            self.current_task = None
            
        return task
    
    async def send_message(self, receiver: AgentRole, content: Dict[str, Any], correlation_id: Optional[UUID] = None) -> AgentMessage:
        """Send a message to another agent."""
        message = AgentMessage(
            sender=self.role,
            receiver=receiver,
            content=content,
            correlation_id=correlation_id
        )
        
        self.logger.debug(f"Sending message to {receiver.value}: {message.id}")
        return message
    
    async def receive_message(self, message: AgentMessage) -> Optional[Dict[str, Any]]:
        """Receive and process a message from another agent."""
        self.logger.debug(f"Received message from {message.sender.value}: {message.id}")
        
        # Default implementation - can be overridden by specific agents
        return {"acknowledged": True, "message_id": message.id}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the agent."""
        return {
            "role": self.role.value,
            "name": self.name,
            "is_active": self.is_active,
            "current_task_id": self.current_task.id if self.current_task else None,
            "tools_count": len(self.tools)
        }
    
    def add_tool(self, tool):
        """Add a tool to the agent's toolkit."""
        self.tools.append(tool)
        self.logger.debug(f"Added tool: {tool.name if hasattr(tool, 'name') else str(tool)}")
    
    def clear_memory(self):
        """Clear the agent's conversation memory."""
        self.memory.clear()
        self.logger.debug("Cleared agent memory")


class LLMAgent(BaseAgent):
    """Base class for agents that use LLM for processing."""
    
    def __init__(self, role: AgentRole, name: str, description: str, llm, **kwargs):
        super().__init__(role, name, description, llm, **kwargs)
        self.agent_executor: Optional[AgentExecutor] = None
        
    def initialize_executor(self):
        """Initialize the LangChain agent executor."""
        if self.llm and self.tools:
            from langchain.agents import initialize_agent, AgentType
            
            self.agent_executor = initialize_agent(
                tools=self.tools,
                llm=self.llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                memory=self.memory,
                verbose=True,
                handle_parsing_errors=True
            )
            
            self.logger.info(f"Initialized agent executor with {len(self.tools)} tools")
    
    async def run_llm_task(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Run a task using the LLM agent executor."""
        if not self.agent_executor:
            self.initialize_executor()
        
        if not self.agent_executor:
            raise ValueError("Agent executor not initialized - missing LLM or tools")
        
        # Add context to the prompt if provided
        if context:
            context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            full_prompt = f"Context:\n{context_str}\n\nTask: {prompt}"
        else:
            full_prompt = prompt
        
        try:
            result = await self.agent_executor.arun(full_prompt)
            return result
        except Exception as e:
            self.logger.error(f"LLM task execution failed: {str(e)}")
            raise
