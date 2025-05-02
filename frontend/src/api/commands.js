import { api } from './apiClient';

// Command APIs
export const fetchCommands = async () => {
  try {
    return await api.get('/commands');
  } catch (error) {
    console.error('Error fetching commands:', error);
    throw error;
  }
};

export const sendCommand = async (command) => {
  try {
    return await api.post('/command', command);
  } catch (error) {
    console.error('Error sending command:', error);
    throw error;
  }
};
