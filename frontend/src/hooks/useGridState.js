import { useState, useEffect, useCallback } from 'react';

const API_BASE = 'http://127.0.0.1:8000';

export function useGridState(pollIntervalMs = 2000) {
  const [state, setState] = useState(null);
  const [topology, setTopology] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch initial static topology
  const fetchTopology = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/topology`);
      if (!res.ok) throw new Error('Failed to fetch topology');
      const data = await res.json();
      setTopology(data);
    } catch (err) {
      console.error(err);
      setError(err.message);
    }
  }, []);

  // Fetch live simulation state
  const fetchState = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/state`);
      if (!res.ok) throw new Error('Failed to fetch state');
      const data = await res.json();
      setState(data);
      setError(null);
    } catch (err) {
      console.error(err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  // Update setpoint via unified API
  const updateSetpoint = useCallback(async (type, payload) => {
    try {
      const res = await fetch(`${API_BASE}/api/setpoint`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, ...payload }),
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to update setpoint');
      }
      const data = await res.json();
      setState(data); // Immediate update from response
      return { success: true };
    } catch (err) {
      console.error(err);
      return { success: false, error: err.message };
    }
  }, []);

  // Reset grid parameters to default
  const resetGrid = useCallback(async () => {
    return updateSetpoint('reset', {});
  }, [updateSetpoint]);

  useEffect(() => {
    fetchTopology();
    fetchState();

    const interval = setInterval(fetchState, pollIntervalMs);
    return () => clearInterval(interval);
  }, [fetchTopology, fetchState, pollIntervalMs]);

  return {
    state,
    topology,
    loading,
    error,
    updateSetpoint,
    resetGrid,
    refetchState: fetchState
  };
}
