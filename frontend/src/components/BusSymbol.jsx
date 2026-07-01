import React from 'react';

const fmt = (v, d = 3) => (v != null && isFinite(v) ? Number(v).toFixed(d) : '—');

export function BusSymbol({ bus, x, y, selected, onClick }) {
  const vpu = bus.v_pu ?? 1.0;

  let statusColor = 'var(--success)';
  if (vpu < 0.90 || vpu > 1.10) statusColor = 'var(--danger)';
  else if (vpu < 0.95 || vpu > 1.05) statusColor = 'var(--warning)';

  const hasGenerator  = bus.is_gen || bus.is_slack;
  const hasCondenser  = bus.is_condenser;
  const hasLoad       = bus.is_load;

  return (
    <g
      className={`bus-group ${selected ? 'selected' : ''}`}
      transform={`translate(${x}, ${y})`}
      onClick={e => { e.stopPropagation(); onClick(bus); }}
      style={{ cursor: 'pointer' }}
    >
      {/* Fat invisible hit area */}
      <circle cx="0" cy="0" r="28" fill="transparent" />

      {/* Selection halo */}
      {selected && (
        <line x1="-24" y1="0" x2="24" y2="0"
          stroke="var(--primary-glow)" strokeWidth="12" strokeLinecap="round" />
      )}

      {/* Busbar tick */}
      <line x1="-20" y1="0" x2="20" y2="0"
        stroke={statusColor} strokeWidth="6" strokeLinecap="round" />

      {/* Labels */}
      <text x="0" y="18" textAnchor="middle" fontSize="11" fontWeight="700" fill="var(--text-main)">
        Bus {bus.id}
      </text>
      <text x="0" y="29" textAnchor="middle" fontSize="9.5" fill={statusColor}>
        {fmt(vpu, 3)} pu
      </text>

      {/* Generator circle + G label */}
      {hasGenerator && (
        <g transform="translate(-28, -22)">
          <circle cx="0" cy="0" r="11" fill="var(--bg-card)" stroke="var(--primary)" strokeWidth="2" />
          <text x="0" y="4" textAnchor="middle" fontSize="10" fontWeight="700" fill="var(--primary)">G</text>
          <line x1="11" y1="0" x2="18" y2="10" stroke="var(--primary)" strokeWidth="1.5" />
        </g>
      )}

      {/* Condenser circle + C label */}
      {hasCondenser && (
        <g transform="translate(-28, -22)">
          <circle cx="0" cy="0" r="11" fill="var(--bg-card)" stroke="var(--accent)" strokeWidth="2" />
          <text x="0" y="4" textAnchor="middle" fontSize="10" fontWeight="700" fill="var(--accent)">C</text>
          <line x1="11" y1="0" x2="18" y2="10" stroke="var(--accent)" strokeWidth="1.5" />
        </g>
      )}

      {/* Load arrow */}
      {hasLoad && (
        <g transform="translate(28, -18)">
          <path d="M0,-8 L0,6 M-4,2 L0,6 L4,2" fill="none"
            stroke="var(--danger)" strokeWidth="2" strokeLinecap="round" />
          <line x1="-11" y1="-8" x2="-18" y2="4" stroke="var(--danger)" strokeWidth="1.5" />
          <text x="5" y="-5" fontSize="8" fill="var(--text-muted)">{Math.round(bus.p_load_mw ?? 0)}MW</text>
        </g>
      )}
    </g>
  );
}
