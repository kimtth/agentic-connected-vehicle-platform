import { api } from './apiClient';

// Vehicle APIs
export const fetchVehicles = async () => {
  try {
    const response = await api.get('/vehicles');
    return response.data;
  } catch (error) {
    console.error('Error fetching vehicles:', error);
    throw error;
  }
};

export const addVehicle = async (vehicle) => {
  try {
    const response = await api.post('/vehicle', vehicle);
    return response.data;
  } catch (error) {
    console.error('Error adding vehicle:', error);
    throw error;
  }
};
