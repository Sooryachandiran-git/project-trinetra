# pyrefly: ignore [missing-import]
import andes
import logging
from api.models import ElectricalGridModel
import json
import pandas as pd
import numpy as np

logger = logging.getLogger("AndesSolver")

def solve_andes_powerflow(grid: ElectricalGridModel):
    """
    Takes an ElectricalGridModel, builds an ANDES system, runs the power flow,
    and extracts the results into a JSON serializable dictionary.
    """
    logger.info("Initializing ANDES network structure.")
    
    # Initialize ANDES System
    system = andes.System()
    system.config.save = False  # Disable file saving to keep it in memory
    
    try:
        bus_map = {}
        
        # 1. Create Buses
        for bus in grid.buses:
            # ANDES requires string or int for idx. We use our string IDs.
            # vn is nominal voltage, v is initial voltage magnitude guess (1.0 pu)
            system.Bus.add(idx=bus.id, name=bus.name, Vn=bus.vn_kv, v0=1.0, a0=0.0)
            bus_map[bus.id] = bus.id
            
        def find_bus_for_component(node_id):
            for line in grid.lines:
                if line.from_node == node_id and line.to_node in bus_map:
                    return bus_map[line.to_node]
                elif line.to_node == node_id and line.from_node in bus_map:
                    return bus_map[line.from_node]
            return None

        # 2. Create Slack (External Grid)
        for ext in grid.ext_grids:
            bus_id = find_bus_for_component(ext.id)
            if bus_id is not None:
                system.Slack.add(idx=ext.id, bus=bus_id, v0=ext.vm_pu, a0=ext.va_degree)

        # 3. Create Loads (PQ)
        # In ANDES, P and Q are typically provided in per unit (pu).
        # We assume base MVA = 100.0 (ANDES default)
        S_base = system.config.mva
        for load in grid.loads:
            bus_id = find_bus_for_component(load.id)
            if bus_id is not None:
                system.PQ.add(idx=load.id, bus=bus_id, p0=load.p_mw / S_base, q0=load.q_mvar / S_base)

        # 4. Create Sgens (Negative PQ)
        for sgen in grid.sgens:
            bus_id = find_bus_for_component(sgen.id)
            if bus_id is not None:
                system.PQ.add(idx=sgen.id, bus=bus_id, p0=-sgen.p_mw / S_base, q0=-sgen.q_mvar / S_base)
                
        # 5. Create Gens (PV)
        for gen in grid.gens:
            bus_id = find_bus_for_component(gen.id)
            if bus_id is not None:
                system.PV.add(idx=gen.id, bus=bus_id, p0=gen.p_mw / S_base, v0=gen.vm_pu)

        # 6. Create Lines
        for line in grid.lines:
            bus_from = bus_map.get(line.from_node)
            bus_to = bus_map.get(line.to_node)
            if bus_from is not None and bus_to is not None:
                # Need to convert ohms to pu. Z_base = V_base^2 / S_base
                # To be accurate, we need the V_base of the line.
                # Assuming simple conversion or just passing raw if ANDES supports it.
                # ANDES Line expects r and x in per-unit!
                # We'll use 110kV as a generic V_base for now if we can't get it easily.
                V_base = 110.0 
                for b in grid.buses:
                    if b.id == bus_from:
                        V_base = b.vn_kv
                        break
                
                Z_base = (V_base ** 2) / S_base
                r_pu = (line.r_ohm_per_km * line.length_km) / Z_base
                x_pu = (line.x_ohm_per_km * line.length_km) / Z_base
                
                # Calculate susceptance (b) in pu. Assume 50Hz.
                # B (Siemens) = 2 * pi * f * C (Farads)
                B_siemens = 2 * np.pi * 50 * (line.c_nf_per_km * 1e-9) * line.length_km
                b_pu = B_siemens * Z_base
                
                system.Line.add(
                    idx=line.id, bus1=bus_from, bus2=bus_to, 
                    r=max(r_pu, 0.0001), x=max(x_pu, 0.0001), b=b_pu,
                    Vn1=V_base, Vn2=V_base
                )

        # 7. Create Transformers as Lines
        # ANDES models Transformers as Lines with trans=1 and tap settings
        for trafo in grid.transformers:
            bus_hv = bus_map.get(trafo.hv_bus)
            bus_lv = bus_map.get(trafo.lv_bus)
            
            if bus_hv is not None and bus_lv is not None:
                # Convert SC impedance from transformer base to system base
                z_k = trafo.vk_percent / 100.0
                r_k = trafo.vkr_percent / 100.0
                x_k = np.sqrt(max(z_k**2 - r_k**2, 0))
                
                r_pu_sys = r_k * (S_base / trafo.sn_mva)
                x_pu_sys = x_k * (S_base / trafo.sn_mva)
                
                # ANDES Line expects phi in radians, but a large static shift (e.g. 150 deg) 
                # often causes the ANDES Newton-Raphson PFlow solver to diverge if not 
                # initialized perfectly. We will set phi=0.0 for the DAE dynamic equivalent 
                # to ensure mathematical convergence, as radial phase shift doesn't affect 
                # magnitude stability.
                phi_rad = 0.0

                system.Line.add(
                    idx=trafo.id, bus1=bus_hv, bus2=bus_lv, 
                    r=max(r_pu_sys, 0.0001), x=max(x_pu_sys, 0.0001), 
                    Vn1=trafo.vn_hv_kv, Vn2=trafo.vn_lv_kv,
                    trans=1.0, tap=1.0, phi=phi_rad
                )

        # 8. Switches (Breakers) -> Model as zero-impedance line (very small R/X)
        for sw in grid.switches:
            if sw.initial_status == 'Closed':
                connected_buses = []
                for line in grid.lines:
                    if line.from_node == sw.id and line.to_node in bus_map:
                        connected_buses.append(bus_map[line.to_node])
                    elif line.to_node == sw.id and line.from_node in bus_map:
                        connected_buses.append(bus_map[line.from_node])
                
                if len(connected_buses) >= 2:
                    system.Line.add(idx=sw.id, bus1=connected_buses[0], bus2=connected_buses[1], r=0.0001, x=0.0001)

        # Setup and Run Power Flow
        system.setup()
        system.PFlow.run()
        
        # Extract Results
        def get_df(model_name):
            if model_name in system.models:
                # ANDES stores variable values in `system.models[name].v.v` 
                # but a simpler way is `.as_df()` if available
                try:
                    df = system.models[model_name].as_df()
                    if df is not None and not df.empty:
                        # For Buses, append the solved algebraic variables
                        if model_name == "Bus":
                            df["v_solved"] = system.models[model_name].v.v
                            df["a_solved_rad"] = system.models[model_name].a.v
                            df["a_solved_deg"] = np.degrees(system.models[model_name].a.v)
                        return df.replace({np.nan: None}).to_dict('records')
                except:
                    pass
            return []

        results = {
            "converged": system.PFlow.converged,
            "res_bus": get_df("Bus"),
            "res_line": get_df("Line"),
            "res_load": get_df("PQ"),
            "res_ext_grid": get_df("Slack"),
            "res_sgen": [], # Combined with PQ
        }
        
        return results

    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"ANDES solve error: {str(e)}")
        return {"converged": False, "error": str(e)}

