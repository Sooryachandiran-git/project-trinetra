/**
 * FastAPI Bridge Service
 * Handles all HTTP communication between the React Frontend and the FastAPI Backend.
 */

const API_BASE_URL = 'http://localhost:8000/api';

export const sendDeployPayload = async (jsonPayload) => {
  try {
    const response = await fetch(`${API_BASE_URL}/deploy`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(jsonPayload),
    });

    // Accept 200 (OK) or 202 (Accepted)
    if (!response.ok && response.status !== 202) {
      const errorData = await response.json();
      throw new Error(errorData.detail || 'Failed to deploy architecture');
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};

export const sendStopSimulation = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/stop`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to stop simulation');
    }

    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
};

export const startAttack = async (payload) => {
  const response = await fetch(`${API_BASE_URL}/attack/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error('Failed to start attack');
  return response.json();
};

export const stopAttack = async (attackId) => {
  const response = await fetch(`${API_BASE_URL}/attack/stop/${attackId}`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to stop attack');
  return response.json();
};

export const fetchTelemetryHistory = async (topologyId, minutes = 60) => {
  const response = await fetch(`${API_BASE_URL}/history/telemetry?topology_id=${topologyId}&minutes=${minutes}`);
  if (!response.ok) throw new Error('Failed to fetch telemetry history');
  return response.json();
};

export const fetchAlarmHistory = async (hours = 24) => {
  const response = await fetch(`${API_BASE_URL}/history/alarms?hours=${hours}`);
  if (!response.ok) throw new Error('Failed to fetch alarm history');
  return response.json();
};

export const getExportDatasetUrl = (topologyId) => {
  return `${API_BASE_URL}/history/export/${topologyId}`;
};
