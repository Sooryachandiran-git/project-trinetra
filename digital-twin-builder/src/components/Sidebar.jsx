import React from 'react';
import { 
  Globe, 
  Square, 
  Zap, 
  Activity, 
  ToggleLeft, 
  ShieldCheck, 
  Share2, 
  Clock, 
  Monitor,
  Cpu
} from 'lucide-react';

const SidebarItem = ({ type, label, icon, description }) => {
  const onDragStart = (event, nodeType) => {
    event.dataTransfer.setData('application/reactflow', nodeType);
    event.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div
      className="flex items-center space-x-3 p-3 bg-white border border-slate-200 shadow-sm rounded-xl cursor-grab hover:border-blue-500 hover:shadow-md transition-all group"
      onDragStart={(event) => onDragStart(event, type)}
      draggable
    >
      <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center group-hover:bg-blue-50 transition-colors">
        {React.cloneElement(icon, { size: 18, className: "text-slate-600 group-hover:text-blue-600" })}
      </div>
      <div className="flex flex-col">
        <span className="font-semibold text-sm text-slate-800 tracking-tight">{label}</span>
        {description && <span className="text-[10px] text-slate-400 font-medium">{description}</span>}
      </div>
    </div>
  );
};

const Sidebar = () => {
  return (
    <aside className="w-72 bg-slate-50 border-r border-slate-200 h-full p-6 overflow-y-auto no-scrollbar">
      <div className="mb-8 p-4 bg-blue-600 rounded-2xl shadow-lg shadow-blue-200">
        <h2 className="text-white font-bold text-lg flex items-center">
          <Zap className="mr-2 fill-white" size={20} /> Component Palette
        </h2>
        <p className="text-blue-100 text-[10px] mt-1 font-medium opacity-80 uppercase tracking-widest">
          Drag & Drop to Build
        </p>
      </div>

      <div className="mb-6">
        <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center">
          <Zap size={14} className="mr-2" /> Electrical Grid
        </h3>
        <div className="space-y-3">
          <SidebarItem type="ext_grid" label="External Grid" icon={<Globe />} description="Main Power Source" />
          <SidebarItem type="bus" label="Bus" icon={<Square />} description="Distribution Node" />
          <SidebarItem type="transmission_line" label="TX Line" icon={<Zap />} description="Connecting Segment" />
          <SidebarItem type="breaker" label="Circuit Breaker" icon={<ToggleLeft />} description="Switching Device" />
          <SidebarItem type="load" label="Consumer Load" icon={<Activity />} description="P/Q Power Demand" />
        </div>
      </div>

      <div className="mb-6 pt-4 border-t border-slate-200">
        <h3 className="text-[11px] font-bold text-slate-400 uppercase tracking-widest mb-4 flex items-center">
          <Cpu size={14} className="mr-2" /> SCADA / Communication
        </h3>
        <div className="space-y-3">
          <SidebarItem type="ied" label="Protection IED" icon={<ShieldCheck />} description="Modbus Logic Controller" />
          <SidebarItem type="gps_clock" label="GPS Master Clock" icon={<Clock />} description="PTP Synchronization" />
        </div>
      </div>

      <div className="mt-auto pt-8">
        <div className="bg-slate-100/50 p-4 rounded-xl border border-dashed border-slate-300">
          <p className="text-[10px] text-slate-500 text-center font-medium leading-relaxed">
            Double click any component on the canvas to configure its physical properties.
          </p>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
