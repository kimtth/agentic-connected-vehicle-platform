import { api } from './apiClient';

export const askAgent = async (payload) => {
  const response = await api.post('/api/agent/ask', payload);
  return response.data;
};
