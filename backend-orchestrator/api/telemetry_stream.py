import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

@router.get("/stream")
async def telemetry_stream():
    """
    Server-Sent Events (SSE) endpoint.
    Streams the live `current_state` of the TRINETRA SimulationEngine to the React frontend every 500ms.
    """
    # Import locally to avoid circular dependencies with main.py at boot
    from main import sim_engine
    
    async def event_generator():
        while True:
            # Yield the current snapshot of the physics and cyber states
            if hasattr(sim_engine, 'current_state'):
                data = json.dumps(sim_engine.current_state)
                yield f"data: {data}\n\n"
            else:
                yield f"data: {json.dumps({'status': 'offline'})}\n\n"
            
            # Broadcast matches the physics engine tick rate
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
