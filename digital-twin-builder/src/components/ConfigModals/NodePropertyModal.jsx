import React, { useState, useEffect } from 'react';
import useGridStore from '../../store/useGridStore';
import { X, Save } from 'lucide-react';

const NodePropertyModal = () => {
  const { isModalOpen, selectedNodeId, nodes, updateNodeData, closeModal } = useGridStore();
  const [formData, setFormData] = useState({});

  const node = nodes.find((n) => n.id === selectedNodeId);

  // Initialize form data when a new node is selected
  useEffect(() => {
    let timeoutId;
    if (node && isModalOpen) {
      timeoutId = setTimeout(() => {
        setFormData({ ...node.data });
      }, 0);
    }
    return () => clearTimeout(timeoutId);
  }, [node, isModalOpen]);

  if (!isModalOpen || !node) return null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = () => {
    updateNodeData(node.id, formData);
    closeModal();
  };

  // Render different input fields based on Node Type
  const renderFields = () => {
    switch (node.type) {
      case 'ext_grid':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Voltage Magnitude (vm_pu)</label>
              <input
                type="number"
                step="0.01"
                name="vm_pu"
                value={formData.vm_pu || '1.00'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-slate-500 mt-1">Per-unit voltage (Active generation)</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Voltage Angle (va_degree)</label>
              <input
                type="number"
                step="0.1"
                name="va_degree"
                value={formData.va_degree || '0.0'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        );
      case 'bus':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nominal Voltage (vn_kv)</label>
              <input
                type="number"
                step="0.1"
                name="vn_kv"
                value={formData.vn_kv || '110.0'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-slate-500 mt-1">Kilovolts</p>
            </div>
          </div>
        );
      case 'load':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Active Power (P in MW)</label>
              <input
                type="number"
                step="0.1"
                name="p_mw"
                value={formData.p_mw || '50.0'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Reactive Power (Q in MVar)</label>
              <input
                type="number"
                step="0.1"
                name="q_mvar"
                value={formData.q_mvar || '10.0'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        );
      case 'shunt':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Active Power (P in MW)</label>
              <input
                type="number"
                step="0.1"
                name="p_mw"
                value={formData.p_mw || '0.0'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-[10px] text-slate-400 mt-1">At nominal voltage (v=1.0 pu)</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Reactive Power (Q in MVar)</label>
              <input
                type="number"
                step="0.1"
                name="q_mvar"
                value={formData.q_mvar || '19.0'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-[10px] text-slate-400 mt-1">At nominal voltage (v=1.0 pu)</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Nominal Voltage (vn_kv)</label>
              <input
                type="number"
                step="0.1"
                name="vn_kv"
                value={formData.vn_kv || '110.0'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Step</label>
              <input
                type="number"
                step="1"
                name="step"
                value={formData.step || '1'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-[10px] text-slate-400 mt-1">Number of active shunt steps (integer)</p>
            </div>
          </div>
        );
      case 'breaker':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Initial Status</label>
              <select
                name="status"
                value={formData.status || 'Closed'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="Closed">Closed (Conducting)</option>
                <option value="Open">Open (Isolated)</option>
              </select>
            </div>
          </div>
        );
      case 'ied':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Modbus Binding Port</label>
              <input
                type="number"
                name="port"
                value={formData.port || '5020'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-slate-500 mt-1">Docker internal binding port (e.g. 5020, 5021)</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Number of Controlled Breakers</label>
              <input
                type="number"
                name="num_breakers"
                min="1"
                max="8"
                value={formData.num_breakers || '1'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-slate-500 mt-1">Controls how many connection handles are visible.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Structured Text (ST) Code</label>
              <textarea
                name="st_code"
                rows="6"
                value={formData.st_code || ''}
                onChange={handleChange}
                placeholder="PROGRAM trinetra_logic...\n  VAR\n    breaker_1 AT %QX0.0 : BOOL;\n  END_VAR\n..."
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-xs bg-slate-50"
              />
              <p className="text-[10px] text-slate-400 mt-1 italic">If left empty, a default protection program will be generated.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Monitors Bus (Physics Ground Truth)</label>
              <select
                name="monitors_bus"
                value={formData.monitors_bus || ''}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
              >
                <option value="">-- Global Fallback (Default) --</option>
                {nodes.filter(n => n.type === 'bus').map(b => (
                  <option key={b.id} value={b.id}>
                    {b.data.label ? `${b.data.label} (${b.id.substring(0, 8)})` : b.id}
                  </option>
                ))}
              </select>
              <p className="text-[10px] text-slate-400 mt-1 italic">
                Links this IED's voltage measurements to a specific physical bus in the grid.
              </p>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
               <p className="text-[11px] text-blue-700 font-medium leading-relaxed">
                 Connect this IED to one or more Circuit Breakers using edges to establish control.
               </p>
            </div>
          </div>
        );
      case 'transmission_line':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Standard Type</label>
              <input
                type="text"
                name="type"
                value={formData.type || 'generic_line'}
                onChange={handleChange}
                placeholder="e.g. NAYY 4x50 SE"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-slate-500 mt-1">If "generic_line", manual R/X values below are used.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Length (km)</label>
              <input
                type="number"
                step="0.1"
                name="length_km"
                value={formData.length_km || '10.0'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            {(!formData.type || formData.type === 'generic_line') && (
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Resistance (R ohm/km)</label>
                  <input
                    type="number"
                    step="0.001"
                    name="r_ohm_per_km"
                    value={formData.r_ohm_per_km || '0.1'}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Reactance (X ohm/km)</label>
                  <input
                    type="number"
                    step="0.001"
                    name="x_ohm_per_km"
                    value={formData.x_ohm_per_km || '0.2'}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            )}
          </div>
        );
      case 'transformer':
      case 'transformer3w':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Standard Type</label>
              <input
                type="text"
                name="std_type"
                value={formData.std_type || (node.type === 'transformer' ? '160 MVA 380/110 kV' : '63/25/38 MVA 110/20/10 kV')}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-slate-500 mt-1">Pandapower standard type string. Use "generic" for custom impedance.</p>
            </div>
            {(formData.std_type === 'generic') && (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Rated Power (sn_mva)</label>
                  <input
                    type="number"
                    step="0.1"
                    name="sn_mva"
                    value={formData.sn_mva !== undefined ? formData.sn_mva : '100.0'}
                    onChange={handleChange}
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-slate-500 mt-1">Apparent power base for impedances (e.g. 9900.0 for IEEE-14).</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Short Circuit Voltage (vk %)</label>
                    <input
                      type="number"
                      step="0.001"
                      name="vk_percent"
                      value={formData.vk_percent !== undefined ? formData.vk_percent : '10.0'}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Real Part (vkr %)</label>
                    <input
                      type="number"
                      step="0.001"
                      name="vkr_percent"
                      value={formData.vkr_percent !== undefined ? formData.vkr_percent : '0.1'}
                      onChange={handleChange}
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      case 'sgen':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Active Power (P in MW)</label>
              <input
                type="number"
                step="0.1"
                name="p_mw"
                value={formData.p_mw || '10.0'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Reactive Power (Q in MVar)</label>
              <input
                type="number"
                step="0.1"
                name="q_mvar"
                value={formData.q_mvar || '0.0'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        );
      case 'gen':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Active Power (P in MW)</label>
              <input
                type="number"
                step="0.1"
                name="p_mw"
                value={formData.p_mw || '100.0'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Voltage Setpoint (vm_pu)</label>
              <input
                type="number"
                step="0.01"
                name="vm_pu"
                value={formData.vm_pu || '1.0'}
                onChange={handleChange}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        );
      case 'network_switch':
        return (
          <div className="space-y-4">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
               <p className="text-xs text-slate-600 italic">
                 Visual component representing an Ethernet Switch. Used for organizational layering.
               </p>
            </div>
          </div>
        );
      case 'scada_server':
      case 'gps_clock':
        return (
          <div className="space-y-4">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
               <p className="text-xs text-slate-600 italic">
                 Visual representation of Control Room assets.
               </p>
            </div>
          </div>
        );
      default:
        return <p className="text-sm text-slate-500">No properties available for this node type.</p>;
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md border border-slate-200 overflow-hidden flex flex-col">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <div>
            <h3 className="text-lg font-bold text-slate-800">Configure Node</h3>
            <p className="text-xs text-slate-500 font-mono uppercase tracking-wider">{node.type} | {node.id.substring(0,10)}</p>
          </div>
          <button 
            onClick={closeModal}
            className="p-2 text-slate-400 hover:text-rose-500 hover:bg-rose-50 rounded-full transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-6">
          <div className="mb-6">
            <label className="block text-sm font-medium text-slate-700 mb-1">Display Label</label>
            <input
              type="text"
              name="label"
              value={formData.label || ''}
              onChange={handleChange}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <div className="w-full h-px bg-slate-100 mb-6"></div>

          {renderFields()}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50 flex justify-end space-x-3">
          <button 
            onClick={closeModal}
            className="px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-200 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button 
            onClick={handleSave}
            className="flex items-center space-x-2 px-6 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 shadow-sm transition-colors"
          >
            <Save size={16} />
            <span>Save Changes</span>
          </button>
        </div>

      </div>
    </div>
  );
};

export default NodePropertyModal;
