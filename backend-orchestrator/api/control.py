from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

# We will import the sim_engine from main in a way that avoids circular imports
# or just pass it in. For now, let's assume we can import it from a shared state.
# A better way is to use a dependency or just import it directly if main doesn't import control.

router = APIRouter()

@router.post("/ied/{ied_id}/reset")
async def reset_ied(ied_id: str):
    """
    Sends a Reset Pulse (TRUE then FALSE) to the specified IED's Reset Coil (%QX0.7).
    """
    from main import sim_engine
    
    if not sim_engine.is_running:
        raise HTTPException(status_code=400, detail="Simulation is not running.")
    
    if ied_id not in sim_engine.modbus.clients:
        raise HTTPException(status_code=404, detail=f"IED {ied_id} not found or not connected.")
    
    try:
        # 1. Pulse HIGH (Set Reset_Cmd to TRUE)
        # Coil 7 corresponds to %QX0.7
        await sim_engine.modbus.clients[ied_id].write_coil(address=7, value=True, slave=1)
        
        # 2. Small delay to ensure the PLC task (500ms) picks it up
        import asyncio
        await asyncio.sleep(0.6)
        
        # 3. Pulse LOW (Set Reset_Cmd to FALSE)
        await sim_engine.modbus.clients[ied_id].write_coil(address=7, value=False, slave=1)
        
        return {"status": "success", "message": f"Reset command pulsed to IED {ied_id}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pulse reset: {str(e)}")
