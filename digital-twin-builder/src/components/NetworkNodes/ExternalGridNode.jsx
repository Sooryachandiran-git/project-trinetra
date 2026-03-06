import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Factory } from 'lucide-react';

const ExternalGridNode = ({ data, isConnectable }) => {
  return (
    <div className="px-4 py-3 shadow-md rounded-md bg-white border-2 border-emerald-600 min-w-[180px]">
      
      <div className="flex items-center space-x-3 mb-1">
        <div className="w-8 h-8 rounded-full bg-emerald-50 flex items-center justify-center">
          <Factory size={16} className="text-emerald-700" />
        </div>
        <div>
          <div className="text-sm font-bold text-slate-800">{data.label || 'External Grid'}</div>
          <div className="text-xs text-slate-500 font-mono">1.0 pu / 0 deg</div>
        </div>
      </div>

      <div className="mt-2 text-[10px] font-bold text-emerald-600 uppercase tracking-widest bg-emerald-50 py-1 px-2 rounded text-center">
        Slack Bus
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-emerald-600"
      />
    </div>
  );
};

export default memo(ExternalGridNode);
