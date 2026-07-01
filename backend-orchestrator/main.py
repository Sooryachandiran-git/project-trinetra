from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from api.models import DeploymentPayload, ElectricalGridModel
from core.simulation_engine import SimulationEngine
from core.pandapower_solver import solve_pure_pandapower
from core.andes_solver import solve_andes_powerflow, simulate_cyber_attack

app = FastAPI(title="TRINETRA Backend Orchestrator", version="1.0")

# Register SSE Telemetry Stream and API Routers
from api.telemetry_stream import router as stream_router
from api.control import router as control_router
from api.attack import router as attack_router
from api.history import router as history_router
app.include_router(stream_router, prefix="/api")
app.include_router(control_router, prefix="/api")
app.include_router(attack_router, prefix="/api")
app.include_router(history_router, prefix="/api")

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

@app.post("/api/pandapower/solve")
async def pandapower_solve(grid: ElectricalGridModel):
    """
    Executes a pure pandapower steady state solve on the provided grid topology.
    Returns the resulting pandas dataframes serialized as JSON.
    """
    print(f"--- Received Pure Pandapower Solve Request ---")
    results = solve_pure_pandapower(grid)
    return results

@app.post("/api/andes/solve")
async def andes_solve(grid: ElectricalGridModel):
    """
    Executes a pure ANDES steady state solve on the provided grid topology.
    Returns the resulting pandas dataframes serialized as JSON.
    """
    print(f"--- Received Pure ANDES Solve Request ---")
    results = solve_andes_powerflow(grid)
    return results

@app.post("/api/andes/cyber-attack")
async def andes_cyber_attack(grid: ElectricalGridModel):
    """
    Executes an ANDES Time-Domain Simulation (TDS) simulating a cyber-attack 
    (tripping a line) and returns the voltage trajectories.
    """
    print(f"--- Received ANDES Cyber Attack TDS Request ---")
    results = simulate_cyber_attack(grid)
    return results

@app.on_event("shutdown")
async def shutdown_event():
    """Ensure background loops and Modbus servers are closed on exit."""
    print("Shutting down TRINETRA Physics Engine gracefully...")
    await sim_engine.stop()
