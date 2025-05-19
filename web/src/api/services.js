import { api } from './apiClient';

/**
 * Fetch services for a specific vehicle
 * @param {string} vehicleId
 * @returns {Promise<Array>} Array of service objects
 */
export const fetchServices = async (vehicleId) => {
  try {
    const response = await api.get(
      `/vehicle/${encodeURIComponent(vehicleId)}/services`
    );

    if (!response.data) {
      return [];
    }

    // Map the data to match the expected format in UI
    return response.data.map((service) => ({
      ServiceCode: service.ServiceCode || service.serviceCode || service.serviceType,
      Description: service.Description || service.description,
      StartDate: service.StartDate || service.startDate || service.serviceDate,
      EndDate: service.EndDate || service.endDate || service.nextServiceDate || '',
      Cost: service.cost || 0,
      Location: service.location || '',
      Technician: service.technician || '',
      Notes: service.notes || '',
    }));
  } catch (error) {
    console.error('Error fetching services:', error);
    throw error;
  }
};

/**
 * Add a service to a vehicle
 * @param {string} vehicleId
 * @param {Object} service Service data to add
 * @returns {Promise<Object>} Created service
 */
export const addService = async (vehicleId, service) => {
  try {
    const response = await api.post(
      `/vehicle/${encodeURIComponent(vehicleId)}/service`,
      service
    );
    return response.data;
  } catch (error) {
    console.error('Error adding service:', error);
    throw error;
  }
};

/**
 * Update an existing service
 * @param {string} vehicleId
 * @param {string} serviceId
 * @param {Object} updates Service updates
 * @returns {Promise<Object>} Updated service
 */
export const updateService = async (vehicleId, serviceId, updates) => {
  try {
    const response = await api.put(
      `/vehicle/${encodeURIComponent(vehicleId)}/service/${encodeURIComponent(serviceId)}`,
      updates
    );
    return response.data;
  } catch (error) {
    console.error('Error updating service:', error);
    throw error;
  }
};

/**
 * Delete a service
 * @param {string} vehicleId
 * @param {string} serviceId
 * @returns {Promise<void>}
 */
export const deleteService = async (vehicleId, serviceId) => {
  try {
    await api.delete(
      `/vehicle/${encodeURIComponent(vehicleId)}/service/${encodeURIComponent(serviceId)}`
    );
  } catch (error) {
    console.error('Error deleting service:', error);
    throw error;
  }
};
