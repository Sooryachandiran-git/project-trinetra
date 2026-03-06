import React, { useRef, useState } from 'react';
import { Save, Upload, Play, Loader2 } from 'lucide-react';
import useGridStore from '../store/useGridStore';
import { compileGridToJSON } from '../utils/jsonBuilder';
import { sendDeployPayload } from '../services/api';

const Topbar = () => {
  const { nodes, edges, loadGrid } = useGridStore();
  const [isDeploying, setIsDeploying] = useState(false);
  const fileInputRef = useRef(null);

  const handleSave = () => {
    // 1. Package the grid state into a JSON object
    const gridData = {
      nodes,
      edges,
    };
    const jsonString = JSON.stringify(gridData, null, 2);

    // 2. Create a Blob and generate a download link
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');

    // 3. Trigger download
    link.href = url;
    link.download = `trinetra_architecture_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleLoadClick = () => {
    // Open the hidden file input dialog
    fileInputRef.current?.click();
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const json = JSON.parse(e.target?.result);
        if (json.nodes && json.edges) {
          loadGrid(json);
          console.log('Grid loaded successfully from file.');
        } else {
          alert('Invalid architecture file format.');
        }
      } catch (err) {
        alert('Failed to parse JSON file.');
      }
    };
    reader.readAsText(file);
    
    // Reset input so the same file could be loaded again if needed
    event.target.value = '';
  };

  const handleDeploy = async () => {
    setIsDeploying(true);
    try {
      const payload = compileGridToJSON(nodes, edges);
      console.log('--- SENDING FASTAPI PAYLOAD ---', payload);
      
      const response = await sendDeployPayload(payload);
      
      const results = response.diagnostics?.results;
      let resultStats = "No simulation results available.";
      
      if (results && results.converged) {
        resultStats = "Simulation Converged!\n\nBus Voltages:\n";
        Object.entries(results.bus_voltages).forEach(([id, voltage]) => {
          const name = results.bus_names[id] || `Bus ${id}`;
          resultStats += `- ${name}: ${Number(voltage).toFixed(4)} pu\n`;
        });
      } else if (results && !results.converged) {
        resultStats = `Simulation Failed to Converge: ${results.reason || results.error || "Unknown Error"}`;
      }

      alert(`Architecture Deployed Successfully!\n\n${resultStats}\n\nExecution Time: ${response.execution_time_ms}ms`);
      console.log("Diagnostics:", response.diagnostics);
      
    } catch (error) {
      alert(`Deployment Failed:\n\n${error.message}`);
    } finally {
      setIsDeploying(false);
    }
  };

  return (
    <div className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 shadow-sm z-20">
      <div className="flex items-center space-x-4">
        <h1 className="font-semibold text-slate-800 text-lg tracking-tight">TRINETRA Builder</h1>
      </div>

      <div className="flex items-center space-x-4">
        {/* Hidden file input for loading JSON */}
        <input
          type="file"
          accept=".json"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden"
        />

        <button 
          onClick={handleLoadClick}
          className="flex items-center space-x-2 px-4 py-2 bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900 font-medium rounded-lg transition-colors border border-slate-200"
        >
          <Upload size={18} />
          <span>Load</span>
        </button>

        <button 
          onClick={handleSave}
          className="flex items-center space-x-2 px-4 py-2 bg-slate-50 text-slate-700 hover:bg-slate-100 hover:text-slate-900 font-medium rounded-lg transition-colors border border-slate-200"
        >
          <Save size={18} />
          <span>Save</span>
        </button>

        <div className="w-px h-6 bg-slate-200 mx-2"></div>

        <button 
          onClick={handleDeploy}
          className="flex items-center space-x-2 px-5 py-2 bg-blue-600 text-white hover:bg-blue-700 font-medium rounded-lg shadow-sm transition-colors"
        >
          <Play size={18} fill="currentColor" />
          <span>Deploy</span>
        </button>
      </div>
    </div>
  );
};

export default Topbar;
