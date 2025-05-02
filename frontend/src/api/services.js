import { api } from './apiClient';

// Service APIs
export const fetchServices = async (vehicleId) => {
  try {
    const response = await api.get(`/vehicle/${vehicleId}/services`);
    return response.data;
  } catch (error) {
    console.error('Error fetching services:', error);
    throw error;
  }
};

export const addService = async (vehicleId, service) => {
  try {
    const response = await api.post(`/vehicle/${vehicleId}/service`, service);
    return response.data;
  } catch (error) {
    console.error('Error adding service:', error);
    throw error;
  }
};
