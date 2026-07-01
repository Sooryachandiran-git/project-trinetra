import os
import sys
import math
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Optional

# Add current directory to sys.path so we can import core modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from core.parse_case14 import IEEE14Parser
from core.convert_case14 import IEEE14Converter
from core.build_ieee14 import IEEE14Builder

app = FastAPI(title="IEEE 14-Bus Live Digital Twin API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paths
base_dir = os.path.dirname(__file__)
case14_path = os.path.join(base_dir, "data/case14.m")

# Global Network State
class NetworkState:
    def __init__(self):
        self.reset()

    def reset(self):
        # Parse case14.m
        self.parser = IEEE14Parser(case14_path)
        self.bus_raw, self.gen_raw, self.branch_raw = self.parser.parse()
        
        # Convert to OpenDSS parameters
        self.converter = IEEE14Converter(self.bus_raw, self.gen_raw, self.branch_raw)
        (
            self.bus,
            self.lines,
            self.transformers,
            self.generators,
            self.loads,
            self.shunts
        ) = self.converter.convert()
        
        # Outage tracking (set of disabled branch IDs, which correspond to indices in branch_raw)
        self.disabled_branches = set()

# Initialize the global state
state = NetworkState()

# Pydantic Schemas for Updates
class GeneratorUpdate(BaseModel):
    bus: int
    pg: float  # MW
    vpu: float  # pu
    status: bool  # True for active, False for inactive

class LoadUpdate(BaseModel):
    bus: int
    pd: float  # MW
    qd: float  # Mvar

class TransformerUpdate(BaseModel):
    id: int  # branch index
    tap: float

class BranchToggle(BaseModel):
    id: int  # branch index
    active: bool

# Endpoints

@app.get("/api/network")
def get_network():
    """Returns the current configurable parameters of the network."""
    # List of generators
    gens = []
    for idx, row in state.generators.iterrows():
        bus_id = int(row["Bus"])
        is_cond = bool(float(row["Pg"]) == 0.0)
        gens.append({
            "bus": bus_id,
            "pg_setpoint_mw": float(row["Pg"]) * 100.0 if not is_cond else 0.0,
            "vpu_setpoint": float(row["Vg"]),
            "status": bool(int(row["Status"]) == 1),
            "is_condenser": is_cond
        })
        
    # List of loads
    loads = []
    for idx, row in state.loads.iterrows():
        loads.append({
            "bus": int(row["Bus"]),
            "pd_mw": float(row["Pd"]) * 100.0,
            "qd_mvar": float(row["Qd"]) * 100.0
        })
        
    # List of branches
    branches = []
    # Lines
    for idx, row in state.lines.iterrows():
        branches.append({
            "id": int(idx),
            "name": f"Line {int(row['FromBus'])}-{int(row['ToBus'])}",
            "type": "line",
            "from_bus": int(row["FromBus"]),
            "to_bus": int(row["ToBus"]),
            "active": bool(int(idx) not in state.disabled_branches)
        })
    # Transformers
    for idx, row in state.transformers.iterrows():
        branches.append({
            "id": int(idx),
            "name": f"Transformer {int(row['FromBus'])}-{int(row['ToBus'])}",
            "type": "transformer",
            "from_bus": int(row["FromBus"]),
            "to_bus": int(row["ToBus"]),
            "active": bool(int(idx) not in state.disabled_branches),
            "tap": float(row["Tap"])
        })
        
    return {
        "buses": [int(b) for b in state.bus["Bus"].values],
        "generators": gens,
        "loads": loads,
        "branches": branches
    }

@app.post("/api/simulate")
def simulate():
    """Runs OpenDSS simulation and returns telemetry."""
    # Instantiate builder with current state DataFrames
    builder = IEEE14Builder(
        state.bus,
        state.lines,
        state.transformers,
        state.generators,
        state.loads,
        state.shunts
    )
    
    # Rebuild circuit
    builder.create_circuit()
    builder.create_source()
    builder.create_transformers()
    builder.create_lines()
    builder.create_generators()
    builder.create_condensers()
    builder.create_loads()
    builder.create_shunts()
    builder.solve() # Initial solve
    
    dss = builder.dss
    
    # Apply branch outages
    for br_id in state.disabled_branches:
        if br_id in state.lines.index:
            # Row index position in lines DataFrame
            pos = state.lines.index.get_loc(br_id)
            line_name = f"Line.L{pos + 1}"
            dss.circuit.set_active_element(line_name)
            dss.cktelement.open([1, 0])
        elif br_id in state.transformers.index:
            transformer_name = f"Transformer.T{br_id}"
            dss.circuit.set_active_element(transformer_name)
            dss.cktelement.open([1, 0])
            
    # Solve again after outages
    dss.solution.solve()
    
    # Extract telemetry
    converged = bool(dss.solution.converged)
    
    # Losses
    losses_w, losses_vars = dss.circuit.losses
    losses_mw = float(losses_w / 1e6)
    losses_mvar = float(losses_vars / 1e6)
    
    # Vsource total power
    total_power = dss.circuit.total_power
    vsource_mw = float(-total_power[0] / 1000.0) if len(total_power) > 0 else 0.0
    vsource_mvar = float(-total_power[1] / 1000.0) if len(total_power) > 1 else 0.0
    
    # Buses telemetry
    bus_data = []
    bus_names = dss.circuit.buses_names
    for name in bus_names:
        dss.circuit.set_active_bus(name)
        vmag_angle_pu = dss.bus.vmag_angle_pu
        vmag_angle = dss.bus.vmag_angle
        
        v_pu = float(vmag_angle_pu[0]) if len(vmag_angle_pu) > 0 else 0.0
        angle_deg = float(vmag_angle_pu[1]) if len(vmag_angle_pu) > 1 else 0.0
        v_kv = float(vmag_angle[0] / 1000.0) if len(vmag_angle) > 0 else 0.0
        
        bus_id = int(name.replace("bus", ""))
        
        # Check if the bus originally has a generator, condenser, load, shunt
        orig_bus_row = state.bus[state.bus["Bus"] == bus_id].iloc[0]
        bus_type_code = int(orig_bus_row["Type"])
        
        bus_data.append({
            "id": bus_id,
            "name": f"Bus {bus_id}",
            "v_pu": v_pu,
            "v_kv": v_kv,
            "angle_deg": angle_deg,
            "p_load_mw": 0.0,
            "q_load_mvar": 0.0,
            "p_gen_mw": 0.0,
            "q_gen_mvar": 0.0,
            "is_slack": bool(bus_id == 1),
            "is_gen": False,
            "is_condenser": False,
            "is_load": False
        })
        
    bus_map = {b["id"]: b for b in bus_data}
    
    # Gather Load injections
    idx = dss.loads.first()
    while idx > 0:
        lname = dss.loads.name
        element_name = f"Load.{lname}"
        dss.circuit.set_active_element(element_name)
        buses = dss.cktelement.bus_names
        powers = dss.cktelement.total_powers
        
        if len(buses) > 0:
            bid = int(buses[0].replace("bus", ""))
            if bid in bus_map:
                bus_map[bid]["p_load_mw"] += float(powers[0] / 1000.0) if len(powers) > 0 else 0.0
                bus_map[bid]["q_load_mvar"] += float(powers[1] / 1000.0) if len(powers) > 1 else 0.0
                bus_map[bid]["is_load"] = True
        idx = dss.loads.next()
        
    # Gather Generator injections
    idx = dss.generators.first()
    while idx > 0:
        gname = dss.generators.name
        element_name = f"Generator.{gname}"
        dss.circuit.set_active_element(element_name)
        buses = dss.cktelement.bus_names
        powers = dss.cktelement.total_powers
        
        if len(buses) > 0:
            bid = int(buses[0].replace("bus", ""))
            if bid in bus_map:
                p_gen = float(-powers[0] / 1000.0) if len(powers) > 0 else 0.0
                q_gen = float(-powers[1] / 1000.0) if len(powers) > 1 else 0.0
                
                is_cond = bool(gname.startswith("c"))
                bus_map[bid]["p_gen_mw"] += p_gen
                bus_map[bid]["q_gen_mvar"] += q_gen
                if is_cond:
                    bus_map[bid]["is_condenser"] = True
                else:
                    bus_map[bid]["is_gen"] = True
        idx = dss.generators.next()
        
    # Add Slack source injection to Bus 1
    if 1 in bus_map:
        bus_map[1]["p_gen_mw"] += vsource_mw
        bus_map[1]["q_gen_mvar"] += vsource_mvar
        bus_map[1]["is_gen"] = True
        
    total_p_gen = float(sum(b["p_gen_mw"] for b in bus_data))
    total_q_gen = float(sum(b["q_gen_mvar"] for b in bus_data))
    
    # Gather Branch flows
    branch_data = []
    
    # Lines
    for i, (_, row) in enumerate(state.lines.iterrows()):
        br_id = int(row.name)
        line_name = f"L{i+1}"
        active = bool(br_id not in state.disabled_branches)
        from_bus = int(row["FromBus"])
        to_bus = int(row["ToBus"])
        
        p_flow = 0.0
        q_flow = 0.0
        s_flow = 0.0
        i_flow = 0.0
        loading_pct = 0.0
        p_loss = 0.0
        q_loss = 0.0
        
        if active and converged:
            dss.circuit.set_active_element(f"Line.{line_name}")
            powers = dss.cktelement.total_powers
            currents = dss.cktelement.currents_mag_ang
            losses = dss.cktelement.losses
            
            p_flow = float(powers[0] / 1000.0) if len(powers) > 0 else 0.0
            q_flow = float(powers[1] / 1000.0) if len(powers) > 1 else 0.0
            s_flow = float(math.sqrt(p_flow**2 + q_flow**2))
            i_flow = float(currents[0]) if len(currents) > 0 else 0.0
            
            p_loss = float(losses[0] / 1e6) if len(losses) > 0 else 0.0
            q_loss = float(losses[1] / 1e6) if len(losses) > 1 else 0.0
            
            norm_amps = dss.cktelement.norm_amps
            if norm_amps <= 0:
                norm_amps = 400.0
            loading_pct = float((i_flow / norm_amps) * 100.0)
        else:
            norm_amps = 400.0
            
        branch_data.append({
            "id": br_id,
            "name": f"Line {from_bus}-{to_bus}",
            "type": "line",
            "from_bus": from_bus,
            "to_bus": to_bus,
            "active": active,
            "p_flow_mw": p_flow,
            "q_flow_mvar": q_flow,
            "s_flow_mva": s_flow,
            "i_flow_a": i_flow,
            "rating_a": float(norm_amps),
            "loading_pct": loading_pct,
            "p_loss_mw": p_loss,
            "q_loss_mvar": q_loss,
            "tap": 0.0
        })
        
    # Transformers
    for tr_id, row in state.transformers.iterrows():
        active = bool(tr_id not in state.disabled_branches)
        from_bus = int(row["FromBus"])
        to_bus = int(row["ToBus"])
        
        p_flow = 0.0
        q_flow = 0.0
        s_flow = 0.0
        i_flow = 0.0
        loading_pct = 0.0
        p_loss = 0.0
        q_loss = 0.0
        tap = float(row["Tap"])
        
        if active and converged:
            dss.circuit.set_active_element(f"Transformer.T{tr_id}")
            powers = dss.cktelement.total_powers
            currents = dss.cktelement.currents_mag_ang
            losses = dss.cktelement.losses
            
            p_flow = float(powers[0] / 1000.0) if len(powers) > 0 else 0.0
            q_flow = float(powers[1] / 1000.0) if len(powers) > 1 else 0.0
            s_flow = float(math.sqrt(p_flow**2 + q_flow**2))
            i_flow = float(currents[0]) if len(currents) > 0 else 0.0
            
            p_loss = float(losses[0] / 1e6) if len(losses) > 0 else 0.0
            q_loss = float(losses[1] / 1e6) if len(losses) > 1 else 0.0
            
            norm_amps = dss.cktelement.norm_amps
            if norm_amps <= 0:
                norm_amps = 1000.0
            loading_pct = float((i_flow / norm_amps) * 100.0)
        else:
            norm_amps = 1000.0
            
        branch_data.append({
            "id": int(tr_id),
            "name": f"Transformer {from_bus}-{to_bus}",
            "type": "transformer",
            "from_bus": from_bus,
            "to_bus": to_bus,
            "active": active,
            "p_flow_mw": p_flow,
            "q_flow_mvar": q_flow,
            "s_flow_mva": s_flow,
            "i_flow_a": i_flow,
            "rating_a": float(norm_amps),
            "loading_pct": loading_pct,
            "p_loss_mw": p_loss,
            "q_loss_mvar": q_loss,
            "tap": tap
        })
        
    # Sort bus data by ID to make it clean
    bus_data.sort(key=lambda x: x["id"])
    
    return {
        "converged": converged,
        "losses": {
            "p_mw": losses_mw,
            "q_mvar": losses_mvar
        },
        "total_generation": {
            "p_mw": total_p_gen,
            "q_mvar": total_q_gen
        },
        "buses": bus_data,
        "branches": branch_data
    }

@app.post("/api/generator/update")
def update_generator(upd: GeneratorUpdate):
    """Updates generator setpoints or status in our memory state."""
    # Find matching row in state.generators
    matches = state.generators[state.generators["Bus"] == upd.bus]
    if len(matches) == 0:
        raise HTTPException(status_code=404, detail="Generator not found at specified bus")
    
    idx = matches.index[0]
    
    # If condenser, Pg setpoint is always 0. Update other fields.
    is_cond = bool(float(state.generators.loc[idx, "Pg"]) == 0.0)
    if not is_cond:
        state.generators.loc[idx, "Pg"] = upd.pg / 100.0  # Convert MW back to pu
        
    state.generators.loc[idx, "Vg"] = upd.vpu
    state.generators.loc[idx, "Status"] = 1 if upd.status else 0
    
    return {"status": "success", "message": f"Updated Generator/Condenser at Bus {upd.bus}"}

@app.post("/api/load/update")
def update_load(upd: LoadUpdate):
    """Updates load active/reactive power in our memory state."""
    matches = state.loads[state.loads["Bus"] == upd.bus]
    if len(matches) == 0:
        raise HTTPException(status_code=404, detail="Load not found at specified bus")
        
    idx = matches.index[0]
    state.loads.loc[idx, "Pd"] = upd.pd / 100.0  # Convert MW back to pu
    state.loads.loc[idx, "Qd"] = upd.qd / 100.0  # Convert Mvar back to pu
    
    return {"status": "success", "message": f"Updated Load at Bus {upd.bus}"}

@app.post("/api/transformer/update")
def update_transformer(upd: TransformerUpdate):
    """Updates transformer tap position in our memory state."""
    if upd.id not in state.transformers.index:
        raise HTTPException(status_code=404, detail="Transformer not found")
        
    state.transformers.loc[upd.id, "Tap"] = upd.tap
    return {"status": "success", "message": f"Updated Transformer {upd.id} tap to {upd.tap}"}

@app.post("/api/branch/toggle")
def toggle_branch(upd: BranchToggle):
    """Disables or enables a transmission line/transformer branch."""
    if upd.active:
        state.disabled_branches.discard(upd.id)
    else:
        state.disabled_branches.add(upd.id)
        
    return {"status": "success", "message": f"Branch {upd.id} active status set to {upd.active}"}

# Pydantic Schema for Unified Setpoint Updates
class SetpointUpdate(BaseModel):
    type: str  # "generator", "load", "transformer", "branch", "reset"
    bus: Optional[int] = None
    id: Optional[int] = None
    pg: Optional[float] = None
    vpu: Optional[float] = None
    pd: Optional[float] = None
    qd: Optional[float] = None
    tap: Optional[float] = None
    active: Optional[bool] = None

@app.get("/api/topology")
def get_topology():
    """Alias for GET /api/network to match frontend spec."""
    return get_network()

@app.get("/api/state")
def get_state():
    """Alias for POST /api/simulate as a GET request for frontend polling."""
    return simulate()

@app.post("/api/setpoint")
def update_setpoint(upd: SetpointUpdate):
    """Unified endpoint to update setpoints and return updated network state."""
    if upd.type == "generator":
        if upd.bus is None or upd.pg is None or upd.vpu is None or upd.active is None:
            raise HTTPException(status_code=400, detail="Missing generator parameters")
        update_generator(GeneratorUpdate(bus=upd.bus, pg=upd.pg, vpu=upd.vpu, status=upd.active))
    elif upd.type == "load":
        if upd.bus is None or upd.pd is None or upd.qd is None:
            raise HTTPException(status_code=400, detail="Missing load parameters")
        update_load(LoadUpdate(bus=upd.bus, pd=upd.pd, qd=upd.qd))
    elif upd.type == "transformer":
        if upd.id is None or upd.tap is None:
            raise HTTPException(status_code=400, detail="Missing transformer parameters")
        update_transformer(TransformerUpdate(id=upd.id, tap=upd.tap))
    elif upd.type == "branch":
        if upd.id is None or upd.active is None:
            raise HTTPException(status_code=400, detail="Missing branch parameters")
        toggle_branch(BranchToggle(id=upd.id, active=upd.active))
    elif upd.type == "reset":
        reset_network()
    else:
        raise HTTPException(status_code=400, detail="Invalid setpoint type")
    
    # Return current solved state immediately
    return simulate()

# Serve Frontend static files
static_dir = os.path.join(base_dir, "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static_assets", StaticFiles(directory=os.path.abspath(os.path.join(base_dir, "../assets"))), name="assets")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
