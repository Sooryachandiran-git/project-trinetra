import React from 'react';
import { ShieldAlert, Crosshair, ZapOff, WifiOff } from 'lucide-react';

// Future endpoints will be hooked up here
const triggerFDIA = () => {
    alert("Triggering FDIA (Under Construction)");
};

const triggerDoS = () => {
    alert("Triggering DoS (Under Construction)");
};

const AttackInterface = () => {
    return (
        <div className="w-80 bg-slate-950 border-l border-red-900/50 flex flex-col flex-shrink-0 shadow-xl z-10">
            <div className="p-4 bg-red-950/40 border-b border-red-900/50 flex items-center space-x-3">
                <ShieldAlert className="text-red-500" size={24} />
                <h2 className="text-red-500 font-bold uppercase tracking-widest text-sm">Red Team Interface</h2>
            </div>
            
            <div className="p-4 flex-1 overflow-y-auto space-y-6">
                
                {/* Attack Vector 1: FDIA */}
                <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
                    <div className="flex items-center space-x-2 text-rose-500 mb-2">
                        <Crosshair size={16} />
                        <h3 className="font-bold text-sm">False Data Injection (FDIA)</h3>
                    </div>
                    <p className="text-xs text-slate-400 mb-4 tracking-wide">
                        Inject highly-crafted false analog telemetry (e.g. overvoltage spikes) into targeted IED memory coils to trick the protection logic.
                    </p>
                    <button 
                        onClick={triggerFDIA}
                        className="w-full py-2 bg-rose-600/10 hover:bg-rose-600/20 text-rose-500 border border-rose-500/30 rounded text-xs font-bold transition-colors uppercase tracking-widest"
                    >
                        Deploy FDIA
                    </button>
                </div>

                {/* Attack Vector 2: DoS */}
                <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
                    <div className="flex items-center space-x-2 text-amber-500 mb-2">
                        <WifiOff size={16} />
                        <h3 className="font-bold text-sm">Denial of Service (DoS)</h3>
                    </div>
                    <p className="text-xs text-slate-400 mb-4 tracking-wide">
                        Flood the target OpenPLC management port to drop the Modbus connection, blinding the Master SCADA.
                    </p>
                    <button 
                        onClick={triggerDoS}
                        className="w-full py-2 bg-amber-600/10 hover:bg-amber-600/20 text-amber-500 border border-amber-500/30 rounded text-xs font-bold transition-colors uppercase tracking-widest"
                    >
                        Launch DoS
                    </button>
                </div>

                {/* Attack Vector 3: Unauthorized Switch */}
                <div className="bg-slate-900 rounded-lg p-4 border border-slate-800">
                    <div className="flex items-center space-x-2 text-purple-500 mb-2">
                        <ZapOff size={16} />
                        <h3 className="font-bold text-sm">Rogue Breaker Trip</h3>
                    </div>
                    <p className="text-xs text-slate-400 mb-4 tracking-wide">
                        Bypass the IED entirely and directly instruct the physical actuator to open the breaker, dropping the load immediately.
                    </p>
                    <button 
                        className="w-full py-2 bg-purple-600/10 hover:bg-purple-600/20 text-purple-500 border border-purple-500/30 rounded text-xs font-bold transition-colors uppercase tracking-widest"
                    >
                        Trip Breaker 1
                    </button>
                </div>
                
            </div>
            
            <div className="p-4 bg-slate-900 border-t border-slate-800 text-[10px] text-slate-500 text-center uppercase tracking-widest rounded-b-lg">
                TRINETRA Internal Security Tool
            </div>
        </div>
    );
};

export default AttackInterface;
