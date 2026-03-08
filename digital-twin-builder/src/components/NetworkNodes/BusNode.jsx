import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Zap } from 'lucide-react';

import useGridStore from '../../store/useGridStore';

const BusNode = ({ id, data, isConnectable }) => {
  const { isRunMode, liveTelemetry } = useGridStore();
  
  // Use static designer value or live running voltage
  // Pandapower typically uses per-unit (pu) scaled back to nominal. We display the raw pu for now.
  let displayVoltage = data.vn_kv || '110.0';
  if (isRunMode && liveTelemetry?.voltage_pu !== undefined) {
    displayVoltage = liveTelemetry.voltage_pu.toFixed(4); // Display in pu natively
  }
  return (
    <div className="px-4 py-2 shadow-md rounded-md bg-white border-2 border-slate-800 min-w-[150px]">
      {/* Top Handle for incoming connections */}
      <Handle
        type="target"
        position={Position.Top}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-slate-800"
      />
      
      <div className="flex items-center space-x-2">
        <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center">
          <Zap size={16} className="text-slate-700" />
        </div>
        <div>
          <div className="text-sm font-bold text-slate-800">{data.label || 'Bus Node'}</div>
          {isRunMode ? 
            <div className={`text-xs font-bold px-2 py-0.5 rounded mt-1 bg-blue-100 text-blue-700`}>
              {displayVoltage} pu
            </div>
            :
            <div className="text-xs text-slate-500">{displayVoltage} kV</div>
          }
        </div>
      </div>

      {/* Bottom Handle for outgoing connections */}
      <Handle
        type="source"
        position={Position.Bottom}
        isConnectable={isConnectable}
        className="w-3 h-3 bg-slate-800"
      />
    </div>
  );
};

export default memo(BusNode);
