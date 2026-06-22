import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Network } from 'lucide-react';

const Transformer3WNode = ({ data, isConnectable }) => {
  return (
    <div className="px-4 py-3 shadow-md rounded-md bg-white border-2 border-emerald-500 min-w-[180px]">
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-emerald-600"
        id="hv"
      />
      <Handle
        type="source"
        position={Position.Bottom}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-emerald-600"
        id="lv"
        style={{ left: '30%' }}
      />
      <Handle
        type="source"
        position={Position.Bottom}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-emerald-600"
        id="mv"
        style={{ left: '70%' }}
      />
      
      <div className="flex items-center space-x-3 mb-2">
        <div className="w-8 h-8 rounded-full bg-emerald-50 flex items-center justify-center">
          <Network size={16} className="text-emerald-700" />
        </div>
        <div>
          <div className="text-sm font-bold text-slate-800">{data.label || '3W Transformer'}</div>
        </div>
      </div>

      <div className="mt-2">
        <div className="bg-slate-50 p-1.5 rounded text-center border border-slate-100">
           <div className="text-[10px] text-slate-400 font-bold uppercase">Type</div>
           <div className="text-xs font-mono text-slate-700">{data.std_type || '63/25/38 MVA 110/20/10 kV'}</div>
        </div>
      </div>
    </div>
  );
};

export default memo(Transformer3WNode);
