from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import time

# Internal imports
from api.models import DeploymentPayload
from api.telemetry_stream import router as stream_router
from core.grid_builder import build_pandapower_network
from core.simulation_engine import SimulationEngine

app = FastAPI(title="TRINETRA Backend Orchestrator", version="1.0")

# Register SSE Telemetry Stream
from api.telemetry_stream import router as stream_router
from api.control import router as control_router
app.include_router(stream_router, prefix="/api")
app.include_router(control_router, prefix="/api")

# Global singleton for the simulation engine
sim_engine = SimulationEngine()

# Enable CORS for the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development to prevent preflight errors
    allow_credentials=False, # Must be False if allow_origins is ["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "online", "message": "TRINETRA Physical Engine is running."}

@app.post("/api/deploy")
async def deploy_architecture(payload: DeploymentPayload):
    """
    Receives the JSON topology payload from the React Builder canvas, 
    initializes the physical engine, and starts the Modbus polling loop.
    """
    try:
        start_time = time.time()
        print(f"--- Received Deployment Payload ---")
        print(f"Nodes: {payload.metadata['total_nodes']} | Edges: {payload.metadata['total_edges']}")
        
        # 1. Start the background simulation engine
        await sim_engine.start(payload)

        execution_time = round((time.time() - start_time) * 1000, 2)
        
        return {
            "status": "success", 
            "message": "Architecture successfully mapped. Cyber-Physical Tick initialized.",
            "execution_time_ms": execution_time
        }

    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/stop")
async def stop_simulation():
    """Stops the background Cyber-Physical Tick loop."""
    await sim_engine.stop()
    return {"status": "success", "message": "Simulation stopped."}

@app.on_event("shutdown")
async def shutdown_event():
    """Ensure background loops and Modbus servers are closed on exit."""
    print("Shutting down TRINETRA Physics Engine gracefully...")
    await sim_engine.stop()
