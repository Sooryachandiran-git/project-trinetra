import pandapower as pp
import logging
from api.models import DeploymentPayload, LineModel, BusModel, SwitchModel, LoadModel, ExtGridModel
from typing import Dict, Any, List, Optional

# Set up detailed logging for the physics engine
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PandapowerCore")

def build_pandapower_network(payload: DeploymentPayload):
    """
    Takes the purely topographical Pydantic payload from React Flow and translates it 
    into a live Pandapower network for physical emulation.
    """
    logger.info("Initializing empty Pandapower network structure.")
    net = pp.create_empty_network()
    
    # Map React Flow UUIDs to Pandapower integer IDs
    bus_map: Dict[str, int] = {}
    
    diagnostics: Dict[str, Any] = {
        "buses_created": 0,
        "ext_grids_created": 0,
        "loads_created": 0,
        "lines_created": 0,
        "switches_created": 0,
        "errors": []
    }

    try:
        # 1. Create Buses
        for bus in payload.electrical_grid.buses:
            pp_bus_id = pp.create_bus(net, name=bus.name, vn_kv=bus.vn_kv, type="b")
            bus_map[bus.id] = pp_bus_id
            diagnostics["buses_created"] += 1

        # HELPER: Find the nearest Bus ID for any given node UUID by traversing edges
        def find_nearest_bus(node_id: str, visited: Optional[set] = None) -> Optional[int]:
            if visited is None: visited = set()
            if node_id in bus_map: return bus_map[node_id]
            if node_id in visited: return None
            visited.add(node_id)
            
            # Search through the grid topography (edges represented as lines in our model)
            for line in payload.electrical_grid.lines:
                if line.from_node == node_id:
                    res = find_nearest_bus(line.to_node, visited)
                    if res is not None: return res
                if line.to_node == node_id:
                    res = find_nearest_bus(line.from_node, visited)
                    if res is not None: return res
            
            # Also check through switches (breakers) to find a connected bus
            for sw in payload.electrical_grid.switches:
                # This is a bit complex as switches aren't 'edges' but 'nodes'
                # In our React Flow, a switch is a node with an incoming and outgoing edge.
                # So the recursive search through lines already covers the 'path'
                pass

            return None

        # 2. Create External Grids
        for ext in payload.electrical_grid.ext_grids:
            bus_id = find_nearest_bus(ext.id)
            if bus_id is not None:
                pp.create_ext_grid(net, bus=bus_id, vm_pu=ext.vm_pu, va_degree=ext.va_degree, name=ext.name)
                diagnostics["ext_grids_created"] += 1
            else:
                diagnostics["errors"].append(f"External Grid {ext.name} is not connected to a Bus.")

        # 3. Create Loads
        for load in payload.electrical_grid.loads:
            bus_id = find_nearest_bus(load.id)
            if bus_id is not None:
                pp.create_load(net, bus=bus_id, p_mw=load.p_mw, q_mvar=load.q_mvar, name=load.name)
                diagnostics["loads_created"] += 1
            else:
                diagnostics["errors"].append(f"Load {load.name} is not connected to a Bus.")

        # 4. Create Physical Lines (Transmission Lines)
        line_map: Dict[str, int] = {}
        for line_node in payload.electrical_grid.lines:
            bus_a = find_nearest_bus(line_node.from_node)
            bus_b = find_nearest_bus(line_node.to_node)
            
            if bus_a is not None and bus_b is not None and bus_a != bus_b:
                pp_line_id = pp.create_line_from_parameters(
                    net, from_bus=bus_a, to_bus=bus_b, 
                    length_km=line_node.length_km,
                    r_ohm_per_km=line_node.r_ohm_per_km,
                    x_ohm_per_km=line_node.x_ohm_per_km,
                    c_nf_per_km=0, max_i_ka=1,
                    name=line_node.name
                )
                line_map[line_node.id] = pp_line_id
                diagnostics["lines_created"] += 1

        # 5. Create Switches (Breaker isolation logic)
        for sw in payload.electrical_grid.switches:
            if sw.initial_status == 'Open':
                # Find any physical lines directly connected to this switch and trip them
                for line_node in payload.electrical_grid.lines:
                    if line_node.from_node == sw.id or line_node.to_node == sw.id:
                        if line_node.id in line_map:
                            line_idx = line_map[line_node.id]
                            net.line.at[line_idx, 'in_service'] = False
                            logger.info(f"Breaker {sw.name} is OPEN. Isolating segment {line_node.name}.")
            diagnostics["switches_created"] += 1

        # --- EXECUTE POWER FLOW ---
        if diagnostics["buses_created"] > 0 and diagnostics["ext_grids_created"] > 0:
            logger.info("Executing Newton-Raphson power flow simulation...")
            pp.runpp(net)
            
            # Format results and MAPPINGS for the simulation engine
            diagnostics["mappings"] = {
                "bus_map": bus_map,
                "line_map": line_map
            }
            diagnostics["results"] = {
                "bus_voltages_pu": net.res_bus.vm_pu.to_dict(),
                "bus_names": net.bus.name.to_dict(),
                "converged": True if hasattr(net, 'res_bus') else False
            }
        else:
            diagnostics["results"] = {"converged": False, "reason": "No power source found in the circuit."}

    except Exception as e:
        logger.error(f"Pandapower error: {str(e)}")
        diagnostics["results"] = {"converged": False, "error": str(e)}

    return net, diagnostics
