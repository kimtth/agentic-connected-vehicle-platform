/**
 * API functions for sending commands to vehicles
 */

import { API_BASE_URL } from './config';
import { INTERVALS } from '../config/intervals';

/**
 * Send a command to a vehicle
 * @param {string} vehicleId - The ID of the vehicle
 * @param {string} command - The command to send
 * @param {boolean} isCustom - Whether this is a custom command
 * @returns {Promise<Object>} - Response data
 */
export const sendVehicleCommand = async (vehicleId, command, isCustom = false) => {
  try {
    // Update to match backend API structure
    const url = `${API_BASE_URL}/api/command`;
    const payload = {
      vehicleId,
      commandType: command,
      isCustom,
      timestamp: new Date().toISOString(),
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), INTERVALS.REQUEST_TIMEOUT);

    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
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
    // Update to match backend API structure
    const url = `${API_BASE_URL}/api/commands?vehicleId=${encodeURIComponent(vehicleId)}&limit=${limit}`;
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), INTERVALS.REQUEST_TIMEOUT);
    
    const response = await fetch(url, { signal: controller.signal });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
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
    const url = `${API_BASE_URL}/api/commands?limit=${limit}`;
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), INTERVALS.REQUEST_TIMEOUT);
    
    const response = await fetch(url, { signal: controller.signal });
    
    clearTimeout(timeoutId);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
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
