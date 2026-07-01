import React from 'react';
import { TransformerIcon } from './TransformerIcon';

export function BranchLine({ branch, layoutFrom, layoutTo, selected, onClick }) {
  if (!layoutFrom || !layoutTo) return null;

  const x1 = layoutFrom.x, y1 = layoutFrom.y;
  const x2 = layoutTo.x,   y2 = layoutTo.y;

  const isTransformer = branch.type === 'transformer';
  const isActive      = branch.active !== false;
  const p_mw          = Math.abs(branch.p_flow_mw ?? 0);
  const loading       = branch.loading_pct ?? 0;

  // Stroke width scales with |P| (1.5–6px)
  const strokeWidth = isActive ? Math.min(6, Math.max(1.5, p_mw / 20)) : 1.5;

  // Color by loading %
  let strokeColor = 'var(--muted)';
  if (isActive) {
    if (loading > 100) strokeColor = 'var(--danger)';
    else if (loading > 80) strokeColor = 'var(--warning)';
    else strokeColor = 'var(--success)';
  }

  const mx  = (x1 + x2) / 2;
  const my  = (y1 + y2) / 2;
  const dx  = x2 - x1, dy = y2 - y1;
  const len = Math.hypot(dx, dy);
  const angle = (Math.atan2(dy, dx) * 180) / Math.PI;
  const ux = len > 0 ? dx / len : 0;
  const uy = len > 0 ? dy / len : 0;

  return (
    <g
      className={`branch-group ${selected ? 'selected' : ''} ${!isActive ? 'offline' : ''}`}
      onClick={e => { e.stopPropagation(); onClick(branch); }}
      style={{ cursor: 'pointer' }}
    >
      {/* Wide invisible hit target */}
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="transparent" strokeWidth={14} />

      {isTransformer ? (
        <>
          <line
            x1={x1} y1={y1}
            x2={mx - 16 * ux} y2={my - 16 * uy}
            stroke={strokeColor} strokeWidth={strokeWidth}
            strokeDasharray={isActive ? undefined : '5,4'}
          />
          <TransformerIcon x={mx} y={my} angle={angle} />
          <line
            x1={mx + 16 * ux} y1={my + 16 * uy}
            x2={x2} y2={y2}
            stroke={strokeColor} strokeWidth={strokeWidth}
            strokeDasharray={isActive ? undefined : '5,4'}
          />
        </>
      ) : (
        <line
          x1={x1} y1={y1} x2={x2} y2={y2}
          stroke={strokeColor} strokeWidth={strokeWidth}
          strokeDasharray={isActive ? undefined : '5,4'}
        />
      )}

      {/* Power flow direction arrow */}
      {isActive && p_mw > 5 && (
        <polygon
          points="-5,-4 5,0 -5,4"
          fill={strokeColor}
          transform={`translate(${mx},${my}) rotate(${(branch.p_flow_mw ?? 0) >= 0 ? angle : angle + 180})`}
        />
      )}
    </g>
  );
}
