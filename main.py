"""Main FastAPI application entry point for the PLC Code Generation System."""

import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import uvicorn

from core.config import settings
from core.orchestrator import WorkflowOrchestrator
from core.self_healing import SelfHealingOrchestrator
from database.connection import DatabaseManager
from agents.retrieval_agent import RetrievalAgent
from agents.planner_agent import PlannerAgent
from agents.generator_agent import GeneratorAgent
from agents.validator_agent import ValidatorAgent
from agents.debugger_agent import DebuggerAgent
from agents.simulator_agent import SimulatorAgent
from agents.monitor_agent import MonitorAgent
from models.schemas import UserRequirements, AgentMessage

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
workflow_orchestrator = None
self_healing_orchestrator = None
db_manager = None
websocket_connections = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global workflow_orchestrator, self_healing_orchestrator, db_manager
    
    logger.info("Starting PLC Code Generation System...")
    
    try:
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.initialize()
        logger.info("Database initialized successfully")
        
        # Initialize workflow orchestrator
        workflow_orchestrator = WorkflowOrchestrator()
        
        # Initialize and register agents
        agents = [
            RetrievalAgent(),
            PlannerAgent(),
            GeneratorAgent(),
            ValidatorAgent(),
            DebuggerAgent(),
            SimulatorAgent(),
            MonitorAgent()
        ]
        
        for agent in agents:
            workflow_orchestrator.register_agent(agent)
        
        logger.info(f"Registered {len(agents)} agents")
        
        # Initialize self-healing orchestrator
        self_healing_orchestrator = SelfHealingOrchestrator(workflow_orchestrator)
        await self_healing_orchestrator.start()
        
        logger.info("System startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Failed to start system: {str(e)}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down system...")
        if db_manager:
            await db_manager.close()
        logger.info("System shutdown completed")


# Create FastAPI app
app = FastAPI(
    title="PLC Code Generation System",
    description="AI-powered multi-agent system for automated PLC code generation",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": "2024-01-01T00:00:00Z"
    }


# System health endpoint
@app.get("/api/system/health")
async def get_system_health():
    """Get comprehensive system health status."""
    if not self_healing_orchestrator:
        raise HTTPException(status_code=503, detail="System not ready")
    
    try:
        health_data = await self_healing_orchestrator.get_system_health()
        return health_data
    except Exception as e:
        logger.error(f"Failed to get system health: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get system health")


# Code generation endpoint
@app.post("/api/code/generate")
async def generate_code(requirements: UserRequirements):
    """Generate PLC code from user requirements."""
    if not workflow_orchestrator:
        raise HTTPException(status_code=503, detail="System not ready")
    
    try:
        # Create workflow for code generation
        workflow_id = await workflow_orchestrator.create_workflow(
            name=f"Code Generation - {requirements.description[:50]}",
            requirements=requirements
        )
        
        # Execute workflow
        result = await workflow_orchestrator.execute_workflow(workflow_id)
        
        return {
            "workflow_id": workflow_id,
            "code": result.get("generated_code", ""),
            "status": result.get("status", "completed"),
            "validation_results": result.get("validation_results"),
            "simulation_results": result.get("simulation_results")
        }
        
    except Exception as e:
        logger.error(f"Code generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Code generation failed: {str(e)}")


