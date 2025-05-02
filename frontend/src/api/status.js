import { api } from './apiClient';

// Vehicle Status API
export const fetchVehicleStatus = async (vehicleId) => {
  try {
    const response = await api.get(`/vehicle/${vehicleId}/status`);
    return response.data;
  } catch (error) {
    console.error('Error fetching vehicle status:', error);
    throw error;
  }
};
