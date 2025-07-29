import { api } from './apiClient';
import { API_BASE_URL } from './config';
import { INTERVALS } from '../config/intervals';

/**
 * Fetch the current vehicle status
 * @param {string} vehicleId 
 * @param {number} retries Number of retries if request fails (default: 2)
 * @returns {Promise<Object>} Vehicle status data
 */
export const fetchVehicleStatus = async (vehicleId, retries = 2) => {
  try {
    // Use the correct API endpoint that matches backend - use plural "vehicles" for status
    const response = await api.get(`/api/vehicles/${encodeURIComponent(vehicleId)}/status`);
    if (response.data) {
      return response.data;
    } else {
      throw new Error("No status data returned");
    }
  } catch (error) {
    // Handle 404 errors specifically
    if (error.response && error.response.status === 404) {
      console.error(`Vehicle status endpoint not found for vehicle ID: ${vehicleId}. Make sure the backend API is running and the endpoint is implemented.`);
      
      // If we have retries left, try again after a short delay
      if (retries > 0) {
        console.log(`Retrying vehicle status fetch for ${vehicleId}. Retries left: ${retries - 1}`);
        await new Promise(resolve => setTimeout(resolve, 1000)); // 1 second delay
        return fetchVehicleStatus(vehicleId, retries - 1);
      }
    }
    
    // Handle 405 Method Not Allowed specifically
    if (error.response && error.response.status === 405) {
      console.error(`Method not allowed for vehicle status endpoint. This suggests the backend endpoint exists but doesn't support GET requests for vehicle ID: ${vehicleId}`);
    }
    
    console.error(`Error fetching vehicle status for ${vehicleId}:`, error);
    throw error;
  }
};

/**
 * Stream vehicle status updates
 * @param {string} vehicleId 
 * @param {function} onStatusUpdate Callback for status updates
 * @param {function} onError Callback for errors
 * @returns {function} Cleanup function to stop streaming
 */
export const streamVehicleStatus = (vehicleId, onStatusUpdate, onError) => {
  const eventSource = new EventSource(`${API_BASE_URL}/api/vehicle/${encodeURIComponent(vehicleId)}/status/stream`);
  
  eventSource.onmessage = (event) => {
    try {
      const statusData = JSON.parse(event.data);
      onStatusUpdate(statusData);
    } catch (error) {
      console.error('Error parsing status update:', error);
      onError(error);
    }
  };
  
  eventSource.onerror = (error) => {
    console.error('Error in status stream:', error);
    onError(error);
  };
  
  // Return cleanup function
  return () => {
    eventSource.close();
  };
};

/**
 * Update vehicle status
 * @param {string} vehicleId 
 * @param {Object} statusData 
 * @returns {Promise<Object>} Updated status
 */
export const updateVehicleStatus = async (vehicleId, statusData) => {
  try {
    // Backend uses singular "vehicle" for status updates
    const response = await api.put(`/api/vehicle/${encodeURIComponent(vehicleId)}/status`, statusData);
    return response.data;
  } catch (error) {
    console.error(`Error updating vehicle status for ${vehicleId}:`, error);
    throw error;
  }
};

/**
 * Partially update vehicle status
 * @param {string} vehicleId 
 * @param {Object} statusUpdates 
 * @returns {Promise<Object>} Updated status
 */
export const patchVehicleStatus = async (vehicleId, statusUpdates) => {
  try {
    // Backend uses singular "vehicle" for status patches
    const response = await api.patch(`/api/vehicle/${encodeURIComponent(vehicleId)}/status`, statusUpdates);
    return response.data;
  } catch (error) {
    console.error(`Error patching vehicle status for ${vehicleId}:`, error);
    throw error;
  }
};

/**
 * Subscribe to vehicle status updates (wrapper for streamVehicleStatus)
 * @param {string} vehicleId 
 * @param {function} onStatusUpdate Callback for status updates
 * @param {function} onError Callback for errors
 * @returns {function} Cleanup function to stop streaming
 */
export const subscribeToVehicleStatus = (vehicleId, onStatusUpdate, onError) => {
  return streamVehicleStatus(vehicleId, onStatusUpdate, onError);
};

/**
 * Update climate settings for a vehicle
 * @param {string} vehicleId 
 * @param {Object} climateSettings - Climate settings to update
 * @returns {Promise<Object>} Updated status
 */
export const updateClimateSettings = async (vehicleId, climateSettings) => {
  try {
    // Create a status update that includes climate settings
    const statusUpdate = {
      climateSettings: {
        temperature: climateSettings.temperature || 22,
        fanSpeed: climateSettings.fanSpeed || 0,
        mode: climateSettings.mode || 'off',
        ...climateSettings
      },
      timestamp: new Date().toISOString()
    };

    // Use the patch endpoint to update only specific fields
    const response = await patchVehicleStatus(vehicleId, statusUpdate);
    return response;
  } catch (error) {
    console.error(`Error updating climate settings for ${vehicleId}:`, error);
    throw error;
  }
};

/**
 * Setup polling for vehicle status (fallback when streaming is not available)
 * @param {string} vehicleId 
 * @param {function} onStatusUpdate Callback for status updates
 * @param {function} onError Callback for errors
 * @param {number} interval Polling interval in milliseconds
 * @returns {function} Cleanup function to stop polling
 */
export const setupPolling = (vehicleId, onStatusUpdate, onError, interval = INTERVALS.REALTIME_POLLING) => {
  let isActive = true;
  
  const poll = async () => {
    if (!isActive) return;
    
    try {
      const status = await fetchVehicleStatus(vehicleId);
      if (isActive) {
        onStatusUpdate(status);
      }
    } catch (error) {
      if (isActive) {
        console.error('Polling error:', error);
        onError(error);
      }
    }
    
    if (isActive) {
      setTimeout(poll, interval);
    }
  };
  
  // Start polling
  poll();
  
  // Return cleanup function
  return () => {
    isActive = false;
  };
};
