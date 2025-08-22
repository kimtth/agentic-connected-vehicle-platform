import { api } from './apiClient';
import { API_BASE_URL } from './config';
import { INTERVALS } from '../config/intervals';

/**
 * Retry mechanism for failed requests
 * @param {Function} fn - Function to retry
 * @param {number} retries - Number of retries
 * @param {number} delay - Delay between retries
 */
const retryRequest = async (fn, retries = 3, delay = 1000) => {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === retries - 1) throw error;
      if (error.name === 'AbortError') throw error; // Don't retry aborted requests
      if (error.code === 'USER_NOT_AUTHENTICATED') throw error; // Don't retry auth errors
      
      console.log(`Status API retry attempt ${i + 1}/${retries} after ${delay}ms`);
      const wait = delay;
      await new Promise(resolve => setTimeout(resolve, wait));
      delay *= 1.5; // Exponential backoff
    }
  }
}

/**
 * Fetch the current vehicle status
 * @param {string} vehicleId 
 * @param {number} retries Number of retries if request fails (default: 2)
 * @returns {Promise<Object>} Vehicle status data
 */
export const fetchVehicleStatus = async (vehicleId, retries = 2) => {
  try {
    return await retryRequest(async () => {
      const response = await api.get(`/api/vehicles/${encodeURIComponent(vehicleId)}/status`);
      if (response.data) {
        return response.data;
      } else {
        throw new Error("No status data returned");
      }
    }, retries);
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      console.error('Authentication required: User must be logged in to fetch vehicle status');
      throw new Error('Please log in to access vehicle status');
    }
    
    // Handle 404 errors specifically
    if (error.response && error.response.status === 404) {
      console.error(`Vehicle status not found for vehicle ID: ${vehicleId}. Vehicle may not exist or have status data.`);
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
export const streamVehicleStatus = async (vehicleId, onStatusUpdate, onError) => {
  try {
    // Use the new public streaming endpoint that doesn't require authentication
    const streamUrl = `${API_BASE_URL}/api/vehicle/${encodeURIComponent(vehicleId)}/status/stream`;
    
    const eventSource = new EventSource(streamUrl);
    
    eventSource.onmessage = (event) => {
      try {
        const statusData = JSON.parse(event.data);
        
        // Check for errors in the stream
        if (statusData.error) {
          const streamError = new Error(statusData.error);
          streamError.code = 'STREAM_ERROR';
          onError(streamError);
          return;
        }
        
        onStatusUpdate(statusData);
      } catch (error) {
        console.error('Error parsing status update:', error);
        onError(error);
      }
    };
    
    eventSource.onerror = (error) => {
      console.error('Error in status stream:', error);
      
      // Check if this might be a connection error
      if (eventSource.readyState === EventSource.CLOSED) {
        const streamError = new Error('Status stream connection closed');
        streamError.code = 'STREAM_CLOSED';
        onError(streamError);
      } else {
        onError(error);
      }
    };
    
    // Return cleanup function
    return () => {
      eventSource.close();
    };
  } catch (error) {
    console.error('Error setting up status stream:', error);
    throw error;
  }
};

/**
 * Update vehicle status
 * @param {string} vehicleId 
 * @param {Object} statusData 
 * @returns {Promise<Object>} Updated status
 */
export const updateVehicleStatus = async (vehicleId, statusData) => {
  try {
    return await retryRequest(async () => {
      const response = await api.put(`/api/vehicle/${encodeURIComponent(vehicleId)}/status`, statusData);
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      console.error('Authentication required: User must be logged in to update vehicle status');
      throw new Error('Please log in to update vehicle status');
    }
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
    return await retryRequest(async () => {
      const response = await api.patch(`/api/vehicle/${encodeURIComponent(vehicleId)}/status`, statusUpdates);
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      console.error('Authentication required: User must be logged in to update vehicle status');
      throw new Error('Please log in to update vehicle status');
    }
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