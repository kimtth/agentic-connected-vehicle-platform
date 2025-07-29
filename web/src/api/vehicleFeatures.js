import { api } from './apiClient';
import { INTERVALS } from '../config/intervals';

// Vehicle Features API
export const controlLights = async (vehicleId, lightType, action) => {
  try {
    const response = await api.post(
      `/api/vehicles/${vehicleId}/features/lights`,
      { light_type: lightType, action }
    );
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to control lights');
  }
};

export const controlClimate = async (vehicleId, temperature, action = 'set_temperature', auto = true) => {
  try {
    const response = await api.post(
      `/api/vehicles/${vehicleId}/features/climate`,
      { temperature, action, auto }
    );
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to control climate');
  }
};

export const controlWindows = async (vehicleId, action, windows = 'all') => {
  try {
    const response = await api.post(
      `/api/vehicles/${vehicleId}/features/windows`,
      { action, windows }
    );
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to control windows');
  }
};

export const getFeatureStatus = async (vehicleId) => {
  try {
    const response = await api.get(
      `/api/vehicles/${vehicleId}/features/status`
    );
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to get feature status');
  }
};

// Remote Access API - Updated to match backend routes
export const controlDoors = async (vehicleId, action) => {
  try {
    const response = await api.post(
      `/api/vehicles/${vehicleId}/remote-access/doors`,
      { action }
    );
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to control doors');
  }
};

export const controlEngine = async (vehicleId, action) => {
  try {
    const response = await api.post(
      `/api/vehicles/${vehicleId}/remote-access/engine`,
      { action }
    );
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to control engine');
  }
};

export const locateVehicle = async (vehicleId) => {
  try {
    const response = await api.post(
      `/api/vehicles/${vehicleId}/remote-access/locate`
    );
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to locate vehicle');
  }
};

// Emergency & Safety API - Updated to match backend routes
export const emergencyCall = async (vehicleId, emergencyType = 'general') => {
  try {
    const response = await api.post(
      `/api/vehicles/${vehicleId}/emergency/call`,
      { emergency_type: emergencyType }
    );
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to initiate emergency call');
  }
};

export const reportCollision = async (vehicleId, severity = 'unknown', location = null) => {
  try {
    const response = await api.post(
      `/api/vehicles/${vehicleId}/emergency/collision`,
      { severity, location }
    );
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to report collision');
  }
};

export const reportTheft = async (vehicleId, description = null, lastSeenLocation = null) => {
  try {
    const response = await api.post(
      `/api/vehicles/${vehicleId}/emergency/theft`,
      { description, last_seen_location: lastSeenLocation }
    );
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to report theft');
  }
};

export const activateSOS = async (vehicleId) => {
  try {
    const response = await api.post(
      `/api/vehicles/${vehicleId}/emergency/sos`
    );
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Failed to activate SOS');
  }
};
