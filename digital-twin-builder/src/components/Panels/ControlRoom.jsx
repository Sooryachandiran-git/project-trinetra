import React, { useState, useEffect } from 'react';
import useGridStore from '../../store/useGridStore';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Activity, Zap, AlertTriangle, Database } from 'lucide-react';

const ControlRoom = () => {
    const { liveTelemetry } = useGridStore();
    const [history, setHistory] = useState([]);
    
    // Global Reset Function
    const handleReset = async () => {
        if (!liveTelemetry?.ied_health) return;
        
        const iedIds = Object.keys(liveTelemetry.ied_health);
        console.log(`[*] Initiating Master Reset for IEDs: ${iedIds.join(', ')}`);
        
        for (const id of iedIds) {
            try {
                await fetch(`http://localhost:8000/api/ied/${id}/reset`, { method: 'POST' });
            } catch (err) {
                console.error(`[-] Failed to reset IED ${id}:`, err);
            }
        }
    };

    // Build a rolling history for the charts based on the Live Telemetry
    useEffect(() => {
        let timeoutId;
        if (liveTelemetry) {
            timeoutId = setTimeout(() => {
                setHistory(prev => {
                    const now = new Date();
                    const timeStr = `${now.getHours()}:${now.getMinutes()}:${now.getSeconds()}.${Math.floor(now.getMilliseconds()/100)}`;
                    const newHistory = [...prev, { 
                        time: timeStr, 
                        voltage: liveTelemetry.voltage_pu, 
                        current: liveTelemetry.current_ka 
                    }];
                    if (newHistory.length > 50) newHistory.shift(); // Keep last 50 ticks (25 seconds viewing window)
                    return newHistory;
                });
            }, 0);
        }
        return () => clearTimeout(timeoutId);
    }, [liveTelemetry]);

    return (
        <div className="flex-1 bg-[#0f172a] text-slate-100 p-6 overflow-y-auto flex flex-col space-y-6">
            
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <div className="flex items-center space-x-3">
                    <Activity className="text-emerald-500" size={28} />
                    <h2 className="text-2xl font-bold text-white tracking-widest uppercase">SCADA Control Dashboard</h2>
                </div>
                <div className="flex items-center space-x-4">
                    <button 
                        onClick={handleReset}
                        className="flex items-center space-x-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold uppercase tracking-widest rounded-lg transition-all shadow-lg active:scale-95 border border-emerald-400/50"
                    >
                        <Activity size={16} />
                        <span>Master System Reset</span>
                    </button>
                    <div className="flex items-center space-x-2 bg-slate-800 px-3 py-1 rounded-full border border-slate-700">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                        <span className="text-xs font-mono text-emerald-400">LIVE SYNC ACTIVE</span>
                    </div>
                </div>
            </div>
            
            {/* Top Row: KPIs */}
            <div className="grid grid-cols-4 gap-6">
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col">
                    <div className="text-slate-400 text-xs font-bold uppercase tracking-widest mb-1">Global System Status</div>
                    <div className={`text-3xl font-light ${liveTelemetry?.breakers && Object.values(liveTelemetry.breakers).some(v => v === true) ? 'text-red-500' : 'text-emerald-400'}`}>
                        {liveTelemetry?.breakers && Object.values(liveTelemetry.breakers).some(v => v === true) ? 'TRIPPED' : 'NOMINAL'}
                    </div>
                </div>
                
                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col">
                    <div className="text-slate-400 text-xs font-bold uppercase tracking-widest mb-1">Grid Base Voltage</div>
                    <div className="flex items-baseline space-x-2">
                        <div className="text-3xl font-mono text-white">{liveTelemetry?.voltage_pu !== undefined ? liveTelemetry.voltage_pu.toFixed(4) : '0.000'}</div>
                        <div className="text-sm text-slate-500">pu</div>
                    </div>
                </div>

                <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg flex flex-col">
                    <div className="text-slate-400 text-xs font-bold uppercase tracking-widest mb-1">Network Base Current</div>
                    <div className="flex items-baseline space-x-2">
                        <div className="text-3xl font-mono text-white">{liveTelemetry?.current_ka !== undefined ? liveTelemetry.current_ka.toFixed(4) : '0.000'}</div>
                        <div className="text-sm text-slate-500">kA</div>
                    </div>
                </div>

                <div className="bg-slate-900 border border-amber-900/50 rounded-xl p-5 shadow-lg flex flex-col relative overflow-hidden">
                    <div className="absolute top-0 right-0 p-3 opacity-20"><AlertTriangle size={48} className="text-amber-500" /></div>
                    <div className="text-amber-500/80 text-xs font-bold uppercase tracking-widest mb-1 z-10">Active Alarms</div>
                    <div className="text-3xl font-light text-amber-500 z-10">
                        {liveTelemetry?.breakers ? Object.values(liveTelemetry.breakers).filter(v => v === true).length : 0}
                    </div>
                </div>
            </div>

            {/* Middle Row: Recharts Trend Graph */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg flex-1 min-h-[400px] flex flex-col">
                <div className="px-6 py-4 border-b border-slate-800 flex justify-between items-center">
                    <h3 className="font-bold text-slate-300 uppercase tracking-widest text-sm flex items-center space-x-2">
                        <Zap size={16} className="text-blue-400" />
                        <span>Real-time Telemetry Trend (Voltage / Current)</span>
                    </h3>
                </div>
                <div className="flex-1 p-6">
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={history} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                            <XAxis dataKey="time" stroke="#475569" tick={{fill: '#64748b', fontSize: 12}} />
                            <YAxis yAxisId="left" stroke="#3b82f6" tick={{fill: '#3b82f6'}} />
                            <YAxis yAxisId="right" orientation="right" stroke="#eab308" tick={{fill: '#eab308'}} />
                            <Tooltip 
                                contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', color: '#f8fafc' }}
                                itemStyle={{ color: '#e2e8f0' }}
                            />
                            <Line yAxisId="left" type="monotone" dataKey="voltage" name="Voltage" stroke="#3b82f6" strokeWidth={2} dot={false} isAnimationActive={false} />
                            <Line yAxisId="right" type="monotone" dataKey="current" name="Current" stroke="#eab308" strokeWidth={2} dot={false} isAnimationActive={false} />
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            </div>

            {/* Bottom Row: Historian Log */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-lg flex flex-col h-64">
                <div className="px-6 py-4 border-b border-slate-800 flex justify-between items-center bg-slate-900 rounded-t-xl">
                    <h3 className="font-bold text-slate-300 uppercase tracking-widest text-sm flex items-center space-x-2">
                        <Database size={16} className="text-slate-400" />
                        <span>Alarm Historian & DB Log</span>
                    </h3>
                    <button className="text-xs font-bold uppercase tracking-widest px-3 py-1.5 bg-slate-800 hover:bg-slate-700 rounded border border-slate-600 transition-colors">
                        📥 Export CSV
                    </button>
                </div>
                <div className="p-4 flex-1 overflow-y-auto font-mono text-sm space-y-2">
                    {/* Placeholder log entries */}
                    <div className="flex space-x-4 border-b border-slate-800/50 pb-2">
                        <span className="text-emerald-500">2026-03-07 23:45:00</span>
                        <span className="text-slate-400">[SYSTEM]</span>
                        <span className="text-slate-300">TRINETRA Simulation Engine Online. Polling Modbus registers.</span>
                    </div>
                </div>
            </div>

        </div>
    );
};

export default ControlRoom;
