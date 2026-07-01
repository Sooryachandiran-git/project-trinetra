import React, { useState } from 'react';
import { useGridState } from './hooks/useGridState';
import { SingleLineDiagram } from './components/SingleLineDiagram';
import { DetailPanel } from './components/DetailPanel';
import { Activity, AlertTriangle, RefreshCw, Zap } from 'lucide-react';

function App() {
  console.log("App component: executing function");
  const {
    state,
    topology,
    loading,
    error,
    updateSetpoint,
    resetGrid,
    refetchState
  } = useGridState(2000);

  const [selectedElement, setSelectedElement] = useState(null);

  return (
    <div className="app-container">
      {/* Navigation bar */}
      <nav className="app-navbar">
        <div className="app-logo">
          <Activity size={24} className="logo-icon animate-pulse" />
          <span>TRINETRA IEEE-14 Bus Digital Twin</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          {error ? (
            <div className="badge badge-danger" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <AlertTriangle size={12} />
              Connection Offline
            </div>
          ) : (
            <div className="badge badge-success" style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
              <Zap size={12} className="text-success" />
              Live Telemetry Polling
            </div>
          )}
          <button className="btn btn-outline" onClick={refetchState} disabled={loading} style={{ padding: '0.35rem 0.75rem', fontSize: '0.75rem' }}>
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            Solve Now
          </button>
        </div>
      </nav>

      {/* Main dashboard content */}
      <div className="app-main">
        {error ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifySelf: 'center', justifyContent: 'center', padding: '3rem', textAlign: 'center' }}>
            <AlertTriangle size={48} className="text-danger" style={{ marginBottom: '1rem' }} />
            <h3>Offline or Connection Failed</h3>
            <p className="text-muted" style={{ maxWidth: '400px', marginTop: '0.5rem', marginBottom: '1.5rem' }}>
              Could not communicate with the digital twin simulator backend. Please check that the uvicorn FastAPI server is running on port 8000.
            </p>
            <button className="btn btn-primary" onClick={refetchState}>
              <RefreshCw size={14} /> Retry Connection
            </button>
          </div>
        ) : !state ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <div className="spinner"></div>
            <p className="text-muted">Resolving IEEE 14-bus topology...</p>
          </div>
        ) : (
          <>
            {/* Main Interactive Diagram Canvas */}
            <SingleLineDiagram
              state={state}
              selectedElement={selectedElement}
              setSelectedElement={setSelectedElement}
            />

            {/* Side Detail Panel / Summary Dashboard */}
            <DetailPanel
              selectedElement={selectedElement}
              setSelectedElement={setSelectedElement}
              updateSetpoint={updateSetpoint}
              resetGrid={resetGrid}
              state={state}
              topology={topology}
            />
          </>
        )}
      </div>
    </div>
  );
}

export default App;
