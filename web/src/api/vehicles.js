// API functions for vehicle data

import { API_BASE_URL } from './config';

/**
 * Fetches all vehicles from the backend
 * @returns {Promise<Array>} - Array of vehicle objects
 */
export const fetchVehicles = async () => {
  try {
    console.log(`Attempting to fetch vehicles from: ${API_BASE_URL}/vehicles`);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10-second timeout
    
    const response = await fetch(`${API_BASE_URL}/vehicles`, {
      signal: controller.signal
    });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(`Failed to fetch vehicles: ${response.status} ${response.statusText} - ${JSON.stringify(errorData)}`);
    }
    
    return await response.json();
  } catch (error) {
    if (error.name === 'AbortError') {
      console.error('Request timeout: Could not connect to the backend server. Please ensure the server is running.');
    } else if (error.message.includes('Failed to fetch')) {
      console.error('Connection error: Could not reach the backend server. Please verify that:');
      console.error('1. The backend server is running at ' + API_BASE_URL);
      console.error('2. There are no network connectivity issues');
      console.error('3. The API URL in .env is configured correctly');
    } else {
      console.error('Error fetching vehicles:', error);
    }
    throw error;
  }
};

/**
 * Fetches a specific vehicle by ID
 * @param {string} vehicleId - The ID of the vehicle to fetch
 * @returns {Promise<Object>} - Vehicle object
 */
export const fetchVehicleById = async (vehicleId) => {
  try {
    const response = await fetch(`${API_BASE_URL}/vehicle/${vehicleId}`);
    
    if (!response.ok) {
      throw new Error(`Failed to fetch vehicle: ${response.status} ${response.statusText}`);
    }
    
    const vehicle = await response.json();
    
    // Ensure consistent field naming
    if (vehicle.VehicleId && !vehicle.vehicleId) {
      vehicle.vehicleId = vehicle.VehicleId;
    }
    
    return vehicle;
  } catch (error) {
    console.error(`Error fetching vehicle ${vehicleId}:`, error);
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
    
    const response = await fetch(`${API_BASE_URL}/vehicle`, {
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
  } catch (error) {
    console.error('Error adding vehicle:', error);
    throw error;
  }
};
