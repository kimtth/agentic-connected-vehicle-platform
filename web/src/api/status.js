import { api } from './apiClient';

/**
 * Fetch the current vehicle status
 * @param {string} vehicleId 
 * @param {number} retries Number of retries if request fails (default: 2)
 * @returns {Promise<Object>} Vehicle status data
 */
export const fetchVehicleStatus = async (vehicleId, retries = 2) => {
  try {
    // Use the API endpoint which will try Cosmos DB first, then simulator as fallback
    const response = await api.get(`/vehicle/${vehicleId}/status`);
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
        console.log(`Retrying fetchVehicleStatus (${retries} attempts left)...`);
        await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
        return fetchVehicleStatus(vehicleId, retries - 1);
      }
      
      throw new Error(`Status API endpoint not available (404) for vehicle: ${vehicleId}. Please check if the API server is running and the endpoint is implemented.`);
    }
    
    console.error("Error fetching vehicle status:", error);
    throw error;
  }
};

/**
 * Subscribe to real-time updates for a vehicle using SSE
 * @param {string} vehicleId 
 * @param {Function} onUpdate Callback for status updates
 * @param {Function} onError Callback for errors
 * @returns {Object} Subscription object with unsubscribe method
 */
export const subscribeToVehicleStatus = async (vehicleId, onUpdate, onError) => {
  try {
    // First get initial status
    const initialStatus = await fetchVehicleStatus(vehicleId);
    onUpdate(initialStatus);
    
    // Check if EventSource is available (for SSE)
    if (typeof EventSource !== 'undefined') {
      // Try to use server-sent events for real-time updates
      const eventSource = new EventSource(`${api.defaults.baseURL}/vehicle/${vehicleId}/status/stream`);
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          onUpdate(data);
        } catch (err) {
          console.error("Error parsing SSE data:", err);
        }
      };
      
      eventSource.onerror = (error) => {
        console.error("SSE error:", error);
        if (onError) onError(error);
        
        // Fallback to polling if SSE fails
        eventSource.close();
        return setupPolling(vehicleId, onUpdate, onError);
      };
      
      return {
        unsubscribe: () => {
          eventSource.close();
        }
      };
    } else {
      console.warn("EventSource not supported in this browser. Falling back to polling.");
      return setupPolling(vehicleId, onUpdate, onError);
    }
  } catch (error) {
    console.error("Error setting up status subscription:", error);
    if (onError) {
      onError(error);
    }
    
    // Fallback to polling
    return setupPolling(vehicleId, onUpdate, onError);
  }
};

/**
 * Helper function to set up polling as a fallback
 */
function setupPolling(vehicleId, onUpdate, onError) {
  const interval = setInterval(async () => {
    try {
      const status = await fetchVehicleStatus(vehicleId);
      onUpdate(status);
    } catch (err) {
      if (onError) onError(err);
    }
  }, 5000); // Poll every 5 seconds
  
  return {
    unsubscribe: () => clearInterval(interval)
  };
}

/**
 * Update the complete vehicle status
 * @param {string} vehicleId 
 * @param {Object} statusData Complete status object
 * @returns {Promise<Object>} Updated status
 */
export const updateVehicleStatus = async (vehicleId, statusData) => {
  try {
    // Make sure vehicleId is included in the data
    const data = {
      ...statusData,
      vehicleId: vehicleId
    };
    
    const response = await api.put(`/vehicle/${vehicleId}/status`, data);
    return response.data;
  } catch (error) {
    console.error(`Error updating vehicle status: ${error}`);
    throw error;
  }
};

/**
 * Update only specific fields of vehicle status (partial update)
 * @param {string} vehicleId 
 * @param {Object} partialStatus Partial status object with only the fields to update
 * @returns {Promise<Object>} Updated status
 */
export const updatePartialStatus = async (vehicleId, partialStatus) => {
  try {
    const response = await api.patch(`/vehicle/${vehicleId}/status`, partialStatus);
    return response.data;
  } catch (error) {
    console.error(`Error updating vehicle status fields: ${error}`);
    throw error;
  }
};

/**
 * Update climate settings
 * @param {string} vehicleId 
 * @param {Object} climateSettings Climate control settings
 * @returns {Promise<Object>} Updated status
 */
export const updateClimateSettings = async (vehicleId, climateSettings) => {
  try {
    const partialStatus = {
      climateSettings: climateSettings
    };
    
    return await updatePartialStatus(vehicleId, partialStatus);
  } catch (error) {
    console.error(`Error updating climate settings: ${error}`);
    throw error;
  }
};