# Code validation endpoint
@app.post("/api/code/validate")
async def validate_code(request: dict):
    """Validate PLC code."""
    code = request.get("code", "")
    if not code:
        raise HTTPException(status_code=400, detail="Code is required")
    
    if not workflow_orchestrator:
        raise HTTPException(status_code=503, detail="System not ready")
    
    try:
        validator_agent = workflow_orchestrator.get_agent("validator")
        if not validator_agent:
            raise HTTPException(status_code=503, detail="Validator agent not available")
        
        result = await validator_agent.process_task({
            "task_type": "validate_code",
            "input_data": {"code": code}
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Code validation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Code validation failed: {str(e)}")


# Code simulation endpoint
@app.post("/api/code/simulate")
async def simulate_code(request: dict):
    """Simulate PLC code execution."""
    code = request.get("code", "")
    if not code:
        raise HTTPException(status_code=400, detail="Code is required")
    
    if not workflow_orchestrator:
        raise HTTPException(status_code=503, detail="System not ready")
    
    try:
        simulator_agent = workflow_orchestrator.get_agent("simulator")
        if not simulator_agent:
            raise HTTPException(status_code=503, detail="Simulator agent not available")
        
        result = await simulator_agent.process_task({
            "task_type": "simulate_code",
            "input_data": {"code": code}
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Code simulation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Code simulation failed: {str(e)}")


# Projects endpoints
@app.get("/api/projects")
async def get_projects():
    """Get all projects."""
    # Mock data for now
    return [
        {
            "id": "1",
            "name": "Conveyor Control System",
            "description": "Automated conveyor belt control with sensors",
            "status": "completed",
            "language": "ST",
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T12:00:00Z"
        },
        {
            "id": "2",
            "name": "Temperature Control",
            "description": "PID temperature control system",
            "status": "in_progress",
            "language": "ST",
            "created_at": "2024-01-02T09:00:00Z",
            "updated_at": "2024-01-02T11:30:00Z"
        }
    ]


@app.get("/api/projects/recent")
async def get_recent_projects():
    """Get recent projects."""
    projects = await get_projects()
    return projects[:5]  # Return last 5 projects


# Workflow endpoints
@app.get("/api/workflows/stats")
async def get_workflow_stats():
    """Get workflow statistics."""
    return {
        "total_workflows": 25,
        "successful_workflows": 20,
        "running_workflows": 2,
        "failed_workflows": 3
    }


# Monitoring endpoints
@app.get("/api/monitor/telemetry")
async def get_telemetry_data(time_range: str = "1h"):
    """Get telemetry data."""
    # Mock telemetry data
    import random
    from datetime import datetime, timedelta
    
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)
    
    data = []
    current_time = start_time
    while current_time <= end_time:
        data.append({
            "timestamp": current_time.isoformat(),
            "cpu_usage": random.uniform(20, 80),
            "memory_usage": random.uniform(30, 70),
            "cycle_time_ms": random.uniform(10, 50)
        })
        current_time += timedelta(minutes=5)
    
    return data


@app.get("/api/monitor/alerts")
async def get_alerts():
    """Get active alerts."""
    return [
        {
            "title": "High CPU Usage",
            "message": "CPU usage exceeded 80% threshold",
            "severity": "warning",
            "timestamp": "2024-01-01T12:00:00Z"
        }
    ]


@app.get("/api/agents")
async def get_agents():
    """Get agent status."""
    return [
        {
            "id": "retrieval",
            "name": "Retrieval Agent",
            "role": "retrieval",
            "status": "running",
            "last_heartbeat": "2024-01-01T12:00:00Z",
            "tasks_processed": 150,
            "success_rate": 0.95
        },
        {
            "id": "planner",
            "name": "Planner Agent",
            "role": "planner",
            "status": "running",
            "last_heartbeat": "2024-01-01T12:00:00Z",
            "tasks_processed": 120,
            "success_rate": 0.92
        },
        {
            "id": "generator",
            "name": "Generator Agent",
            "role": "generator",
            "status": "running",
            "last_heartbeat": "2024-01-01T12:00:00Z",
            "tasks_processed": 100,
            "success_rate": 0.88
        }
    ]


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time communication."""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            
            # Echo back for now (can be extended for real functionality)
            await websocket.send_text(f"Echo: {data}")
            
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)


async def broadcast_message(message: dict):
    """Broadcast message to all connected WebSocket clients."""
    if websocket_connections:
        for websocket in websocket_connections.copy():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {str(e)}")
                websocket_connections.remove(websocket)


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
