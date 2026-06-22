import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Zap } from 'lucide-react';

const GenNode = ({ data, isConnectable }) => {
  return (
    <div className="px-4 py-3 shadow-md rounded-md bg-white border-2 border-orange-400 min-w-[160px]">
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-orange-500"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-orange-500"
      />
      
      <div className="flex items-center space-x-3 mb-2">
        <div className="w-8 h-8 rounded-full bg-orange-50 flex items-center justify-center">
          <Zap size={16} className="text-orange-600" />
        </div>
        <div>
          <div className="text-sm font-bold text-slate-800">{data.label || 'Generator'}</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 mt-2">
        <div className="bg-slate-50 p-1.5 rounded text-center border border-slate-100">
           <div className="text-[10px] text-slate-400 font-bold uppercase">P (MW)</div>
           <div className="text-xs font-mono text-slate-700">{data.p_mw || '100.0'}</div>
        </div>
        <div className="bg-slate-50 p-1.5 rounded text-center border border-slate-100">
           <div className="text-[10px] text-slate-400 font-bold uppercase">V (p.u.)</div>
           <div className="text-xs font-mono text-slate-700">{data.vm_pu || '1.0'}</div>
        </div>
      </div>
    </div>
  );
};

export default memo(GenNode);
