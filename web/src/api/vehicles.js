// API functions for vehicle data

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
      
      console.log(`Retry attempt ${i + 1}/${retries} after ${delay}ms`);
      const currentDelay = delay;
      await new Promise(resolve => setTimeout(resolve, currentDelay));
      delay *= 1.5; // Exponential backoff
    }
  }
};

/**
 * Create a fetch request with timeout and abort signal
 * @param {string} url - Request URL
 * @param {Object} options - Fetch options
 * @param {number} timeout - Timeout in milliseconds
 */
const fetchWithTimeout = async (url, options = {}, timeout = INTERVALS.REQUEST_TIMEOUT) => {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);
  
  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);
    throw error;
  }
};

/**
 * Fetches all vehicles from the backend
 * @returns {Promise<Array>} - Array of vehicle objects
 */
export const fetchVehicles = async () => {
  try {
    console.log(`Attempting to fetch vehicles from: ${API_BASE_URL}/api/vehicles`);
    
    return await retryRequest(async () => {
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/vehicles`);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(`Failed to fetch vehicles: ${response.status} ${response.statusText} - ${JSON.stringify(errorData)}`);
      }
      
      return await response.json();
    }, 2, 2000); // 2 retries with 2 second initial delay
    
  } catch (error) {
    if (error.name === 'AbortError') {
      console.error('Request timeout: Could not connect to the backend server. Please ensure the server is running.');
      throw new Error('Connection timeout - backend server may not be running');
    } else if (error.message.includes('Failed to fetch') || error.message.includes('fetch')) {
      console.error('Connection error: Could not reach the backend server. Please verify that:');
      console.error('1. The backend server is running at ' + API_BASE_URL);
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
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/vehicles/${encodeURIComponent(vehicleId)}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch vehicle: ${response.status} ${response.statusText}`);
      }
      
      const vehicle = await response.json();
      
      // Ensure consistent field naming
      if (vehicle.VehicleId && !vehicle.vehicleId) {
        vehicle.vehicleId = vehicle.VehicleId;
      }
      
      return vehicle;
    });
  } catch (error) {
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
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/vehicles/${encodeURIComponent(vehicleId)}/status`);
      
      if (!response.ok) {
        if (response.status === 404) {
          throw new Error(`Vehicle ${vehicleId} not found`);
        }
        throw new Error(`Failed to fetch vehicle status: ${response.status} ${response.statusText}`);
      }
      
      return await response.json();
    });
  } catch (error) {
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
      const response = await fetchWithTimeout(`${API_BASE_URL}/api/vehicle`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to add vehicle: ${response.status} ${response.statusText}`);
      }
      
      return await response.json();
    });
  } catch (error) {
    console.error('Error adding vehicle:', error);
    throw error;
  }
};
