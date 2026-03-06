import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Server } from 'lucide-react';

const IEDNode = ({ data, isConnectable }) => {
  const isOnline = data.comms_status !== 0;

  return (
    <div className={`px-4 py-3 shadow-md rounded-md bg-slate-900 border-2 min-w-[200px] transition-colors ${isOnline ? 'border-slate-700' : 'border-amber-500'}`}>
      
      <div className="flex items-center space-x-3 mb-2">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center relative ${isOnline ? 'bg-blue-500/10' : 'bg-amber-500/10'}`}>
          <Server size={20} className={isOnline ? 'text-blue-400' : 'text-amber-500'} />
          {isOnline && (
            <span className="absolute -top-1 -right-1 flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
            </span>
          )}
        </div>
        <div className="flex-grow">
          <div className="text-sm font-bold text-white">{data.label || 'OpenPLC IED'}</div>
          <div className="text-xs text-slate-400 font-mono">Port: {data.port || '5020'}</div>
        </div>
      </div>

      {!isOnline && (
        <div className="mt-2 text-[10px] font-bold text-amber-500 uppercase tracking-widest bg-amber-500/10 py-1 px-2 rounded text-center">
          Stale Data / Comms Lost
        </div>
      )}

      {/* 
        IEDs control multiple breakers via Modbus TCP.
        They don't connect physically to the power line (Pandapower),
        but we use React Flow edges to logically map which breakers they control. 
      */}
      {Array.from({ length: parseInt(data.num_breakers || 1) }).map((_, i) => (
        <Handle
          key={`control_out_${i}`}
          type="source"
          position={Position.Bottom}
          id={`control_out_${i}`}
          isConnectable={isConnectable}
          className="w-4 h-2 bg-blue-500 rounded-sm"
          style={{ left: `${(i + 1) * (100 / (parseInt(data.num_breakers || 1) + 1))}%` }}
        />
      ))}
    </div>
  );
};

export default memo(IEDNode);
