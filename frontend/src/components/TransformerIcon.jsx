import React from 'react';

export function TransformerIcon({ x, y, angle = 0 }) {
  return (
    <g transform={`translate(${x}, ${y}) rotate(${angle})`} className="transformer-icon">
      {/* Background glow / container */}
      <circle cx="0" cy="0" r="15" fill="var(--bg-card)" opacity="0.9" />
      {/* Two overlapping circles for the transformer schematic representation */}
      <circle cx="-6" cy="0" r="9" fill="none" stroke="var(--primary)" strokeWidth="2" />
      <circle cx="6" cy="0" r="9" fill="none" stroke="var(--accent)" strokeWidth="2" />
    </g>
  );
}
