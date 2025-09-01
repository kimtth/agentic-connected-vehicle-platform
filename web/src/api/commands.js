/**
 * API functions for sending commands to vehicles
 */

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
      
      console.log(`Command API retry attempt ${i + 1}/${retries} after ${delay}ms`);
      const wait = delay;
      await new Promise(resolve => setTimeout(resolve, wait));
      delay *= 1.5; // Exponential backoff
    }
  }
};

/**
 * Send a command to a vehicle
 * @param {string} vehicleId - The ID of the vehicle
 * @param {string} command - The command to send
 * @param {boolean} isCustom - Whether this is a custom command
 * @param {Object} payload - Optional payload for the command
 * @returns {Promise<Object>} - Response data
 */
export const sendVehicleCommand = async (vehicleId, command, isCustom = false, payload) => {
  // Allow object-form: sendVehicleCommand({ vehicleId, commandType, command, isCustom, payload })
  if (typeof vehicleId === 'object' && vehicleId !== null) {
    const o = vehicleId;
    payload = o.payload;
    isCustom = !!o.isCustom;
    command = o.commandType || o.command;
    vehicleId = o.vehicleId;
  }
  try {
    const body = {
      vehicleId,
      commandType: command,
      isCustom,
      timestamp: new Date().toISOString(),
      ...(payload !== undefined ? { payload } : {})
    };
    return await retryRequest(async () => {
      const response = await api.post('/api/command', body);
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      console.error('Authentication required: User must be logged in to send vehicle commands');
      throw new Error('Please log in to send vehicle commands');
    }
    console.error('Error sending vehicle command:', error);
    throw error;
  }
};

/**
 * Get command history for a vehicle
 * @param {string} vehicleId - The ID of the vehicle
 * @param {number} limit - Maximum number of commands to return
 * @returns {Promise<Array>} - Array of command history items
 */
export const getCommandHistory = async (vehicleId, limit = 20) => {
  try {
    return await retryRequest(async () => {
      const response = await api.get(`/api/commands?vehicleId=${encodeURIComponent(vehicleId)}&limit=${limit}`);
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      console.error('Authentication required: User must be logged in to access command history');
      throw new Error('Please log in to access command history');
    }
    console.error('Error fetching command history:', error);
    throw error;
  }
};

/**
 * Get all commands (no vehicle filter)
 * @param {number} limit - Maximum number of commands to return
 * @returns {Promise<Array>} - Array of command history items
 */
export const getAllCommands = async (limit = 50) => {
  try {
    return await retryRequest(async () => {
      const response = await api.get(`/api/commands?limit=${limit}`);
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      console.error('Authentication required: User must be logged in to access commands');
      throw new Error('Please log in to access commands');
    }
    console.error('Error fetching all commands:', error);
    throw error;
  }
};

const commandsApi = {
  sendVehicleCommand,
  getCommandHistory,
  getAllCommands,
};

export default commandsApi;

