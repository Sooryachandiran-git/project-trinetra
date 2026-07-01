/**
 * JSON Compiler Utility
 * Converts the visual React Flow nodes/edges into a mathematical layout
 * suitable for the FastAPI backend (Pandapower & OpenPLC orchestration).
 */

// Helper to safely parse numbers, preserving 0.0 values which are falsy in JS
const parseNum = (val, defaultVal) => {
  if (val === undefined || val === null || val === '') return defaultVal;
  const parsed = parseFloat(val);
  return isNaN(parsed) ? defaultVal : parsed;
};

export const compileGridToJSON = (nodes, edges) => {
  const payload = {
    metadata: {
      generated_at: new Date().toISOString(),
      version: '1.0',
      topology_id: `run_${Math.floor(Date.now() / 1000)}`,
      total_nodes: nodes.length,
      total_edges: edges.length
    },
    electrical_grid: {
      buses: [],
      ext_grids: [],
      loads: [],
      lines: [],
      switches: [], // Circuit breakers
      transformers: [],
      transformers3w: [],
      sgens: [],
      gens: [],
      shunts: []
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
          vn_kv: parseNum(node.data.vn_kv, 110.0)
        });
        break;
      
      case 'ext_grid':
        payload.electrical_grid.ext_grids.push({
          id: node.id,
          name: node.data.label || 'External Grid',
          vm_pu: parseNum(node.data.vm_pu, 1.0),
          va_degree: parseNum(node.data.va_degree, 0.0),
          // ext_grid must connect to a bus. We'll find that in the edges.
        });
        break;

      case 'load':
        payload.electrical_grid.loads.push({
          id: node.id,
          name: node.data.label || 'Load',
          p_mw: parseNum(node.data.p_mw, 50.0),
          q_mvar: parseNum(node.data.q_mvar, 10.0)
        });
        break;

      case 'breaker':
        payload.electrical_grid.switches.push({
          id: node.id,
          name: node.data.label || 'Breaker',
          initial_status: node.data.status === 'Closed' || node.data.status === 1 ? 'Closed' : 'Open'
        });
        break;

      case 'transmission_line': {
        const inEdge = edges.find(e => e.target === node.id);
        const outEdge = edges.find(e => e.source === node.id);
        payload.electrical_grid.lines.push({
          id: node.id,
          name: node.data.label || 'Transmission Line',
          length_km: parseNum(node.data.length_km, 10.0),
          r_ohm_per_km: parseNum(node.data.r_ohm_per_km, 0.1),
          x_ohm_per_km: parseNum(node.data.x_ohm_per_km, 0.2),
          type: node.data.type || 'generic_line',
          from_node: inEdge ? inEdge.source : '',
          to_node: outEdge ? outEdge.target : ''
        });
        break;
      }

      case 'transformer':
        payload.electrical_grid.transformers.push({
          id: node.id,
          name: node.data.label || 'Transformer',
          std_type: node.data.std_type || '160 MVA 380/110 kV',
          sn_mva: parseNum(node.data.sn_mva, 100.0),
          vk_percent: parseNum(node.data.vk_percent, 10.0),
          vkr_percent: parseNum(node.data.vkr_percent, 0.1),
          hv_bus: '', // We will populate these in edge processing
          lv_bus: ''
        });
        break;

      case 'transformer3w':
        payload.electrical_grid.transformers3w.push({
          id: node.id,
          name: node.data.label || '3W Transformer',
          std_type: node.data.std_type || '63/25/38 MVA 110/20/10 kV',
          hv_bus: '',
          mv_bus: '',
          lv_bus: ''
        });
        break;

      case 'sgen':
        payload.electrical_grid.sgens.push({
          id: node.id,
          name: node.data.label || 'Static Generator',
          p_mw: parseNum(node.data.p_mw, 10.0),
          q_mvar: parseNum(node.data.q_mvar, 0.0)
        });
        break;

      case 'gen':
        payload.electrical_grid.gens.push({
          id: node.id,
          name: node.data.label || 'Generator',
          p_mw: parseNum(node.data.p_mw, 100.0),
          vm_pu: parseNum(node.data.vm_pu, 1.0)
        });
        break;

      case 'shunt':
        payload.electrical_grid.shunts.push({
          id: node.id,
          name: node.data.label || 'Shunt',
          p_mw: parseNum(node.data.p_mw, 0.0),
          q_mvar: parseNum(node.data.q_mvar, 19.0),
          vn_kv: parseNum(node.data.vn_kv, 110.0),
          step: parseInt(node.data.step) || 1
        });
        break;

      case 'ied':
        payload.scada_system.ieds.push({
          id: node.id,
          name: node.data.label || 'IED',
          port: parseInt(node.data.port) || 5020,
          num_breakers: parseInt(node.data.num_breakers) || 1,
          st_code: node.data.st_code || null,
          monitors_bus: node.data.monitors_bus || null,
          protocols: ['ModbusTCP']
        });
        break;

      case 'network_switch':
      case 'gps_clock':
      case 'scada_server':
        // These are purely visual/cyber nodes for the UI layout, 
        // they don't affect the physical Pandapower engine directly (yet)
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

    // If this edge connects TO or FROM a transformer, we need to map the bus IDs
    const trafo = payload.electrical_grid.transformers.find(t => t.id === targetNode.id || t.id === sourceNode.id);
    if (trafo) {
      if (sourceNode.type === 'bus' && targetNode.type === 'transformer') {
        trafo.hv_bus = sourceNode.id;
      } else if (sourceNode.type === 'transformer' && targetNode.type === 'bus') {
        trafo.lv_bus = targetNode.id;
      }
      return; // Handled as trafo connection, don't add generic line
    }

    const trafo3w = payload.electrical_grid.transformers3w.find(t => t.id === targetNode.id || t.id === sourceNode.id);
    if (trafo3w) {
      if (sourceNode.type === 'bus' && targetNode.type === 'transformer3w') {
        trafo3w.hv_bus = sourceNode.id; // Assuming top is HV
      } else if (sourceNode.type === 'transformer3w' && targetNode.type === 'bus') {
        // Need logic for MV vs LV based on handle ID... for now just set lv_bus
        trafo3w.lv_bus = targetNode.id;
      }
      return; 
    }

    // Electrical Logic: Everything else is essentially a line/cable/switch
    // (In a full Pandapower model, nodes attach to buses. A line connects two buses).
    // If it's connecting a Bus to an ExtGrid, Load, Sgen, Gen, it's just a direct attachment, not a Line model in pandapower.
    // Wait, the backend builder needs to know which bus an element connects to. 
    // Right now, the backend `pandapower_solver.py` looks at `lines` to figure out attachments for loads/ext_grids? 
    // Let's check `pandapower_solver.py`.
    payload.electrical_grid.lines.push({
      id: edge.id,
      from_node: sourceNode.id,
      to_node: targetNode.id,
      length_km: sourceNode.type === 'transmission_line' ? parseFloat(sourceNode.data.length_km) : 1.0, 
      type: sourceNode.type === 'transmission_line' ? sourceNode.data.type : 'generic_line'
    });
  });

  return payload;
};
