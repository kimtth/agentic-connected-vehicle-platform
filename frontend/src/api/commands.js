import { api } from './apiClient';

/**
 * Fetch command log from the backend API
 * @returns {Promise<Array>} Array of command objects
 */
export const fetchCommands = async () => {
  try {
    const response = await api.get('/commands');

    if (!response.data) {
      return [];
    }

    // Map the data to match the expected format in UI
    const commands = response.data.map((command) => ({
      commandId: command.commandId,
      vehicleId: command.vehicleId,
      commandType: command.commandType,
      status: command.status,
      timestamp: command.timestamp,
      parameters: command.parameters || command.payload || {},
      executedTime: command.executedTime || command.completion_time,
      error: command.error || null,
    }));

    // Sort by timestamp - most recent first
    return commands.sort(
      (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
    );
  } catch (error) {
    console.error('Error fetching commands:', error);
    throw error;
  }
};

/**
 * Send a command to a vehicle
 * @param {Object} command Command object to send
 * @returns {Promise<Object>} Response containing commandId
 */
export const sendCommand = async (command) => {
  try {
    const response = await api.post('/command', command);
    return response.data;
  } catch (error) {
    console.error('Error sending command:', error);
    throw error;
  }
};

/**
 * Get details for a specific command
 * @param {string} commandId
 * @returns {Promise<Object>} Command details
 */
export const getCommandDetails = async (commandId) => {
  try {
    const response = await api.get(`/command/${commandId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching command details:', error);
    throw error;
  }
};

/**
 * Cancel a pending command
 * @param {string} commandId
 * @returns {Promise<Object>} Cancelled command
 */
export const cancelCommand = async (commandId) => {
  try {
    const response = await api.post(`/command/${commandId}/cancel`);
    return response.data;
  } catch (error) {
    console.error('Error cancelling command:', error);
    throw error;
  }
};
