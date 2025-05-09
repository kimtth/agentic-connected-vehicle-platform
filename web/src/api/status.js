import { api } from './apiClient';

/**
 * Fetch the current vehicle status
 * @param {string} vehicleId 
 * @returns {Promise<Object>} Vehicle status data
 */
export const fetchVehicleStatus = async (vehicleId) => {
  try {
    // Use the API endpoint which will try Cosmos DB first, then simulator as fallback
    const response = await api.get(`/vehicle/${vehicleId}/status`);
    if (response.data) {
      return response.data;
    } else {
      throw new Error("No status data returned");
    }
  } catch (error) {
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
