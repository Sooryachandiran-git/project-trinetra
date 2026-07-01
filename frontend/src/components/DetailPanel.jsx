import React, { useState, useEffect } from 'react';
import { Settings, RefreshCw, Zap, Sliders } from 'lucide-react';

// Safe number formatter — never throws on null/undefined
const fmt = (v, d = 2) => (v != null && isFinite(v) ? Number(v).toFixed(d) : '—');

export function DetailPanel({
  selectedElement,
  setSelectedElement,
  updateSetpoint,
  resetGrid,
  state,
}) {
  const [activeTab, setActiveTab] = useState('summary');
  const [formState, setFormState] = useState({});

  useEffect(() => {
    if (!selectedElement || !state) return;

    if (selectedElement.type === 'bus') {
      const live = state.buses.find(b => b.id === selectedElement.id);
      setFormState({
        pg:     live?.p_gen_mw   ?? 0,
        vpu:    live?.v_pu       ?? 1.0,
        status: live?.is_gen     ?? false,
        pd:     live?.p_load_mw  ?? 0,
        qd:     live?.q_load_mvar ?? 0,
        isGen:  live?.is_gen || live?.is_slack || live?.is_condenser,
        isLoad: live?.is_load,
      });
    } else if (selectedElement.type === 'branch') {
      const live = state.branches.find(b => b.id === selectedElement.id);
      setFormState({
        tap:    live?.tap    ?? 1.0,
        active: live?.active ?? true,
      });
    }
  }, [selectedElement, state]);

  if (!state) {
    return (
      <div className="detail-panel empty">
        <div className="spinner"></div>
        <p>Awaiting simulation telemetry…</p>
      </div>
    );
  }

  const change = (field, val) => setFormState(p => ({ ...p, [field]: val }));

  /* ── BUS DETAIL ─────────────────────────────── */
  const renderBus = () => {
    const live = state.buses.find(b => b.id === selectedElement.id);
    if (!live) return <p className="text-muted">Bus not found in live state.</p>;

    return (
      <div className="panel-content animate-slide-in">
        <div className="panel-header">
          <h3>Bus {live.id} — {live.name}</h3>
          <button className="btn-close" onClick={() => setSelectedElement(null)}>×</button>
        </div>

        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-title">Voltage (p.u.)</span>
            <span className="stat-value text-success">{fmt(live.v_pu, 4)}</span>
          </div>
          <div className="stat-card">
            <span className="stat-title">Angle (deg)</span>
            <span className="stat-value">{fmt(live.angle_deg, 2)}°</span>
          </div>
          <div className="stat-card">
            <span className="stat-title">P gen (MW)</span>
            <span className="stat-value">{fmt(live.p_gen_mw, 2)}</span>
          </div>
          <div className="stat-card">
            <span className="stat-title">Q gen (Mvar)</span>
            <span className="stat-value">{fmt(live.q_gen_mvar, 2)}</span>
          </div>
        </div>

        {formState.isGen && (
          <div className="control-section">
            <h4 className="section-title"><Zap size={16} /> Generator Control</h4>
            <div className="form-group">
              <label>Active Power (Pg): {fmt(formState.pg, 1)} MW</label>
              <input type="range" min="0" max="300" step="1"
                value={formState.pg}
                onChange={e => change('pg', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Voltage Setpoint (Vpu): {fmt(formState.vpu, 3)}</label>
              <input type="range" min="0.9" max="1.1" step="0.005"
                value={formState.vpu}
                onChange={e => change('vpu', e.target.value)} />
            </div>
            <button className="btn btn-primary" onClick={async () => {
              const r = await updateSetpoint('generator', {
                bus: live.id,
                pg: parseFloat(formState.pg),
                vpu: parseFloat(formState.vpu),
                active: true,
              });
              if (!r.success) alert('Error: ' + r.error);
            }}>Apply Generator Setpoints</button>
          </div>
        )}

        {formState.isLoad && (
          <div className="control-section">
            <h4 className="section-title"><Sliders size={16} /> Load Demand Control</h4>
            <div className="form-group">
              <label>Active Load (Pd): {fmt(formState.pd, 1)} MW</label>
              <input type="range" min="0" max="150" step="0.5"
                value={formState.pd}
                onChange={e => change('pd', e.target.value)} />
            </div>
            <div className="form-group">
              <label>Reactive Load (Qd): {fmt(formState.qd, 1)} Mvar</label>
              <input type="range" min="-20" max="50" step="0.5"
                value={formState.qd}
                onChange={e => change('qd', e.target.value)} />
            </div>
            <button className="btn btn-accent" onClick={async () => {
              const r = await updateSetpoint('load', {
                bus: live.id,
                pd: parseFloat(formState.pd),
                qd: parseFloat(formState.qd),
              });
              if (!r.success) alert('Error: ' + r.error);
            }}>Apply Load Demand</button>
          </div>
        )}

        {!formState.isGen && !formState.isLoad && (
          <div className="control-section">
            <p className="text-muted">Junction / PQ bus — no controllable generation or load.</p>
          </div>
        )}
      </div>
    );
  };

  /* ── BRANCH DETAIL ──────────────────────────── */
  const renderBranch = () => {
    const live = state.branches.find(b => b.id === selectedElement.id);
    if (!live) return <p className="text-muted">Branch not found in live state.</p>;

    const isTrans = live.type === 'transformer';

    return (
      <div className="panel-content animate-slide-in">
        <div className="panel-header">
          <h3>{isTrans ? 'Transformer' : 'Line'} — {live.name}</h3>
          <button className="btn-close" onClick={() => setSelectedElement(null)}>×</button>
        </div>

        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-title">P Flow (MW)</span>
            <span className="stat-value">{fmt(live.p_flow_mw, 2)}</span>
          </div>
          <div className="stat-card">
            <span className="stat-title">Loading</span>
            <span className={`stat-value ${(live.loading_pct ?? 0) > 95 ? 'text-danger' : (live.loading_pct ?? 0) > 80 ? 'text-warning' : 'text-success'}`}>
              {fmt(live.loading_pct, 1)}%
            </span>
          </div>
          <div className="stat-card">
            <span className="stat-title">Q Flow (Mvar)</span>
            <span className="stat-value">{fmt(live.q_flow_mvar, 2)}</span>
          </div>
          <div className="stat-card">
            <span className="stat-title">P Loss (MW)</span>
            <span className="stat-value text-danger">{fmt(live.p_loss_mw, 3)}</span>
          </div>
        </div>

        <div className="control-section">
          <h4 className="section-title"><Settings size={16} /> Branch Settings</h4>
          <div className="form-group">
            <label>Service Status</label>
            <div className="toggle-switch">
              <button className={`toggle-btn ${formState.active ? 'active' : ''}`} onClick={() => change('active', true)}>In Service</button>
              <button className={`toggle-btn ${!formState.active ? 'active-off' : ''}`} onClick={() => change('active', false)}>Out of Service</button>
            </div>
          </div>
          {isTrans && (
            <div className="form-group">
              <label>Tap Ratio: {fmt(formState.tap, 3)}</label>
              <input type="range" min="0.9" max="1.1" step="0.00625"
                value={formState.tap}
                onChange={e => change('tap', e.target.value)} />
            </div>
          )}
          <button className="btn btn-primary" onClick={async () => {
            if (isTrans) {
              await updateSetpoint('transformer', { id: live.id, tap: parseFloat(formState.tap) });
            }
            await updateSetpoint('branch', { id: live.id, active: formState.active });
          }}>Apply Settings</button>
        </div>

        <div className="technical-parameters">
          <h5>Technical Specs</h5>
          <div className="tech-row"><span>From Bus</span><span>Bus {live.from_bus}</span></div>
          <div className="tech-row"><span>To Bus</span><span>Bus {live.to_bus}</span></div>
          <div className="tech-row"><span>Current</span><span>{fmt(live.i_flow_a, 1)} A</span></div>
          <div className="tech-row"><span>Rating</span><span>{fmt(live.rating_a, 0)} A</span></div>
        </div>
      </div>
    );
  };

  /* ── GLOBAL OVERVIEW TABS ───────────────────── */
  const renderOverview = () => (
    <div className="global-overview animate-fade-in">
      <div className="panel-tabs">
        {['summary','generators','loads','transformers','branches'].map(t => (
          <button key={t} className={`tab-btn ${activeTab === t ? 'active' : ''}`} onClick={() => setActiveTab(t)}>
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      <div className="tab-content">

        {activeTab === 'summary' && (
          <div className="summary-tab">
            <div className="summary-card main-stats">
              <h4>System Telemetry</h4>
              <div className="grid-2">
                <div className="stat-mini">
                  <span className="lbl">Total Generation</span>
                  <span className="val">{fmt(state.total_generation?.p_mw, 2)} MW</span>
                </div>
                <div className="stat-mini">
                  <span className="lbl">Total Losses</span>
                  <span className="val text-danger">{fmt(state.losses?.p_mw, 3)} MW</span>
                </div>
              </div>
              <div className="grid-2" style={{ marginTop: 10 }}>
                <div className="stat-mini">
                  <span className="lbl">Power Flow</span>
                  <span className={`val ${state.converged ? 'text-success' : 'text-danger'}`}>
                    {state.converged ? 'Converged ✓' : 'Diverged ✗'}
                  </span>
                </div>
                <button className="btn btn-outline" onClick={resetGrid}>
                  <RefreshCw size={14} /> Reset
                </button>
              </div>
            </div>

            <div className="summary-card">
              <h4>Voltage Profile</h4>
              <div className="v-bars">
                {state.buses.map(b => (
                  <div key={b.id} className="v-bar-row">
                    <span className="bus-id">B{b.id}</span>
                    <div className="bar-bg">
                      <div className="bar-fill" style={{
                        width: `${Math.min(100, Math.max(0, ((b.v_pu ?? 1) - 0.8) / 0.4 * 100))}%`,
                        backgroundColor: (b.v_pu ?? 1) < 0.95 || (b.v_pu ?? 1) > 1.05 ? 'var(--warning)' : 'var(--success)',
                      }} />
                    </div>
                    <span className="bus-v">{fmt(b.v_pu, 3)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'generators' && (
          <table className="grid-table">
            <thead><tr><th>Bus</th><th>Type</th><th>P gen (MW)</th><th>Q gen (Mvar)</th><th>V (pu)</th></tr></thead>
            <tbody>
              {state.buses.filter(b => b.is_gen || b.is_slack || b.is_condenser).map(b => (
                <tr key={b.id} onClick={() => setSelectedElement({ type: 'bus', id: b.id, data: b })}>
                  <td>Bus {b.id}</td>
                  <td>{b.is_slack ? 'Slack' : b.is_condenser ? 'Condenser' : 'Generator'}</td>
                  <td>{fmt(b.p_gen_mw, 2)}</td>
                  <td>{fmt(b.q_gen_mvar, 2)}</td>
                  <td>{fmt(b.v_pu, 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {activeTab === 'loads' && (
          <table className="grid-table">
            <thead><tr><th>Bus</th><th>P load (MW)</th><th>Q load (Mvar)</th><th>V (pu)</th></tr></thead>
            <tbody>
              {state.buses.filter(b => b.is_load).map(b => (
                <tr key={b.id} onClick={() => setSelectedElement({ type: 'bus', id: b.id, data: b })}>
                  <td>Bus {b.id}</td>
                  <td>{fmt(b.p_load_mw, 2)}</td>
                  <td>{fmt(b.q_load_mvar, 2)}</td>
                  <td>{fmt(b.v_pu, 4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {activeTab === 'transformers' && (
          <table className="grid-table">
            <thead><tr><th>Name</th><th>From→To</th><th>P (MW)</th><th>Loading</th><th>Status</th></tr></thead>
            <tbody>
              {state.branches.filter(b => b.type === 'transformer').map(b => (
                <tr key={b.id} onClick={() => setSelectedElement({ type: 'branch', id: b.id, data: b })}>
                  <td>{b.name}</td>
                  <td>{b.from_bus}→{b.to_bus}</td>
                  <td>{fmt(b.p_flow_mw, 2)}</td>
                  <td className={(b.loading_pct ?? 0) > 95 ? 'text-danger' : 'text-success'}>{fmt(b.loading_pct, 1)}%</td>
                  <td><span className={`badge ${b.active ? 'badge-success' : 'badge-danger'}`}>{b.active ? 'Online' : 'Outage'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {activeTab === 'branches' && (
          <table className="grid-table">
            <thead><tr><th>Name</th><th>From→To</th><th>P (MW)</th><th>Loss (MW)</th><th>Loading</th><th>Status</th></tr></thead>
            <tbody>
              {state.branches.filter(b => b.type === 'line').map(b => (
                <tr key={b.id} onClick={() => setSelectedElement({ type: 'branch', id: b.id, data: b })}>
                  <td>{b.name}</td>
                  <td>{b.from_bus}→{b.to_bus}</td>
                  <td>{fmt(b.p_flow_mw, 2)}</td>
                  <td>{fmt(b.p_loss_mw, 3)}</td>
                  <td className={(b.loading_pct ?? 0) > 95 ? 'text-danger' : (b.loading_pct ?? 0) > 80 ? 'text-warning' : 'text-success'}>{fmt(b.loading_pct, 1)}%</td>
                  <td><span className={`badge ${b.active ? 'badge-success' : 'badge-danger'}`}>{b.active ? 'Online' : 'Outage'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

      </div>
    </div>
  );

  return (
    <div className="detail-panel">
      {selectedElement ? (selectedElement.type === 'bus' ? renderBus() : renderBranch()) : renderOverview()}
    </div>
  );
}
