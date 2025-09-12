"""
AutoPLC Enhanced - Main FastAPI Application (Updated for meta column)
"""

import os
import asyncio
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import asynccontextmanager
import re

import json
from fastapi import FastAPI, HTTPException, Depends, WebSocket, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn

from backend.core.database import init_db, get_async_db, AsyncSessionLocal
from backend.core.config import get_settings
from backend.core.supervisor import DynamicSupervisor
from backend.models.task import Task, AgentMessage, TaskStatus, AgentRole
from backend.core.websocket_manager import WebSocketManager
from backend.agents.simulator_agent import SimulatorAgent
from backend.tools.knowledge_base import initialize_knowledge_base

# Pydantic models for API
class CodeGenerationRequest(BaseModel):
    prompt: str
    user_id: Optional[str] = "default"
    context: Optional[Dict[str, Any]] = {}

class FeedbackRequest(BaseModel):
    task_id: str
    feedback: str
    user_id: Optional[str] = "default"

class SimulationRequest(BaseModel):
    code: str

class CompileRequest(BaseModel):
    code: str

class ParseVariablesRequest(BaseModel):
    code: str

class DashboardGenerationRequest(BaseModel):
    code: str
    prompt: str

class TaskResponse(BaseModel):
    task_id: str
    prompt: Optional[str] = None
    status: str
    progress: float = 0.0
    current_agent: Optional[str] = None
    generated_code: Optional[str] = None
    quality_score: Optional[float] = None
    error: Optional[str] = None

# Global instances
supervisor = None
websocket_manager = WebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    global supervisor
    
    print("🚀 Starting AutoPLC Enhanced...")
    
    # Initialize database
    await init_db()
    
    # Initialize knowledge base
    try:
        initialize_knowledge_base()
    except Exception as e:
        print(f"⚠️ Knowledge base initialization failed: {e}")
    
    # Initialize dynamic supervisor
    supervisor = DynamicSupervisor()
    
    print("✅ AutoPLC Enhanced started successfully!")
    yield
    print("🛑 Shutting down AutoPLC Enhanced...")

