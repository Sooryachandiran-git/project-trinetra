import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Zap } from 'lucide-react';

const TransmissionLineNode = ({ data, isConnectable }) => {
  return (
    <div className="px-4 py-2 shadow-sm rounded-md bg-white border-2 border-slate-400 min-w-[160px]">
      <Handle type="target" position={Position.Top} isConnectable={isConnectable} />
      
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-md bg-slate-100 flex items-center justify-center">
          <Zap size={16} className="text-slate-600" />
        </div>
        <div>
          <div className="text-xs font-bold text-slate-800">{data.label || 'TX Line'}</div>
          <div className="text-[10px] text-slate-500 font-mono">
             {data.length_km || '10'} km | {data.r_ohm_per_km || '0.1'} Ω/km
          </div>
        </div>
      </div>

      <Handle type="source" position={Position.Bottom} isConnectable={isConnectable} />
    </div>
  );
};

export default memo(TransmissionLineNode);
