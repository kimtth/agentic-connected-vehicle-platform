// API functions for vehicle data

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
      
      console.log(`Retry attempt ${i + 1}/${retries} after ${delay}ms`);
      const currentDelay = delay;
      await new Promise(resolve => setTimeout(resolve, currentDelay));
      delay *= 1.5; // Exponential backoff
    }
  }
};

/**
 * Fetches all vehicles from the backend
 * @returns {Promise<Array>} - Array of vehicle objects
 */
export const fetchVehicles = async () => {
  try {
    console.log(`Attempting to fetch vehicles from authenticated API`);
    
    return await retryRequest(async () => {
      const response = await api.get('/api/vehicles');
      return response.data;
    }, 2, 2000); // 2 retries with 2 second initial delay
    
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      console.error('Authentication required: User must be logged in to fetch vehicles');
      throw new Error('Please log in to access vehicle data');
    } else if (error.code === 'ECONNABORTED') {
      console.error('Request timeout: Could not connect to the backend server. Please ensure the server is running.');
      throw new Error('Connection timeout - backend server may not be running');
    } else if (error.message?.includes('Network Error') || error.code === 'ERR_NETWORK') {
      console.error('Connection error: Could not reach the backend server. Please verify that:');
      console.error('1. The backend server is running');
      console.error('2. There are no network connectivity issues');
      console.error('3. The API URL in .env is configured correctly');
      throw new Error('Backend server is not reachable - please check server status');
    } else {
      console.error('Error fetching vehicles:', error);
      throw error;
    }
  }
};

/**
 * Fetches a specific vehicle by ID
 * @param {string} vehicleId - The ID of the vehicle to fetch
 * @returns {Promise<Object>} - Vehicle object
 */
export const fetchVehicleById = async (vehicleId) => {
  try {
    return await retryRequest(async () => {
      const response = await api.get(`/api/vehicles/${encodeURIComponent(vehicleId)}`);
      const vehicle = response.data;
      
      // Ensure consistent field naming
      if (vehicle.VehicleId && !vehicle.vehicleId) {
        vehicle.vehicleId = vehicle.VehicleId;
      }
      
      return vehicle;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      console.error('Authentication required: User must be logged in to fetch vehicle details');
      throw new Error('Please log in to access vehicle details');
    }
    console.error(`Error fetching vehicle ${vehicleId}:`, error);
    throw error;
  }
};

/**
 * Fetches vehicle status from the backend
 * @param {string} vehicleId - The ID of the vehicle
 * @returns {Promise<Object>} - Vehicle status object
 */
export const fetchVehicleStatus = async (vehicleId) => {
  try {
    return await retryRequest(async () => {
      const response = await api.get(`/api/vehicles/${encodeURIComponent(vehicleId)}/status`);
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      console.error('Authentication required: User must be logged in to fetch vehicle status');
      throw new Error('Please log in to access vehicle status');
    } else if (error.response?.status === 404) {
      console.error(`Vehicle status not found for vehicle ID: ${vehicleId}. Vehicle may not exist or have status data.`);
      throw new Error(`Vehicle ${vehicleId} not found`);
    }
    console.error(`Error fetching vehicle status for ${vehicleId}:`, error);
    throw error;
  }
};

/**
 * Adds a new vehicle
 * @param {Object} vehicleData - The vehicle data to add
 * @returns {Promise<Object>} - Added vehicle object
 */
export const addVehicle = async (vehicleData) => {
  try {
    // Ensure consistent field naming before sending to backend
    const payload = {
      ...vehicleData,
      vehicleId: vehicleData.vehicleId || vehicleData.VehicleId
    };
    
    return await retryRequest(async () => {
      const response = await api.post('/api/vehicle', payload);
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      console.error('Authentication required: User must be logged in to add vehicles');
      throw new Error('Please log in to add vehicles');
    }
    console.error('Error adding vehicle:', error);
    throw error;
  }
};
