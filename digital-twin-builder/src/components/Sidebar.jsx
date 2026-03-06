import React from 'react';
import { Zap, Power, Server, Factory, ArrowDownToLine } from 'lucide-react';

const Sidebar = () => {
  const onDragStart = (event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div className="w-64 bg-white border-r border-slate-200 p-6 flex flex-col shadow-sm z-10 overflow-y-auto">
      <h2 className="font-semibold text-slate-800 mb-6 text-lg tracking-tight">Component Palette</h2>
      
      {/* Electrical Components */}
      <div className="mb-8">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Electrical Grid</h3>
        
        <div 
          className="flex items-center space-x-3 p-3 bg-white border border-slate-200 shadow-sm rounded-xl text-slate-700 cursor-grab mb-3 hover:border-emerald-500 hover:shadow-md transition-all group"
          onDragStart={(event) => onDragStart(event, 'ext_grid')}
          draggable
        >
          <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center group-hover:bg-emerald-50 transition-colors">
            <Factory size={16} className="text-slate-600 group-hover:text-emerald-600" />
          </div>
          <div className="flex flex-col">
             <span className="font-medium text-sm">External Grid</span>
             <span className="text-[10px] text-slate-400">Power Source</span>
          </div>
        </div>

        <div 
          className="flex items-center space-x-3 p-3 bg-white border border-slate-200 shadow-sm rounded-xl text-slate-700 cursor-grab mb-3 hover:border-blue-400 hover:shadow-md transition-all group"
          onDragStart={(event) => onDragStart(event, 'bus')}
          draggable
        >
          <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center group-hover:bg-blue-50 transition-colors">
            <Zap size={16} className="text-slate-600 group-hover:text-blue-600" />
          </div>
          <span className="font-medium text-sm">Bus / Substation</span>
        </div>

        <div 
          className="flex items-center space-x-3 p-3 bg-white border border-slate-200 shadow-sm rounded-xl text-slate-700 cursor-grab mb-3 hover:border-emerald-400 hover:shadow-md transition-all group"
          onDragStart={(event) => onDragStart(event, 'breaker')}
          draggable
        >
          <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center group-hover:bg-emerald-50 transition-colors">
            <Power size={16} className="text-slate-600 group-hover:text-emerald-600" />
          </div>
          <span className="font-medium text-sm">Circuit Breaker</span>
        </div>

        <div 
          className="flex items-center space-x-3 p-3 bg-white border border-slate-200 shadow-sm rounded-xl text-slate-700 cursor-grab mb-3 hover:border-indigo-400 hover:shadow-md transition-all group"
          onDragStart={(event) => onDragStart(event, 'load')}
          draggable
        >
          <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center group-hover:bg-indigo-50 transition-colors">
            <ArrowDownToLine size={16} className="text-slate-600 group-hover:text-indigo-600" />
          </div>
          <div className="flex flex-col">
             <span className="font-medium text-sm">Consumer Load</span>
             <span className="text-[10px] text-slate-400">P/Q Config</span>
          </div>
        </div>
      </div>

      {/* SCADA Components */}
      <div className="mb-8">
        <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Cyber Architecture</h3>
        
        <div 
          className="flex items-center space-x-3 p-3 bg-slate-900 border border-slate-800 shadow-sm rounded-xl text-white cursor-grab mb-3 hover:border-blue-400 hover:shadow-md transition-all group"
          onDragStart={(event) => onDragStart(event, 'ied')}
          draggable
        >
          <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center">
            <Server size={16} className="text-blue-400 group-hover:text-blue-300" />
          </div>
          <div className="flex flex-col">
             <span className="font-medium text-sm">OpenPLC IED</span>
             <span className="text-[10px] text-slate-400">Modbus Controller</span>
          </div>
        </div>
      </div>
      
      <div className="mt-auto pt-6 border-t border-slate-200">
        <a 
          href="#"
          className="w-full flex items-center justify-center px-4 py-3 bg-slate-100 text-slate-600 text-sm font-medium rounded-xl hover:bg-slate-200 transition-colors border border-slate-300 shadow-sm"
        >
          Exit Workspace
        </a>
      </div>
    </div>
  );
};

export default Sidebar;
