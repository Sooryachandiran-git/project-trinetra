import React from 'react';
import useGridStore from '../store/useGridStore';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const CyberAttackResultsView = () => {
  const { cyberAttackResults } = useGridStore();

  if (!cyberAttackResults || !cyberAttackResults.time || !cyberAttackResults.voltages) {
    return (
      <div className="h-full flex items-center justify-center bg-slate-50 text-slate-500">
        No simulation data available. Run the Cyber Attack Simulation first.
      </div>
    );
  }

  // Format data for Recharts
  const timeArray = cyberAttackResults.time;
  const busVoltages = cyberAttackResults.voltages;
  const busIds = Object.keys(busVoltages);

  // Convert row-based arrays to column-based objects
  const chartData = timeArray.map((t, i) => {
    const dataPoint = { time: Number(t).toFixed(3) };
    busIds.forEach(busId => {
      dataPoint[busId] = busVoltages[busId][i];
    });
    return dataPoint;
  });

  const colors = ['#ef4444', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#6366f1'];

  return (
    <div className="p-8 h-full overflow-y-auto bg-slate-50">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* Header Section */}
        <div className="bg-white rounded-xl shadow-sm border border-red-100 p-6 flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-slate-800 flex items-center space-x-2">
              <span className="w-3 h-3 rounded-full bg-red-500 animate-pulse"></span>
              <span>Cyber-Physical Attack Simulation</span>
            </h2>
            <p className="text-slate-600 mt-2">
              Time-Domain Simulation (TDS) of a malicious cyber-attack. At t=2.0s, a simulated hacker exploits an IED vulnerability to close a grounding switch, causing a catastrophic short-circuit fault. 
            </p>
          </div>
          <div className="bg-red-50 text-red-700 px-4 py-2 rounded-lg font-mono text-sm font-semibold border border-red-100">
            {cyberAttackResults.converged ? 'TDS Solved (10s)' : 'TDS Diverged'}
          </div>
        </div>

        {/* Chart Section */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-lg font-semibold text-slate-800 mb-4">Bus Voltages Over Time (pu)</h3>
          
          <div className="h-[500px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={chartData}
                margin={{ top: 10, right: 30, left: 20, bottom: 30 }}
              >
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis 
                  dataKey="time" 
                  label={{ value: 'Time (Seconds)', position: 'insideBottom', offset: -20 }}
                  tick={{ fontSize: 12, fill: '#64748b' }}
                  tickMargin={10}
                />
                <YAxis 
                  domain={[0, 'auto']}
                  label={{ value: 'Voltage Magnitude (pu)', angle: -90, position: 'insideLeft', offset: -10 }}
                  tick={{ fontSize: 12, fill: '#64748b' }}
                />
                <Tooltip 
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  labelStyle={{ fontWeight: 'bold', color: '#1e293b' }}
                />
                <Legend verticalAlign="top" height={36} iconType="circle" />
                
                {busIds.map((busId, index) => (
                  <Line 
                    key={busId}
                    type="stepAfter" // Represents instant changes correctly
                    dataKey={busId}
                    name={`Bus ${busId}`}
                    stroke={colors[index % colors.length]}
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 6, strokeWidth: 0 }}
                    animationDuration={1500}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          
          <div className="mt-6 p-4 bg-slate-50 rounded-lg border border-slate-200">
            <h4 className="font-semibold text-slate-700 mb-2">Simulation Physics Context:</h4>
            <ul className="text-sm text-slate-600 space-y-1 list-disc list-inside">
              <li>0.0s - 2.0s: Grid operates in steady-state (Initial Power Flow).</li>
              <li>2.0s: Attack executes. Grounding switch closes creating a zero-impedance path to ground.</li>
              <li>Voltage on the compromised bus instantaneously drops near zero, dragging down adjacent buses.</li>
              <li>This mimics real-world behavior seen in cyber-attacks like the 2015 Ukraine grid hack, solved dynamically via ANDES Differential-Algebraic Equations.</li>
            </ul>
          </div>
        </div>

      </div>
    </div>
  );
};

export default CyberAttackResultsView;
