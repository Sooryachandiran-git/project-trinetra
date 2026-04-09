import React, { useState } from 'react';
import { ShieldAlert, Crosshair, ZapOff, WifiOff, Loader2 } from 'lucide-react';
import useGridStore from '../../store/useGridStore';
import { startAttack, stopAttack } from '../../services/api';

const AttackInterface = () => {
    const { nodes } = useGridStore();
    const [activeAttacks, setActiveAttacks] = useState({});
    const [isLoading, setIsLoading] = useState(false);
    const [targetIed, setTargetIed] = useState("");

    // Get all IED nodes from the canvas to populate target dropdown
    const iedNodes = nodes.filter(n => n.type === 'ied');

    const handleAttackToggle = async (attackType, attackName) => {
        if (!targetIed) {
             alert("Please select a target IED first.");
             return;
        }

        const attackId = `${attackType}_${targetIed}`;
        setIsLoading(true);

        try {
            if (activeAttacks[attackId]) {
                // Stop it
                await stopAttack(attackId);
                setActiveAttacks(prev => {
                    const next = {...prev};
                    delete next[attackId];
                    return next;
                });
            } else {
                // Start it
                await startAttack({
                    attack_id: attackId,
                    attack_type: attackType,
                    target_ied: targetIed,
                    params: attackType === 'fdia_overvoltage' ? { injected_value: 1.20 } : {}
                });
                setActiveAttacks(prev => ({ ...prev, [attackId]: true }));
            }
        } catch (error) {
            console.error("Attack failed:", error);
            alert("Attack action failed. Is the simulation running?");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="w-80 bg-slate-950 border-l border-red-900/50 flex flex-col flex-shrink-0 shadow-xl z-10">
            <div className="p-4 bg-red-950/40 border-b border-red-900/50 flex flex-col space-y-3">
                <div className="flex items-center space-x-3">
                    <ShieldAlert className="text-red-500" size={24} />
                    <h2 className="text-red-500 font-bold uppercase tracking-widest text-sm">Red Team Interface</h2>
                </div>
                
                {/* Target Selection Dropdown */}
                <div className="flex flex-col space-y-1">
                    <label className="text-[10px] text-red-500/70 uppercase font-bold tracking-wider">Target IED</label>
                    <select 
                        value={targetIed}
                        onChange={(e) => setTargetIed(e.target.value)}
                        className="bg-black/50 border border-red-900/50 text-red-100 text-xs py-1.5 px-2 rounded outline-none focus:border-red-500"
                    >
                        <option value="">-- Select Target --</option>
                        {iedNodes.map(ied => (
                            <option key={ied.id} value={ied.id}>
                                {ied.data.label || ied.id}
                            </option>
                        ))}
                    </select>
                </div>
            </div>
            
            <div className="p-4 flex-1 overflow-y-auto space-y-6">
                
                {/* Attack Vector 1: FDIA */}
                <div className={`rounded-lg p-4 transition-colors border ${activeAttacks[`fdia_overvoltage_${targetIed}`] ? 'bg-rose-950/40 border-rose-500/50' : 'bg-slate-900 border-slate-800'}`}>
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center space-x-2 text-rose-500">
                            <Crosshair size={16} />
                            <h3 className="font-bold text-sm">False Data Injection</h3>
                        </div>
                        {activeAttacks[`fdia_overvoltage_${targetIed}`] && (
                            <span className="flex h-2 w-2 relative">
                                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                                <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
                            </span>
                        )}
                    </div>
                    <p className="text-xs text-slate-400 mb-4 tracking-wide">
                        Inject highly-crafted false analog telemetry (e.g. overvoltage spikes) to trick protection logic.
                    </p>
                    <button 
                        onClick={() => handleAttackToggle('fdia_overvoltage', 'FDIA')}
                        disabled={isLoading || !targetIed}
                        className={`w-full py-2 flex items-center justify-center space-x-2 border rounded text-xs font-bold transition-all uppercase tracking-widest disabled:opacity-50
                            ${activeAttacks[`fdia_overvoltage_${targetIed}`] 
                                ? 'bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-800' 
                                : 'bg-rose-950/50 text-rose-500 border-rose-500/30 hover:bg-rose-900/50 hover:border-rose-500'}`}
                    >
                        {isLoading ? <Loader2 size={14} className="animate-spin" /> : null}
                        <span>{activeAttacks[`fdia_overvoltage_${targetIed}`] ? 'Abort Attack' : 'Deploy FDIA'}</span>
                    </button>
                </div>

                {/* Attack Vector 2: DoS */}
                <div className={`rounded-lg p-4 transition-colors border ${activeAttacks[`ddos_${targetIed}`] ? 'bg-amber-950/40 border-amber-500/50' : 'bg-slate-900 border-slate-800'}`}>
                    <div className="flex items-center space-x-2 text-amber-500 mb-2">
                        <WifiOff size={16} />
                        <h3 className="font-bold text-sm">Denial of Service</h3>
                    </div>
                    <p className="text-xs text-slate-400 mb-4 tracking-wide">
                        Flood the target OpenPLC management port to drop the Modbus connection.
                    </p>
                    <button 
                        onClick={() => handleAttackToggle('ddos', 'DoS')}
                        disabled={isLoading || !targetIed}
                        className={`w-full py-2 flex items-center justify-center space-x-2 border rounded text-xs font-bold transition-all uppercase tracking-widest disabled:opacity-50
                            ${activeAttacks[`ddos_${targetIed}`] 
                                ? 'bg-slate-900 text-slate-300 border-slate-700 hover:bg-slate-800' 
                                : 'bg-amber-950/50 text-amber-500 border-amber-500/30 hover:bg-amber-900/50 hover:border-amber-500'}`}
                    >
                        {isLoading ? <Loader2 size={14} className="animate-spin" /> : null}
                        <span>{activeAttacks[`ddos_${targetIed}`] ? 'Abort DoS' : 'Launch DoS'}</span>
                    </button>
                </div>

                {/* Attack Vector 3: Unauthorized Switch */}
                <div className="bg-slate-900 rounded-lg p-4 border border-slate-800 opacity-50">
                    <div className="flex items-center space-x-2 text-purple-500 mb-2">
                        <ZapOff size={16} />
                        <h3 className="font-bold text-sm">Rogue Breaker Trip</h3>
                    </div>
                    <p className="text-xs text-slate-400 mb-4 tracking-wide">
                        Bypass the IED entirely and directly instruct the physical actuator to open the breaker.
                    </p>
                    <button disabled className="w-full py-2 bg-slate-950 text-slate-600 border border-slate-800 rounded text-xs font-bold cursor-not-allowed uppercase tracking-widest">
                        Trip Actuator (WIP)
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
