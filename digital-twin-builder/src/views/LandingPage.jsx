import React, { useRef } from 'react'
import { Zap, Upload, Plus } from 'lucide-react'
import useGridStore from '../store/useGridStore'

function LandingPage() {
  const fileInputRef = useRef(null);
  const { loadGrid } = useGridStore();

  const handleLoadClick = () => {
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
          // Redirect to workspace after successful load
          window.location.hash = '#workspace';
        } else {
          alert('Invalid architecture file format. Missing nodes or edges.');
        }
      } catch (err) {
        alert('Failed to parse JSON file.');
      }
    };
    reader.readAsText(file);
    event.target.value = ''; // Reset
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-slate-900 tracking-tight mb-4">
          Project TRINETRA
        </h1>
        <p className="text-lg text-slate-600 max-w-2xl mx-auto">
          Physics-Aware Digital Twin & Virtual Cyber Range for SCADA Security.
          Select your plant system to continue.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl w-full">
        <div className="group relative flex flex-col items-center justify-center p-12 bg-white rounded-3xl shadow-sm border border-slate-200 hover:shadow-xl hover:border-blue-200 transition-all duration-300">
          <div className="w-20 h-20 mb-8 rounded-2xl bg-blue-50 flex items-center justify-center text-blue-600 group-hover:scale-110 transition-transform duration-300">
            <Zap size={40} strokeWidth={1.5} />
          </div>
          <h2 className="text-2xl font-semibold text-slate-800 mb-3">Electrical SCADA</h2>
          <p className="text-center text-slate-500 text-sm leading-relaxed mb-8">
            Design and simulate power grid topologies with Pandapower and OpenPLC.
          </p>
          
          <div className="w-full flex flex-col space-y-3">
            <a 
              href="#workspace" 
              className="w-full flex items-center justify-center space-x-2 px-6 py-3 bg-slate-900 text-white text-sm font-medium rounded-xl shadow-md hover:bg-blue-600 transition-colors"
            >
              <Plus size={18} />
              <span>Create New Architecture</span>
            </a>
            
            <input
              type="file"
              accept=".json"
              ref={fileInputRef}
              onChange={handleFileChange}
              className="hidden"
            />
            <button 
              onClick={handleLoadClick}
              className="w-full flex items-center justify-center space-x-2 px-6 py-3 bg-slate-50 text-slate-700 text-sm font-medium rounded-xl border border-slate-200 hover:bg-slate-100 hover:text-slate-900 transition-colors"
            >
              <Upload size={18} />
              <span>Load Saved Architecture</span>
            </button>
          </div>
        </div>

        {/* Placeholder for future plant types */}
        <div className="flex flex-col items-center justify-center p-12 bg-slate-50 rounded-3xl border border-dashed border-slate-300 opacity-60">
          <div className="w-16 h-16 mb-6 rounded-full bg-slate-200 flex items-center justify-center text-slate-400">
            <span className="text-2xl font-bold">+</span>
          </div>
          <p className="text-slate-400 font-medium">Coming Soon</p>
        </div>
      </div>

      <footer className="mt-20 text-slate-400 text-xs font-medium uppercase tracking-[0.2em]">
        Research-Grade Security Testing Environment
      </footer>
    </div>
  )
}

export default LandingPage
