/**
 * JSON Compiler Utility
 * Converts the visual React Flow nodes/edges into a mathematical layout
 * suitable for the FastAPI backend (Pandapower & OpenPLC orchestration).
 */

export const compileGridToJSON = (nodes, edges) => {
  const payload = {
    metadata: {
      generated_at: new Date().toISOString(),
      version: '1.0',
      total_nodes: nodes.length,
      total_edges: edges.length
    },
    electrical_grid: {
      buses: [],
      ext_grids: [],
      loads: [],
      lines: [],
      switches: [] // Circuit breakers
    },
    scada_system: {
      ieds: [],
      control_mappings: []
    }
  };

  // 1. Process Nodes
  nodes.forEach(node => {
    switch (node.type) {
      case 'bus':
        payload.electrical_grid.buses.push({
          id: node.id,
          name: node.data.label || 'Bus',
          vn_kv: parseFloat(node.data.vn_kv) || 110.0
        });
        break;
      
      case 'ext_grid':
        payload.electrical_grid.ext_grids.push({
          id: node.id,
          name: node.data.label || 'External Grid',
          vm_pu: parseFloat(node.data.vm_pu) || 1.0,
          va_degree: parseFloat(node.data.va_degree) || 0.0,
          // ext_grid must connect to a bus. We'll find that in the edges.
        });
        break;

      case 'load':
        payload.electrical_grid.loads.push({
          id: node.id,
          name: node.data.label || 'Load',
          p_mw: parseFloat(node.data.p_mw) || 50.0,
          q_mvar: parseFloat(node.data.q_mvar) || 10.0
        });
        break;

      case 'breaker':
        payload.electrical_grid.switches.push({
          id: node.id,
          name: node.data.label || 'Breaker',
          initial_status: node.data.status === 'Closed' || node.data.status === 1 ? 'Closed' : 'Open'
        });
        break;

      case 'ied':
        payload.scada_system.ieds.push({
          id: node.id,
          name: node.data.label || 'IED',
          port: parseInt(node.data.port) || 5020,
          protocols: ['ModbusTCP']
        });
        break;
        
      default:
        console.warn(`Unknown node type: ${node.type}`);
    }
  });

  // 2. Process Edges (Topology Mapping)
  edges.forEach(edge => {
    const sourceNode = nodes.find(n => n.id === edge.source);
    const targetNode = nodes.find(n => n.id === edge.target);

    if (!sourceNode || !targetNode) return;

    // SCADA Logic: If an IED points to a Breaker, it's a control mapping
    if (sourceNode.type === 'ied' && targetNode.type === 'breaker') {
      payload.scada_system.control_mappings.push({
        ied_id: sourceNode.id,
        breaker_id: targetNode.id,
        type: 'modbus_coil'
      });
      return;
    }

    // Electrical Logic: Everything else is essentially a line/cable/switch
    // (In a full Pandapower model, nodes attach to buses. A line connects two buses).
    // For this compiler, we just dump the raw electrical connections.
    payload.electrical_grid.lines.push({
      id: edge.id,
      from_node: sourceNode.id,
      to_node: targetNode.id,
      length_km: 1.0, // Default for now
      type: 'generic_line'
    });
  });

  return payload;
};
