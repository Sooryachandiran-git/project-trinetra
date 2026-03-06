import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Monitor } from 'lucide-react';

const ScadaServerNode = ({ data, isConnectable }) => {
  return (
    <div className="px-4 py-3 shadow-lg rounded-md bg-white border-2 border-slate-300 min-w-[180px]">
      <div className="flex items-center space-x-3">
        <div className="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center border border-slate-200">
          <Monitor size={22} className="text-slate-700" />
        </div>
        <div>
          <div className="text-sm font-bold text-slate-900">{data.label || 'SCADA Workstation'}</div>
          <div className="text-[10px] font-bold text-blue-600 uppercase tracking-tight">Control Room Tier</div>
        </div>
      </div>

      <div className="mt-2 h-1 w-full bg-slate-100 rounded-full overflow-hidden">
        <div className="h-full bg-blue-500 w-2/3"></div>
      </div>
      
      <Handle type="target" position={Position.Top} className="w-3 h-3 bg-slate-400" />
    </div>
  );
};

export default memo(ScadaServerNode);
