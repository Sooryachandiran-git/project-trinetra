import React, { useRef, useState } from 'react';
import { Save, Upload, Play, Loader2 } from 'lucide-react';
import useGridStore from '../store/useGridStore';
import { compileGridToJSON } from '../utils/jsonBuilder';
import { sendDeployPayload, sendStopSimulation, sendPandapowerSolve, sendAndesSolve, sendAndesCyberAttack } from '../services/api';
import { Square, Activity, LayoutTemplate, Calculator, Zap, ShieldAlert } from 'lucide-react';

const Topbar = () => {
  const { nodes, edges, loadGrid, isRunMode, setRunMode, setLiveTelemetry, activeView, setActiveView, setPandapowerResults, andesResults, setAndesResults, cyberAttackResults, setCyberAttackResults } = useGridStore();
  const [isDeploying, setIsDeploying] = useState(false);
  const [isSolving, setIsSolving] = useState(false);
  const [isSolvingAndes, setIsSolvingAndes] = useState(false);
  const [isSimulatingAttack, setIsSimulatingAttack] = useState(false);
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

      // If successful, enter run mode
      setRunMode(true);
      
    } catch (error) {
      alert(`Deployment Failed:\n\n${error.message}`);
    } finally {
      setIsDeploying(false);
    }
  };

  const handleSolve = async () => {
    setIsSolving(true);
    try {
      const payload = compileGridToJSON(nodes, edges);
      console.log('--- SENDING PANDAPOWER SOLVE PAYLOAD ---', payload);
      
      const response = await sendPandapowerSolve(payload.electrical_grid);
      
      if (response.converged) {
        setPandapowerResults(response);
        setActiveView('pandapower');
      } else {
        alert(`Pandapower Solve Failed:\n\n${response.error || "Unknown Error"}`);
      }
    } catch (error) {
      alert(`Solve Request Failed:\n\n${error.message}`);
    } finally {
      setIsSolving(false);
    }
  };

  const handleSolveAndes = async () => {
    setIsSolvingAndes(true);
    try {
      const payload = compileGridToJSON(nodes, edges);
      console.log('--- SENDING ANDES SOLVE PAYLOAD ---', payload);
      
      const response = await sendAndesSolve(payload.electrical_grid);
      
      if (response.converged) {
        setAndesResults(response);
        setActiveView('andes');
      } else {
        alert(`ANDES Solve Failed:\n\n${response.error || "Unknown Error"}`);
      }
    } catch (error) {
      alert(`ANDES Solve Request Failed:\n\n${error.message}`);
    } finally {
      setIsSolvingAndes(false);
    }
  };

  const handleSimulateCyberAttack = async () => {
    setIsSimulatingAttack(true);
    try {
      const payload = compileGridToJSON(nodes, edges);
      console.log('--- SENDING CYBER ATTACK TDS PAYLOAD ---', payload);
      
      const response = await sendAndesCyberAttack(payload.electrical_grid);
      
      if (response.converged) {
        setCyberAttackResults(response);
        setActiveView('cyber_attack');
      } else {
        alert(`Cyber Attack Simulation Failed:\n\n${response.error || "Unknown Error"}`);
      }
    } catch (error) {
      alert(`Cyber Attack Request Failed:\n\n${error.message}`);
    } finally {
      setIsSimulatingAttack(false);
    }
  };

  const handleStop = async () => {
    try {
      await sendStopSimulation();
      setRunMode(false);
      setLiveTelemetry(null);
    } catch (error) {
      alert(`Stop Failed:\n\n${error.message}`);
    }
  };

  return (
    <div className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 shadow-sm z-20">
      <div className="flex items-center space-x-4">
        <h1 className="font-semibold text-slate-800 text-lg tracking-tight">TRINETRA Builder</h1>
      </div>

      {(isRunMode || useGridStore.getState().pandapowerResults || useGridStore.getState().andesResults) && (
        <div className="flex items-center space-x-1 bg-slate-100 p-1 rounded-lg border border-slate-200">
          <button 
            onClick={() => setActiveView('topology')}
            className={`flex items-center space-x-2 px-4 py-1.5 rounded-md text-sm font-bold transition-all ${
              activeView === 'topology' 
                ? 'bg-white text-blue-600 shadow-sm' 
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            <LayoutTemplate size={16} />
            <span>Topology SLD</span>
          </button>
          {isRunMode && (
            <button 
              onClick={() => setActiveView('control_room')}
              className={`flex items-center space-x-2 px-4 py-1.5 rounded-md text-sm font-bold transition-all ${
                activeView === 'control_room' 
                  ? 'bg-slate-800 text-emerald-400 shadow-sm' 
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              <Activity size={16} />
              <span>Control Room</span>
            </button>
          )}
          {useGridStore.getState().pandapowerResults && (
            <button 
              onClick={() => setActiveView('pandapower')}
              className={`flex items-center space-x-2 px-4 py-1.5 rounded-md text-sm font-bold transition-all ${
                activeView === 'pandapower' 
                  ? 'bg-white text-emerald-600 shadow-sm' 
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              <Calculator size={16} />
              <span>Physics Results</span>
            </button>
          )}
          {useGridStore.getState().andesResults && (
            <button 
              onClick={() => setActiveView('andes')}
              className={`flex items-center space-x-2 px-4 py-1.5 rounded-md text-sm font-bold transition-all ${
                activeView === 'andes' 
                  ? 'bg-white text-purple-600 shadow-sm' 
                  : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              <Zap size={16} />
              <span>ANDES Results</span>
            </button>
          )}
          {useGridStore.getState().cyberAttackResults && (
            <button 
              onClick={() => setActiveView('cyber_attack')}
              className={`flex items-center space-x-2 px-4 py-1.5 rounded-md text-sm font-bold transition-all ${
                activeView === 'cyber_attack' 
                  ? 'bg-red-600 text-white shadow-sm' 
                  : 'bg-white text-red-600 hover:bg-red-50'
              }`}
            >
              <ShieldAlert size={16} />
              <span>Cyber Attack Simulation</span>
            </button>
          )}
        </div>
      )}

      <div className="flex items-center space-x-4">
        {!isRunMode ? (
          <>
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
              onClick={handleSolve}
              disabled={isSolving || isDeploying}
              className="flex items-center space-x-2 px-5 py-2 bg-emerald-600 text-white hover:bg-emerald-700 font-medium rounded-lg shadow-sm transition-colors disabled:opacity-50"
            >
              {isSolving ? <Loader2 size={18} className="animate-spin" /> : <Calculator size={18} />}
              <span>{isSolving ? 'Solving...' : 'Solve Physics'}</span>
            </button>
            <button 
              onClick={handleSolveAndes}
              disabled={isSolvingAndes || isDeploying || isSolving || isSimulatingAttack}
              className="flex items-center space-x-2 px-5 py-2 bg-purple-600 text-white hover:bg-purple-700 font-medium rounded-lg shadow-sm transition-colors disabled:opacity-50"
            >
              {isSolvingAndes ? <Loader2 size={18} className="animate-spin" /> : <Zap size={18} />}
              <span>{isSolvingAndes ? 'Solving ANDES...' : 'Solve ANDES'}</span>
            </button>
            <button 
              onClick={handleSimulateCyberAttack}
              disabled={isSimulatingAttack || isSolvingAndes || isDeploying || isSolving}
              className="flex items-center space-x-2 px-5 py-2 bg-red-600 text-white hover:bg-red-700 font-medium rounded-lg shadow-sm transition-colors disabled:opacity-50"
            >
              {isSimulatingAttack ? <Loader2 size={18} className="animate-spin" /> : <ShieldAlert size={18} />}
              <span>{isSimulatingAttack ? 'Simulating Attack...' : 'Simulate Cyber Attack'}</span>
            </button>
            <button 
              onClick={handleDeploy}
              disabled={isDeploying || isSolving || isSolvingAndes || isSimulatingAttack}
              className="flex items-center space-x-2 px-5 py-2 bg-blue-600 text-white hover:bg-blue-700 font-medium rounded-lg shadow-sm transition-colors disabled:opacity-50"
            >
              {isDeploying ? <Loader2 size={18} className="animate-spin" /> : <Play size={18} fill="currentColor" />}
              <span>{isDeploying ? 'Deploying...' : 'Deploy'}</span>
            </button>
          </>
        ) : (
          <button 
            onClick={handleStop}
            className="flex items-center space-x-2 px-5 py-2 bg-red-600 text-white hover:bg-red-700 font-medium rounded-lg shadow-sm transition-colors"
          >
            <Square size={18} fill="currentColor" />
            <span>Stop Simulation</span>
          </button>
        )}
      </div>
    </div>
  );
};

export default Topbar;
