import pandapower as pp
import logging
from api.models import DeploymentPayload
from typing import Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PandapowerCore")

def build_pandapower_network(payload: DeploymentPayload):
    """
    Translates the visual graph into a strict Pandapower physical network.
    Enforces:
    - All components (Load, ExtGrid) MUST plug into a Bus.
    - Breakers (Switches) MUST sit between two Buses.
    """
    logger.info("Initializing strict physics Pandapower network structure.")
    net = pp.create_empty_network()
    
    bus_map: Dict[str, int] = {}
    switch_map: Dict[str, int] = {}
    
    diagnostics = {
        "buses_created": 0,
        "ext_grids_created": 0,
        "loads_created": 0,
        "switches_created": 0,
        "errors": []
    }

    try:
        # 1. Create Buses
        for bus in payload.electrical_grid.buses:
            pp_bus_id = pp.create_bus(net, name=bus.name, vn_kv=bus.vn_kv, type="b")
            bus_map[bus.id] = pp_bus_id
            diagnostics["buses_created"] += 1

        # HELPER: Find exactly which Bus a node is physically wired to.
        # We only traverse pure edges (which are represented as 'generic_line' in the payload).
        # We DO NOT traverse through Switches. A Switch separates two buses.
        def find_bus_for_component(node_id: str) -> Optional[int]:
            for line in payload.electrical_grid.lines:
                target_id = None
                if line.from_node == node_id:
                    target_id = line.to_node
                elif line.to_node == node_id:
                    target_id = line.from_node

                if target_id is not None:
                    if target_id in bus_map:
                        return bus_map[target_id]
            return None

        # 2. Create External Grids -> attach to Bus
        for ext in payload.electrical_grid.ext_grids:
            bus_id = find_bus_for_component(ext.id)
            if bus_id is not None:
                pp.create_ext_grid(net, bus=bus_id, vm_pu=ext.vm_pu, va_degree=ext.va_degree, name=ext.name)
                diagnostics["ext_grids_created"] += 1
            else:
                diagnostics["errors"].append(f"External Grid {ext.name} MUST be connected to a Bus.")

        # 3. Create Loads -> attach to Bus
        for load in payload.electrical_grid.loads:
            bus_id = find_bus_for_component(load.id)
            if bus_id is not None:
                pp.create_load(net, bus=bus_id, p_mw=load.p_mw, q_mvar=load.q_mvar, name=load.name)
                diagnostics["loads_created"] += 1
            else:
                diagnostics["errors"].append(f"Load {load.name} MUST be connected to a Bus.")

        # 4. Create True Mathematical Switches (bus-to-bus)
        for sw in payload.electrical_grid.switches:
            # A switch must connect exactly two buses. Find both.
            connected_buses = []
            for line in payload.electrical_grid.lines:
                if line.from_node == sw.id:
                    connected_buses.append(find_bus_for_component(line.to_node) or (bus_map.get(line.to_node)))
                elif line.to_node == sw.id:
                    connected_buses.append(find_bus_for_component(line.from_node) or (bus_map.get(line.from_node)))
            
            # Filter nones
            connected_buses = [b for b in connected_buses if b is not None]
            
            if len(connected_buses) >= 2:
                bus_a, bus_b = connected_buses[0], connected_buses[1]
                if bus_a != bus_b:
                    is_closed = (sw.initial_status == 'Closed')
                    # Create actual Pandapower switch
                    pp_sw_id = pp.create_switch(net, bus=bus_a, element=bus_b, et="b", closed=is_closed, name=sw.name)
                    switch_map[sw.id] = pp_sw_id
                    diagnostics["switches_created"] += 1
            else:
                diagnostics["errors"].append(f"Breaker {sw.name} MUST sit between two Buses geographically.")

        # --- EXECUTE INITIAL POWER FLOW ---
        if diagnostics["buses_created"] > 0 and diagnostics["ext_grids_created"] > 0:
            logger.info("Executing initial Newton-Raphson power flow simulation...")
            try:
                pp.runpp(net)
                diagnostics["results"] = {"converged": True}
            except Exception as e:
                diagnostics["results"] = {"converged": False, "reason": str(e)}
            
            # ── Build ied_bus_map ──────────────────────────────────────────────
            # Maps each IED id → pandapower integer bus index.
            # Uses IEDModel.monitors_bus (React node id) looked up in bus_map.
            # This enables per-bus physics truth (bus_v_pu_true) per IED in the
            # simulation tick — the foundation of the dual-source anomaly signal.
            ied_bus_map: Dict[str, int] = {}
            for ied in payload.scada_system.ieds:
                if ied.monitors_bus and ied.monitors_bus in bus_map:
                    # IED explicitly wired to a specific bus on the canvas
                    ied_bus_map[ied.id] = bus_map[ied.monitors_bus]
                    logger.info(
                        f"IED '{ied.name}' monitors bus '{ied.monitors_bus}' "
                        f"→ pandapower index {bus_map[ied.monitors_bus]}"
                    )
                else:
                    # Fallback: use index 0 (source/slack bus) if not configured
                    ied_bus_map[ied.id] = 0
                    logger.warning(
                        f"IED '{ied.name}' has no monitors_bus set. "
                        f"Defaulting to bus index 0. "
                        f"Set monitors_bus in the IED modal for accurate per-bus truth."
                    )

            # Format MAPPINGS for the simulation engine
            diagnostics["mappings"] = {
                "bus_map":     bus_map,
                "switch_map":  switch_map,
                "ied_bus_map": ied_bus_map   # ← NEW: per-IED localized bus index
            }
        else:
            diagnostics["results"] = {"converged": False, "reason": "No valid power source attached to a bus."}

    except Exception as e:
        logger.error(f"Pandapower error: {str(e)}")
        diagnostics["results"] = {"converged": False, "error": str(e)}

    return net, diagnostics
