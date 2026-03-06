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

    if (!response.ok) {
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
