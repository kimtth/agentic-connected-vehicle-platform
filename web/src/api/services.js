import { api } from './apiClient';

/**
 * Normalize service object to camelCase
 * @param {Object} service
 * @returns {Object} Normalized service object
 */
function normalizeService(service) {
  return {
    serviceCode: service.serviceCode,
    description: service.description,
    startDate: service.startDate,
    endDate: service.endDate || '',
    cost: service.cost ?? 0,
    location: service.location || '',
    technician: service.technician || '',
    notes: service.notes || '',
    vehicleId: service.vehicleId
  };
}

/**
 * Fetch services for a specific vehicle
 * @param {string} vehicleId
 * @returns {Promise<Array>} Array of service objects
 */
export const fetchServices = async (vehicleId) => {
  try {
    // Update to match backend API structure - use singular "vehicle" not "vehicles"
    const response = await api.get(
      `/api/vehicles/${encodeURIComponent(vehicleId)}/services`
    );

    if (!response.data) {
      return [];
    }

    // Map the data to match the expected format in UI
    return Array.isArray(response.data)
      ? response.data.map(normalizeService)
      : [];
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
    const payload = {
      vehicleId,
      serviceCode: service.serviceCode,
      description: service.description,
      startDate: service.startDate,
      endDate: service.endDate || '',
      cost: service.cost ?? 0,
      location: service.location || '',
      technician: service.technician || '',
      notes: service.notes || ''
    };
    const response = await api.post(
      `/api/vehicles/${encodeURIComponent(vehicleId)}/services`,
      payload
    );
    return normalizeService(response.data);
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
    const payload = {
      vehicleId,
      serviceCode: updates.serviceCode,
      description: updates.description,
      startDate: updates.startDate,
      endDate: updates.endDate || '',
      cost: updates.cost ?? 0,
      location: updates.location || '',
      technician: updates.technician || '',
      notes: updates.notes || ''
    };
    const response = await api.put(
      `/api/vehicles/${encodeURIComponent(vehicleId)}/services/${encodeURIComponent(serviceId)}`,
      payload
    );
    return normalizeService(response.data);
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
      `/api/vehicles/${encodeURIComponent(vehicleId)}/services/${encodeURIComponent(serviceId)}`
    );
  } catch (error) {
    console.error('Error deleting service:', error);
    throw error;
  }
};


export const askAIAndSpeak = async (input, languageCode) => {
  if (!input) return '';

  let messages;
  if (Array.isArray(input)) {
    // Already formatted as conversation messages
    messages = input.filter(msg => msg.content && msg.content.trim());
  } else if (typeof input === 'string') {
    messages = [{ role: 'user', content: input }];
  } else if (typeof input === 'object' && input.content) {
    messages = [input];
  } else {
    return '';
  }

  try {
    const payload = { messages, ...(languageCode && { languageCode }) };
    const { data } = await api.post('/api/speech/ask_ai', payload);
    return data?.response || '';
  } catch (error) {
    console.error('AI request failed:', error);
    throw error;
  }
};


export const fetchSpeechToken = async () => {
  const { data } = await api.get('/api/speech/token');
  if (!data || typeof data !== 'object') throw new Error('Invalid token response');
  const { token, region } = data;
  if (!token || !region) throw new Error('Malformed token payload');
  return { token, region };
};

export const fetchSpeechIceToken = async () => {
  const { data } = await api.get('/api/speech/ice_token');
  if (!data || typeof data !== 'object') throw new Error('Invalid ICE token response');

  // CamelCase only (no fallbacks)
  const { urls, username, password } = data;

  if (!Array.isArray(urls) || urls.length === 0 || !username || !password) {
    throw new Error('Malformed ICE token payload');
  }

  return {
    iceServers: [
      {
        urls,
        username,
        credential: password
      }
    ]
  };
};