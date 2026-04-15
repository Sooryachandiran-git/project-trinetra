from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from pydantic import BaseModel

# We will import the sim_engine from main in a way that avoids circular imports
# or just pass it in. For now, let's assume we can import it from a shared state.
# A better way is to use a dependency or just import it directly if main doesn't import control.

router = APIRouter()


@router.get("/attacks")
async def get_attack_state():
    """Return currently configured simulator-only attack demos."""
    from main import sim_engine

    return {
        "status": "success",
        "attacks": sim_engine.attack_state,
        "active_attacks": sim_engine.get_active_attacks(),
    }


@router.post("/attacks/atk12/enable")
async def enable_atk12_demo():
    """
    Enable a safe ATK-12 demonstration mode.
    This simulates bidirectional Modbus tampering within the backend loop.
    """
    from main import sim_engine

    sim_engine.set_attack_state("atk12_mitm_demo", True)
    return {
        "status": "success",
        "message": "ATK-12 demo mode enabled.",
        "active_attacks": sim_engine.get_active_attacks(),
    }


@router.post("/attacks/atk12/disable")
async def disable_atk12_demo():
    """Disable the safe ATK-12 demonstration mode."""
    from main import sim_engine

    sim_engine.set_attack_state("atk12_mitm_demo", False)
    return {
        "status": "success",
        "message": "ATK-12 demo mode disabled.",
        "active_attacks": sim_engine.get_active_attacks(),
    }

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


@router.post("/attacks/atk13/enable")
async def enable_atk13_demo():
    """Enable ATK-13 GPS Time Desync demo."""
    from main import sim_engine
    sim_engine.set_attack_state("atk13_gps_desync", True)
    return {"status": "success", "message": "ATK-13 GPS Desync enabled."}


class LoadMultiplierPayload(BaseModel):
    multiplier: float = 1.0

@router.post("/debug/pandapower/load")
async def debug_pandapower_load(payload: LoadMultiplierPayload):
    """
    ATK-14 endpoint: Modify the Pandapower load in-memory to simulate
    a compromised state estimator pushing lines beyond thermal limits.
    """
    from main import sim_engine
    
    if not sim_engine.is_running or sim_engine.net is None:
        raise HTTPException(status_code=400, detail="Simulation is not running.")
    
    try:
        import pandapower as pp
        # Multiply all load P and Q values
        sim_engine.net.load['p_mw'] = sim_engine.net.load['p_mw'] * payload.multiplier
        sim_engine.net.load['q_mvar'] = sim_engine.net.load['q_mvar'] * payload.multiplier
        
        return {
            "status": "success",
            "message": f"Load profile scaled by {payload.multiplier}x",
            "new_loads": sim_engine.net.load[['name', 'p_mw', 'q_mvar']].to_dict(orient='records')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to modify load: {str(e)}")
