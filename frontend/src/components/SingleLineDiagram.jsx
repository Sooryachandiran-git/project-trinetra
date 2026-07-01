import React from 'react';
import { BusSymbol } from './BusSymbol';
import { BranchLine } from './BranchLine';
import layout from '../layout.json';

export function SingleLineDiagram({ state, selectedElement, setSelectedElement }) {
  if (!state) return null;

  const handleCanvasClick = () => {
    setSelectedElement(null);
  };

  const handleElementClick = (type, item) => {
    setSelectedElement({
      type,
      id: item.id,
      data: item
    });
  };

  return (
    <div className="sld-container" onClick={handleCanvasClick}>
      <div className="sld-header">
        <h3>IEEE 14-Bus Single Line Diagram (Live Telemetry)</h3>
        <p className="sld-subtitle">
          Hover over elements to view quick info, click to inspect/modify parameters.
        </p>
      </div>

      <div className="sld-canvas-wrapper">
        <svg 
          viewBox="0 0 1050 780" 
          className="sld-svg"
          xmlns="http://www.w3.org/2000/svg"
        >
          {/* Grids and background patterns for modern look */}
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke="var(--bg-grid)" strokeWidth="1" />
            </pattern>
            <linearGradient id="bus-glow" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.2" />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity="0.2" />
            </linearGradient>
          </defs>

          {/* Grid Background */}
          <rect width="100%" height="100%" fill="url(#grid)" />

          {/* Connection Lines & Transformers */}
          <g className="branches-layer">
            {state.branches.map((branch) => {
              const layoutFrom = layout[branch.from_bus.toString()];
              const layoutTo = layout[branch.to_bus.toString()];
              const isSelected = selectedElement?.type === 'branch' && selectedElement?.id === branch.id;
              
              return (
                <BranchLine
                  key={`branch-${branch.id}`}
                  branch={branch}
                  layoutFrom={layoutFrom}
                  layoutTo={layoutTo}
                  selected={isSelected}
                  onClick={(item) => handleElementClick('branch', item)}
                />
              );
            })}
          </g>

          {/* Busbars & Component Icons */}
          <g className="buses-layer">
            {state.buses.map((bus) => {
              const pos = layout[bus.id.toString()];
              if (!pos) return null;
              const isSelected = selectedElement?.type === 'bus' && selectedElement?.id === bus.id;

              return (
                <BusSymbol
                  key={`bus-${bus.id}`}
                  bus={bus}
                  x={pos.x}
                  y={pos.y}
                  selected={isSelected}
                  onClick={(item) => handleElementClick('bus', item)}
                />
              );
            })}
          </g>
        </svg>
      </div>

      {/* Dynamic Status bar below SVG */}
      <div className="sld-footer-legend">
        <div className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: 'var(--success)' }}></span>
          <span>Normal Voltage (0.95 - 1.05 pu)</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: 'var(--warning)' }}></span>
          <span>Warning Level (0.90 - 0.95 or 1.05 - 1.10 pu)</span>
        </div>
        <div className="legend-item">
          <span className="legend-dot" style={{ backgroundColor: 'var(--danger)' }}></span>
          <span>Critical Level (&lt;0.90 or &gt;1.10 pu)</span>
        </div>
        <div className="legend-item">
          <span className="legend-line-sample"></span>
          <span>Width scales with Power Flow (MW)</span>
        </div>
      </div>
    </div>
  );
}
