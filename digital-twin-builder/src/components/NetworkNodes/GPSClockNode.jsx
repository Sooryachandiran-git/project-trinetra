import React, { memo, useState, useEffect } from 'react';
import { Handle, Position } from '@xyflow/react';
import { Clock } from 'lucide-react';

import useGridStore from '../../store/useGridStore';

const GPSClockNode = ({ data, isConnectable }) => {
  const [time, setTime] = useState(new Date());
  const liveTelemetry = useGridStore(state => state.liveTelemetry);
  const timeOffset = liveTelemetry?.gps_clock_offset || 0;

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  const displayTime = new Date(time.getTime() + timeOffset * 1000);
  const formattedTime = displayTime.toLocaleTimeString('en-GB', { 
    hour12: false, 
    hour: '2-digit', 
    minute: '2-digit', 
    second: '2-digit' 
  }) + `:${displayTime.getMilliseconds().toString().padStart(3, '0')}`;

  return (
    <div className="px-4 py-2 shadow-md rounded-md bg-slate-900 border-2 border-amber-500/50 min-w-[200px]">
      <div className="flex items-center space-x-3">
        <div className="w-8 h-8 rounded-md bg-amber-500/10 flex items-center justify-center border border-amber-500/30">
          <Clock size={16} className="text-amber-500 animate-pulse" />
        </div>
        <div>
          <div className="text-[10px] font-bold text-slate-400 tracking-widest uppercase">GPS Master Clock</div>
          <div className="text-[16px] text-amber-500 font-mono font-bold tracking-wider">
            {formattedTime}
          </div>
        </div>
      </div>
      
      <Handle type="source" position={Position.Bottom} className="w-2 h-2 bg-amber-500" />
    </div>
  );
};

export default memo(GPSClockNode);
