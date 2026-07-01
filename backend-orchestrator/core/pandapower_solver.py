import pandapower as pp
import logging
from api.models import ElectricalGridModel
import json
import pandas as pd
import numpy as np

logger = logging.getLogger("PandapowerSolver")

def solve_pure_pandapower(grid: ElectricalGridModel):
    """
    Takes an ElectricalGridModel, builds a pure pandapower network, runs the power flow,
    and extracts the results into a JSON serializable dictionary.
    """
    logger.info("Initializing pure Pandapower network structure.")
    net = pp.create_empty_network()
    
    bus_map = {}
    
    try:
        # 1. Create Buses
        for bus in grid.buses:
            pp_bus_id = pp.create_bus(net, name=bus.name, vn_kv=bus.vn_kv, type="b")
            bus_map[bus.id] = pp_bus_id

        # Helper to find bus mapping
        def get_bus_idx(node_id):
            # For lines, we just need to find the node_id in bus_map.
            # But wait, lines connect buses directly in pure pandapower (if no breakers)
            # Actually, the frontend allows lines to connect any two nodes, but for a valid grid,
            # lines must connect two buses. The frontend should enforce this or we resolve it here.
            # In the pure pandapower mode, we assume the user directly connected buses with lines, or buses with breakers.
            return bus_map.get(node_id)
            
        def find_bus_for_component(node_id):
            # In pure pandapower builder, a load or ext_grid is attached directly to a bus
            # so the node_id in the link could be from a component to a bus.
            # We must traverse the lines to find the bus connected to this component.
            for line in grid.lines:
                if line.from_node == node_id and line.to_node in bus_map:
                    return bus_map[line.to_node]
                elif line.to_node == node_id and line.from_node in bus_map:
                    return bus_map[line.from_node]
            return None

        # 2. Create External Grids
        for ext in grid.ext_grids:
            bus_id = find_bus_for_component(ext.id)
            if bus_id is not None:
                pp.create_ext_grid(net, bus=bus_id, vm_pu=ext.vm_pu, va_degree=ext.va_degree, name=ext.name)

        # 3. Create Loads
        for load in grid.loads:
            bus_id = find_bus_for_component(load.id)
            if bus_id is not None:
                pp.create_load(net, bus=bus_id, p_mw=load.p_mw, q_mvar=load.q_mvar, name=load.name)

        # 4. Create Sgens
        for sgen in grid.sgens:
            bus_id = find_bus_for_component(sgen.id)
            if bus_id is not None:
                pp.create_sgen(net, bus=bus_id, p_mw=sgen.p_mw, q_mvar=sgen.q_mvar, name=sgen.name)
                
        # 5. Create Gens
        for gen in grid.gens:
            bus_id = find_bus_for_component(gen.id)
            if bus_id is not None:
                pp.create_gen(net, bus=bus_id, p_mw=gen.p_mw, vm_pu=gen.vm_pu, name=gen.name)

        # 6. Create Lines
        for line in grid.lines:
            # Check if this line is actually connecting two buses
            bus_from = bus_map.get(line.from_node)
            bus_to = bus_map.get(line.to_node)
            if bus_from is not None and bus_to is not None:
                # It's a real line between two buses
                if line.type != "generic_line":
                    # Use standard type if available and exists in pp
                    try:
                        pp.create_line(net, from_bus=bus_from, to_bus=bus_to, length_km=line.length_km, std_type=line.type, name=f"Line {line.from_node}-{line.to_node}")
                    except:
                        pp.create_line_from_parameters(net, from_bus=bus_from, to_bus=bus_to, length_km=line.length_km, r_ohm_per_km=line.r_ohm_per_km, x_ohm_per_km=line.x_ohm_per_km, c_nf_per_km=line.c_nf_per_km, max_i_ka=line.max_i_ka, name=f"Line {line.id}")
                else:
                    pp.create_line_from_parameters(net, from_bus=bus_from, to_bus=bus_to, length_km=line.length_km, r_ohm_per_km=line.r_ohm_per_km, x_ohm_per_km=line.x_ohm_per_km, c_nf_per_km=line.c_nf_per_km, max_i_ka=line.max_i_ka, name=f"Line {line.id}")

        # 7. Create Transformers
        for trafo in grid.transformers:
            # We already have hv_bus and lv_bus node IDs populated by the frontend
            bus_hv = bus_map.get(trafo.hv_bus)
            bus_lv = bus_map.get(trafo.lv_bus)
            
            if bus_hv is not None and bus_lv is not None:
                if getattr(trafo, 'use_std_type', True):
                    pp.create_transformer(net, hv_bus=bus_hv, lv_bus=bus_lv, std_type=trafo.std_type, name=trafo.name)
                else:
                    pp.create_transformer_from_parameters(
                        net, hv_bus=bus_hv, lv_bus=bus_lv, 
                        sn_mva=trafo.sn_mva, vn_hv_kv=trafo.vn_hv_kv, vn_lv_kv=trafo.vn_lv_kv, 
                        vk_percent=trafo.vk_percent, vkr_percent=trafo.vkr_percent, 
                        pfe_kw=trafo.pfe_kw, i0_percent=trafo.i0_percent, 
                        shift_degree=trafo.shift_degree, name=trafo.name
                    )
                
        # 8. Create 3W Transformers
        for trafo3w in grid.transformers3w:
            bus_hv = bus_map.get(trafo3w.hv_bus)
            bus_mv = bus_map.get(trafo3w.mv_bus)
            bus_lv = bus_map.get(trafo3w.lv_bus)
            
            # Since MV might not be explicitly drawn in a simple drag-drop, fallback or just enforce
            if bus_hv is not None and bus_lv is not None and bus_mv is not None:
                pp.create_transformer3w(net, hv_bus=bus_hv, mv_bus=bus_mv, lv_bus=bus_lv, std_type=trafo3w.std_type, name=trafo3w.name)

        # 9. Create Switches (Breakers)
        for sw in grid.switches:
            connected_buses = []
            for line in grid.lines:
                if line.from_node == sw.id and line.to_node in bus_map:
                    connected_buses.append(bus_map[line.to_node])
                elif line.to_node == sw.id and line.from_node in bus_map:
                    connected_buses.append(bus_map[line.from_node])
            
            if len(connected_buses) >= 2:
                bus_a, bus_b = connected_buses[0], connected_buses[1]
                is_closed = (sw.initial_status == 'Closed')
                pp.create_switch(net, bus=bus_a, element=bus_b, et="b", closed=is_closed, name=sw.name)

        # RUN POWER FLOW
        if len(net.bus) > 0 and len(net.ext_grid) > 0:
            pp.runpp(net)
            
            # Serialize results
            def clean_df(df):
                if df is None or df.empty:
                    return []
                # Replace NaN with None for JSON serialization
                return df.replace({np.nan: None}).to_dict('records')

            results = {
                "converged": True,
                "res_bus": clean_df(net.res_bus),
                "res_line": clean_df(net.res_line),
                "res_trafo": clean_df(net.res_trafo),
                "res_trafo3w": clean_df(net.res_trafo3w) if hasattr(net, 'res_trafo3w') else [],
                "res_load": clean_df(net.res_load),
                "res_ext_grid": clean_df(net.res_ext_grid),
                "res_sgen": clean_df(net.res_sgen) if hasattr(net, 'res_sgen') else [],
                "res_gen": clean_df(net.res_gen) if hasattr(net, 'res_gen') else [],
            }
            return results
        else:
            return {"converged": False, "error": "Network must have at least one bus and one external grid."}

    except Exception as e:
        logger.error(f"Pandapower pure solve error: {str(e)}")
        return {"converged": False, "error": str(e)}
