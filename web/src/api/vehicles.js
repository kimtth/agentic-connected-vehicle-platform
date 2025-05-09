import { api } from './apiClient';

/**
 * Fetch all vehicles
 * @returns {Promise<Array>} Array of vehicle objects
 */
export const fetchVehicles = async () => {
  try {
    const response = await api.get('/vehicles');

    if (!response.data) {
      return [];
    }

    // Map the data to match the expected format in UI
    return response.data.map((vehicle) => ({
      VehicleId: vehicle.VehicleId || vehicle.id,
      Brand: vehicle.Brand || vehicle.Make || '',
      VehicleModel: vehicle.VehicleModel || vehicle.Model || '',
      Year: vehicle.Year || 0,
      Color: vehicle.Color || '',
      VIN: vehicle.VIN || '',
      LicensePlate: vehicle.LicensePlate || '',
      Status: vehicle.Status || 'Active',
      Mileage: vehicle.Mileage || 0,
      Type: vehicle.Type || '',
      Features: vehicle.Features || {},
      OwnerId: vehicle.OwnerId || '',
    }));
  } catch (error) {
    console.error('Error fetching vehicles:', error);
    throw error;
  }
};

/**
 * Add a new vehicle
 * @param {Object} vehicle Vehicle data to add
 * @returns {Promise<Object>} Created vehicle
 */
export const addVehicle = async (vehicle) => {
  try {
    const response = await api.post('/vehicle', vehicle);
    return response.data;
  } catch (error) {
    console.error('Error adding vehicle:', error);
    throw error;
  }
};

/**
 * Update an existing vehicle
 * @param {string} vehicleId
 * @param {Object} updates Vehicle updates
 * @returns {Promise<Object>} Updated vehicle
 */
export const updateVehicle = async (vehicleId, updates) => {
  try {
    const response = await api.put(`/vehicle/${vehicleId}`, updates);
    return response.data;
  } catch (error) {
    console.error('Error updating vehicle:', error);
    throw error;
  }
};

/**
 * Delete a vehicle
 * @param {string} vehicleId
 * @returns {Promise<void>}
 */
export const deleteVehicle = async (vehicleId) => {
  try {
    await api.delete(`/vehicle/${vehicleId}`);
  } catch (error) {
    console.error('Error deleting vehicle:', error);
    throw error;
  }
};

/**
 * Get details for a specific vehicle
 * @param {string} vehicleId
 * @returns {Promise<Object>} Vehicle details
 */
export const getVehicleDetails = async (vehicleId) => {
  try {
    const response = await api.get(`/vehicle/${vehicleId}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching vehicle details:', error);
    throw error;
  }
};
