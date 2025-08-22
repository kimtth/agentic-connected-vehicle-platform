import { api } from './apiClient';

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
      
      console.log(`Vehicle features API retry attempt ${i + 1}/${retries} after ${delay}ms`);
      const wait = delay;
      await new Promise(resolve => setTimeout(resolve, wait));
      delay *= 1.5; // Exponential backoff
    }
  }
}

// Vehicle Features API
export const controlLights = async (vehicleId, lightType, action) => {
  try {
    return await retryRequest(async () => {
      const response = await api.post(
        `/api/vehicles/${vehicleId}/features/lights`,
        { light_type: lightType, action }
      );
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      throw new Error('Please log in to control vehicle lights');
    }
    throw new Error(error.response?.data?.detail || 'Failed to control lights');
  }
};

export const controlClimate = async (vehicleId, temperature, action = 'set_temperature', auto = true) => {
  try {
    return await retryRequest(async () => {
      const response = await api.post(
        `/api/vehicles/${vehicleId}/features/climate`,
        { temperature, action, auto }
      );
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      throw new Error('Please log in to control vehicle climate');
    }
    throw new Error(error.response?.data?.detail || 'Failed to control climate');
  }
};

export const controlWindows = async (vehicleId, action, windows = 'all') => {
  try {
    return await retryRequest(async () => {
      const response = await api.post(
        `/api/vehicles/${vehicleId}/features/windows`,
        { action, windows }
      );
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      throw new Error('Please log in to control vehicle windows');
    }
    throw new Error(error.response?.data?.detail || 'Failed to control windows');
  }
};

export const getFeatureStatus = async (vehicleId) => {
  try {
    return await retryRequest(async () => {
      const response = await api.get(
        `/api/vehicles/${vehicleId}/features/status`
      );
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      throw new Error('Please log in to access vehicle feature status');
    }
    throw new Error(error.response?.data?.detail || 'Failed to get feature status');
  }
};

// Remote Access API - Updated to match backend routes
export const controlDoors = async (vehicleId, action) => {
  try {
    return await retryRequest(async () => {
      const response = await api.post(
        `/api/vehicles/${vehicleId}/remote-access/doors`,
        { action }
      );
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      throw new Error('Please log in to control vehicle doors');
    }
    throw new Error(error.response?.data?.detail || 'Failed to control doors');
  }
};

export const controlEngine = async (vehicleId, action) => {
  try {
    return await retryRequest(async () => {
      const response = await api.post(
        `/api/vehicles/${vehicleId}/remote-access/engine`,
        { action }
      );
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      throw new Error('Please log in to control vehicle engine');
    }
    throw new Error(error.response?.data?.detail || 'Failed to control engine');
  }
};

export const locateVehicle = async (vehicleId) => {
  try {
    return await retryRequest(async () => {
      const response = await api.post(
        `/api/vehicles/${vehicleId}/remote-access/locate`
      );
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      throw new Error('Please log in to locate vehicle');
    }
    throw new Error(error.response?.data?.detail || 'Failed to locate vehicle');
  }
};

// Emergency & Safety API - Updated to match backend routes
export const emergencyCall = async (vehicleId, emergencyType = 'general') => {
  try {
    return await retryRequest(async () => {
      const response = await api.post(
        `/api/vehicles/${vehicleId}/emergency/call`,
        { emergency_type: emergencyType }
      );
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      throw new Error('Please log in to make emergency calls');
    }
    throw new Error(error.response?.data?.detail || 'Failed to initiate emergency call');
  }
};

export const reportCollision = async (vehicleId, severity = 'unknown', location = null) => {
  try {
    return await retryRequest(async () => {
      const response = await api.post(
        `/api/vehicles/${vehicleId}/emergency/collision`,
        { severity, location }
      );
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      throw new Error('Please log in to report collisions');
    }
    throw new Error(error.response?.data?.detail || 'Failed to report collision');
  }
};

export const reportTheft = async (vehicleId, description = null, lastSeenLocation = null) => {
  try {
    return await retryRequest(async () => {
      const response = await api.post(
        `/api/vehicles/${vehicleId}/emergency/theft`,
        { description, last_seen_location: lastSeenLocation }
      );
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      throw new Error('Please log in to report theft');
    }
    throw new Error(error.response?.data?.detail || 'Failed to report theft');
  }
};

export const activateSOS = async (vehicleId) => {
  try {
    return await retryRequest(async () => {
      const response = await api.post(
        `/api/vehicles/${vehicleId}/emergency/sos`
      );
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      throw new Error('Please log in to activate SOS');
    }
    throw new Error(error.response?.data?.detail || 'Failed to activate SOS');
  }
};