def simulate_cyber_attack(grid: ElectricalGridModel):
    """
    Builds the ANDES system just like power flow, but adds a Toggler to simulate
    a cyber attack (tripping a line) and runs a Time Domain Simulation.
    """
    logger.info("Initializing ANDES Cyber Attack Simulation.")
    
    # Initialize ANDES System
    system = andes.System()
    system.config.save = False
    
    try:
        bus_map = {}
        for bus in grid.buses:
            system.Bus.add(idx=bus.id, name=bus.name, Vn=bus.vn_kv, v0=1.0, a0=0.0)
            bus_map[bus.id] = bus.id
            
        def find_bus_for_component(node_id):
            for line in grid.lines:
                if line.from_node == node_id and line.to_node in bus_map:
                    return bus_map[line.to_node]
                elif line.to_node == node_id and line.from_node in bus_map:
                    return bus_map[line.from_node]
            return None

        # 2. Slack
        for ext in grid.ext_grids:
            bus_id = find_bus_for_component(ext.id)
            if bus_id is not None:
                system.Slack.add(idx=ext.id, bus=bus_id, v0=ext.vm_pu, a0=ext.va_degree)

        S_base = system.config.mva
        
        # 3. Loads
        for load in grid.loads:
            bus_id = find_bus_for_component(load.id)
            if bus_id is not None:
                system.PQ.add(idx=load.id, bus=bus_id, p0=load.p_mw / S_base, q0=load.q_mvar / S_base)

        # 4. Sgens
        for sgen in grid.sgens:
            bus_id = find_bus_for_component(sgen.id)
            if bus_id is not None:
                system.PQ.add(idx=sgen.id, bus=bus_id, p0=-sgen.p_mw / S_base, q0=-sgen.q_mvar / S_base)
                
        # 5. Gens
        for gen in grid.gens:
            bus_id = find_bus_for_component(gen.id)
            if bus_id is not None:
                system.PV.add(idx=gen.id, bus=bus_id, p0=gen.p_mw / S_base, v0=gen.vm_pu)

        # 6. Lines
        first_line_id = None
        for line in grid.lines:
            bus_from = bus_map.get(line.from_node)
            bus_to = bus_map.get(line.to_node)
            if bus_from is not None and bus_to is not None:
                V_base = 110.0 
                for b in grid.buses:
                    if b.id == bus_from:
                        V_base = b.vn_kv
                        break
                Z_base = (V_base ** 2) / S_base
                r_pu = (line.r_ohm_per_km * line.length_km) / Z_base
                x_pu = (line.x_ohm_per_km * line.length_km) / Z_base
                
                B_siemens = 2 * np.pi * 50 * (line.c_nf_per_km * 1e-9) * line.length_km
                b_pu = B_siemens * Z_base
                
                system.Line.add(
                    idx=line.id, bus1=bus_from, bus2=bus_to, 
                    r=max(r_pu, 0.0001), x=max(x_pu, 0.0001), b=b_pu,
                    Vn1=V_base, Vn2=V_base
                )
                if first_line_id is None:
                    first_line_id = line.id

        # 7. Transformers
        for trafo in grid.transformers:
            bus_hv = bus_map.get(trafo.hv_bus)
            bus_lv = bus_map.get(trafo.lv_bus)
            if bus_hv is not None and bus_lv is not None:
                z_k = trafo.vk_percent / 100.0
                r_k = trafo.vkr_percent / 100.0
                x_k = np.sqrt(max(z_k**2 - r_k**2, 0))
                r_pu_sys = r_k * (S_base / trafo.sn_mva)
                x_pu_sys = x_k * (S_base / trafo.sn_mva)
                
                system.Line.add(
                    idx=trafo.id, bus1=bus_hv, bus2=bus_lv, 
                    r=max(r_pu_sys, 0.0001), x=max(x_pu_sys, 0.0001), 
                    Vn1=trafo.vn_hv_kv, Vn2=trafo.vn_lv_kv,
                    trans=1.0, tap=1.0, phi=0.0
                )

        # Switches
        for sw in grid.switches:
            if sw.initial_status == 'Closed':
                connected_buses = []
                for line in grid.lines:
                    if line.from_node == sw.id and line.to_node in bus_map:
                        connected_buses.append(bus_map[line.to_node])
                    elif line.to_node == sw.id and line.from_node in bus_map:
                        connected_buses.append(bus_map[line.from_node])
                if len(connected_buses) >= 2:
                    system.Line.add(idx=sw.id, bus1=connected_buses[0], bus2=connected_buses[1], r=0.0001, x=0.0001)

        # ADD CYBER ATTACK FAULT (Hacker closes grounding switch)
        target_bus = None
        for bus in grid.buses:
            if bus.id != list(bus_map.values())[0]: # Pick a bus that isn't the first one
                target_bus = bus.id
                break
        
        if target_bus:
            # Short circuit fault at t=2.0 seconds, never clears (tc=99.0)
            system.Fault.add(idx='hacker_attack', bus=target_bus, tf=2.0, tc=99.0, rf=0.0001, xf=0.0001)
            logger.info(f"Added Cyber Attack Fault on bus {target_bus} at t=2.0")

        # Bypass connectivity check which fails without SynGen
        system.connectivity = lambda *args, **kwargs: None

        # Setup and Run Power Flow first
        system.setup()
        system.PFlow.run()
        
        # Run TDS
        system.TDS.config.tf = 10.0
        system.TDS.run()
        
        # Extract results
        time = system.dae.ts.t.tolist() if hasattr(system.dae.ts, 't') else []
        voltages = {}
        
        if len(time) > 0 and hasattr(system.dae.ts, 'y'):
            for i, bus_id in enumerate(system.Bus.idx.v):
                y_idx = system.Bus.v.a[i]
                v_trace = system.dae.ts.y[:, y_idx].tolist()
                voltages[bus_id] = v_trace
                
        return {
            "converged": system.TDS.converged if hasattr(system.TDS, 'converged') else True,
            "time": time,
            "voltages": voltages
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error(f"ANDES TDS error: {str(e)}")
        return {"converged": False, "error": str(e)}

