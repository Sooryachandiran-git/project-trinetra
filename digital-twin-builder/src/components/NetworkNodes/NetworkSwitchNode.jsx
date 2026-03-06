import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Share2 } from 'lucide-react';

const NetworkSwitchNode = ({ data, isConnectable }) => {
  return (
    <div className="px-4 py-3 shadow-md rounded-md bg-slate-800 border-2 border-slate-600 min-w-[220px]">
      <div className="flex items-center space-x-3 mb-2">
        <div className="w-8 h-8 rounded-md bg-slate-700 flex items-center justify-center">
          <Share2 size={18} className="text-blue-400" />
        </div>
        <div className="flex-grow">
          <div className="text-sm font-bold text-white">{data.label || 'Substation Switch'}</div>
          <div className="text-[10px] text-slate-400 font-mono tracking-tighter">Managed Ethernet Switch</div>
        </div>
      </div>

      <div className="flex justify-around items-center px-1 mt-2">
        <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
        <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
        <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
        <div className="w-2 h-2 rounded-full bg-slate-600"></div>
        <div className="w-2 h-2 rounded-full bg-slate-600"></div>
      </div>

      {/* Multiple handles for a switch */}
      <Handle type="target" position={Position.Top} id="in_1" className="w-2 h-2 bg-blue-500" />
      <Handle type="source" position={Position.Bottom} id="out_1" className="w-2 h-2 bg-blue-500" />
      <Handle type="source" position={Position.Left} id="side_L" className="w-2 h-2 bg-blue-500" />
      <Handle type="source" position={Position.Right} id="side_R" className="w-2 h-2 bg-blue-500" />
    </div>
  );
};

export default memo(NetworkSwitchNode);
