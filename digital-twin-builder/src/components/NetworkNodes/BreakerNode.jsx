import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Power } from 'lucide-react';

const BreakerNode = ({ data, isConnectable }) => {
  const isClosed = data.status === 1 || data.status === 'Closed';

  return (
    <div className={`px-4 py-2 shadow-sm rounded-md bg-white border-2 min-w-[160px] transition-colors ${isClosed ? 'border-emerald-500' : 'border-rose-500'}`}>
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-slate-400"
      />
      
      <div className="flex items-center space-x-3">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${isClosed ? 'bg-emerald-100' : 'bg-rose-100'}`}>
          <Power size={16} className={isClosed ? 'text-emerald-700' : 'text-rose-700'} />
        </div>
        <div>
          <div className="text-sm font-bold text-slate-800">{data.label || 'Breaker'}</div>
          <div className={`text-xs font-semibold ${isClosed ? 'text-emerald-600' : 'text-rose-600'}`}>
            {isClosed ? 'CLOSED' : 'OPEN'}
          </div>
        </div>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-slate-400"
      />
    </div>
  );
};

export default memo(BreakerNode);
