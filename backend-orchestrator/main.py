from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from api.models import DeploymentPayload
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

@app.post("/api/deploy", status_code=202)
async def deploy_architecture(payload: DeploymentPayload, background_tasks: BackgroundTasks):
    """
    Receives the JSON topology payload from the React Builder canvas.
    Immediately returns 202 Accepted, then starts the Cyber-Physical engine
    in the background (Docker provisioning takes 20-30 seconds).
    """
    print(f"--- Received Deployment Payload ---")
    print(f"Nodes: {payload.metadata['total_nodes']} | Edges: {payload.metadata['total_edges']}")
    
    # Fire-and-forget: provision IEDs, compile ST code, connect Modbus.
    # This prevents the 30s Docker wait from timing out the HTTP request.
    background_tasks.add_task(sim_engine.start, payload)
    
    return {
        "status": "provisioning",
        "message": "Deployment accepted. Containers are starting in the background. Monitor terminal logs."
    }

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