# Create FastAPI app
app = FastAPI(
    title="AutoPLC Enhanced",
    description="AI-powered PLC code generation with multi-agent collaboration",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
@app.post("/api/generate", response_model=TaskResponse)
async def generate_code(
    request: CodeGenerationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """Generate PLC code with dynamic agent orchestration"""
    
    # Create new task
    task = Task(
        prompt=request.prompt,
        user_id=request.user_id,
        status=TaskStatus.PENDING,
        context=request.context
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    
    # Start generation in background
    background_tasks.add_task(
        run_dynamic_workflow,
        str(task.id),
        request.prompt,
        request.context
    )
    
    return TaskResponse(
        task_id=str(task.id),
        status="running",
        progress=0.0
    )

@app.post("/api/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """Submit feedback for iterative improvement"""
    
    task = await db.get(Task, int(request.task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Start feedback processing in background
    background_tasks.add_task(
        process_user_feedback,
        request.task_id,
        request.feedback,
        request.user_id
    )
    
    return {"message": "Feedback received, processing improvements..."}

@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
async def get_task_status(task_id: str, db: AsyncSession = Depends(get_async_db)):
    """Get task status and results"""
    
    task = await db.get(Task, int(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskResponse(
        task_id=str(task.id),
        prompt=task.prompt,
        status=task.status.value,
        progress=task.progress,
        current_agent=task.current_agent,
        generated_code=task.generated_code,
        quality_score=task.quality_score,
        error=task.error_message
    )

@app.get("/api/tasks/{task_id}/messages")
async def get_task_messages(task_id: str, db: AsyncSession = Depends(get_async_db)):
    """Get all agent messages for a task"""
    
    result = await db.execute(select(AgentMessage).where(
        AgentMessage.task_id == int(task_id)
    ).order_by(AgentMessage.timestamp))
    messages = result.scalars().all()
    return [
        {
            "id": msg.id,
            "agent_role": msg.agent_role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
            "meta": msg.meta  # FIXED: Changed from metadata to meta
        }
        for msg in messages
    ]

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_async_db)):
    """Delete a task and all its associated data."""
    
    task = await db.get(Task, int(task_id))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    await db.delete(task)
    await db.commit()
    
    return {"message": f"Task {task_id} deleted successfully."}

@app.post("/api/compile")
async def compile_code_endpoint(request: CompileRequest):
    """Compiles code on-demand using MATIEC."""
    # This is a synchronous operation, run it in a thread pool
    from backend.agents.validator_agent import ValidatorAgent
    validator = ValidatorAgent()
    result = await run_in_threadpool(validator.compile_code_only, request.code)
    success = "successful" in result.lower()
    return {"success": success, "message": result}

@app.post("/api/parse-variables")
async def parse_variables_endpoint(request: ParseVariablesRequest):
    """Parses variables from a code string."""
    try:
        inputs = []
        outputs = []
        internals = []
        
        var_block_match = re.search(r"VAR(.*?)END_VAR", request.code, re.DOTALL | re.IGNORECASE)
        if var_block_match:
            var_block = var_block_match.group(1)
            lines = var_block.split('\n')
            for line in lines:
                line = line.strip()
                if not line or line.startswith("(*"):
                    continue
                
                # Regex to capture name, address (optional), and complex types.
                # It stops at `:=`, `;`, or end of line.
                regex = r"(\w+)\s*(?:AT\s*(%[IQ][X]?\d+\.\d+))?\s*:\s*([\w\s\[\]\(\)\d\._]+?)\s*(?::=|;|$)"
                match = re.match(regex, line, re.IGNORECASE)
                if match:
                    name, address, var_type = match.groups()
                    var_info = {"name": name, "type": var_type.strip().upper(), "address": address}
                    if address and address.upper().startswith('%I'):
                        inputs.append(var_info)
                    elif address and address.upper().startswith('%Q'):
                        outputs.append(var_info)
                    else:
                        internals.append(var_info)

        return {"success": True, "inputs": inputs, "outputs": outputs, "internals": internals}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse variables: {e}")

@app.post("/api/simulation/dashboard")
async def generate_dashboard_endpoint(request: DashboardGenerationRequest):
    """Generates a dynamic dashboard definition using an LLM."""
    simulator = SimulatorAgent()
    result = await simulator.generate_dashboard_definition(request.code, request.prompt)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to generate dashboard"))
    return result


@app.post("/api/simulate")
async def start_simulation_endpoint(request: SimulationRequest):
    """Uploads code to OpenPLC and starts the simulation."""
    simulator = SimulatorAgent()

    # This is a synchronous operation, run it in a thread pool
    def run_simulation_steps():
        filepath = simulator.save_code_to_file(request.code)
        upload_result = simulator.upload_to_openplc(filepath)
        if not upload_result.get("success"):
            return {"success": False, "message": f"Upload failed: {upload_result.get('error', 'Unknown error')}"}

        start_result = simulator.start_plc_simulation()
        if not start_result.get("success"):
            return {"success": False, "message": f"Failed to start PLC: {start_result.get('error', 'Unknown error')}"}

        return {"success": True, "message": "Simulation started successfully."}

    result = await run_in_threadpool(run_simulation_steps)
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.post("/api/simulation/stop")
async def stop_simulation_endpoint():
    """Stops the running PLC simulation."""
    simulator = SimulatorAgent()
    result = await run_in_threadpool(simulator.stop_plc_simulation)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to stop PLC"))
    return {"success": True, "message": "Simulation stopped."}

@app.get("/api/simulation/status")
async def get_simulation_status_endpoint():
    """Gets the current status and variable values from the PLC."""
    simulator = SimulatorAgent()
    def get_full_status():
        status = simulator.get_plc_status()
        variables = simulator.get_variable_values()
        return {"plc_status": status, "variables": variables}
    result = await run_in_threadpool(get_full_status)
    return result

@app.get("/api/tasks")
async def get_recent_tasks(
    limit: int = 10,
    user_id: str = "default",
    db: AsyncSession = Depends(get_async_db)
):
    """Get recent tasks for a user"""
    
    result = await db.execute(select(Task).where(
        Task.user_id == user_id
    ).order_by(Task.created_at.desc()).limit(limit))
    tasks = result.scalars().all()
    return [
        {
            "id": str(task.id),
            "prompt": task.prompt[:100] + "..." if len(task.prompt) > 100 else task.prompt,
            "status": task.status.value,
            "quality_score": task.quality_score,
            "created_at": task.created_at.isoformat()
        }
        for task in tasks
    ]

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time updates"""
    await websocket_manager.connect(websocket, client_id)
    try:
        while True:
            # Wait for messages from the client (e.g., for subscribing to tasks)
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "subscribe":
                task_id = message.get("task_id")
                if task_id:
                    await websocket_manager.subscribe_to_task(client_id, task_id)
                    await websocket_manager.send_personal_message(
                        {"status": "subscribed", "task_id": task_id},
                        client_id
                    )

    except Exception as e:
        # This exception is expected when the client disconnects
        print(f"WebSocket disconnected for client {client_id}: {e}")
    finally:
        websocket_manager.disconnect(client_id)

# Background task functions
async def run_dynamic_workflow(task_id: str, prompt: str, context: Dict[str, Any]):
    """Run the dynamic agent workflow"""
    global supervisor
    async with AsyncSessionLocal() as db:
        task = await db.get(Task, int(task_id))
        if not task:
            print(f"Workflow error: Task {task_id} not found.")
            return

        try:
            # Update task status
            task.status = TaskStatus.RUNNING
            task.progress = 0.1
            await db.commit()

            # Send real-time update
            await websocket_manager.broadcast(task_id, {
                "type": "status_update",
                "status": "running",
                "progress": 0.1,
                "message": "Starting dynamic workflow..."
            })

            # Run the supervisor workflow
            result = await supervisor.execute_workflow(
                task_id=task_id,
                prompt=prompt,
                context=context,
                progress_callback=lambda p, msg: asyncio.create_task(
                    websocket_manager.broadcast(task_id, {
                        "type": "progress",
                        "progress": p,
                        "message": msg
                    })
                ),
                agent_callback=lambda agent, status, msg: asyncio.create_task(
                    websocket_manager.broadcast(task_id, {
                        "type": "agent_update",
                        "agent": agent.value,
                        "status": status,
                        "message": msg
                    })
                )
            )

            # Update task with results
            task.status = TaskStatus.COMPLETED if result.get("success") else TaskStatus.FAILED
            task.generated_code = result.get("code")
            task.quality_score = result.get("quality_score")
            task.error_message = result.get("error")
            task.progress = 1.0
            task.completed_at = datetime.utcnow()
            await db.commit()

            # Send completion update
            await websocket_manager.broadcast(task_id, {
                "type": "completed",
                "result": result
            })

        except Exception as e:
            # Handle errors
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.progress = 1.0
            task.completed_at = datetime.utcnow()
            await db.commit()

            await websocket_manager.broadcast(task_id, {
                "type": "error",
                "error": str(e)
            })
            print(f"Workflow failed for task {task_id}: {e}")

async def process_user_feedback(task_id: str, feedback: str, user_id: str):
    """Process user feedback for iterative improvement"""
    global supervisor
    async with AsyncSessionLocal() as db:
        task = await db.get(Task, int(task_id))
        if not task:
            return

        try:
            # Use supervisor to process feedback
            result = await supervisor.process_feedback(
                task_id=task_id,
                original_code=task.generated_code,
                feedback=feedback,
                validator_report=task.error_message or "No previous errors"
            )

            # Update task with improved code
            if result.get("success"):
                task.generated_code = result.get("code")
                task.quality_score = result.get("quality_score")
                task.status = TaskStatus.COMPLETED
            else:
                task.error_message = result.get("error")
                task.status = TaskStatus.FAILED

            await db.commit()

            # Send update
            await websocket_manager.broadcast(task_id, {
                "type": "feedback_processed",
                "result": result
            })

        except Exception as e:
            print(f"Feedback processing error: {e}")

# Serve frontend files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def serve_frontend():
    """Serve the main frontend page"""
    return FileResponse("frontend/index.html")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0"
    }

if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["backend"],
        log_level="info"
    )
