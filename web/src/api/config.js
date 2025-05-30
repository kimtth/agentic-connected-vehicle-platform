/**
 * API configuration
 */

import { INTERVALS } from '../config/intervals';

// Determine environment
const isProduction = process.env.NODE_ENV === 'production';

// Base URL for all API requests - environment-dependent
export let API_BASE_URL = process.env.REACT_APP_API_URL || 
  (isProduction
    ? `${window.location.origin}` // Use current origin in production
    : 'http://localhost:8000');   // Development endpoint

console.log(`Using API endpoint: ${API_BASE_URL} (${isProduction ? 'production' : 'development'})`);

// Default request timeout in milliseconds - use centralized configuration
export const REQUEST_TIMEOUT = INTERVALS.REQUEST_TIMEOUT;

// Whether to include credentials in requests
export const INCLUDE_CREDENTIALS = false;

// Common headers for all requests
export const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
};

// Retry configuration
export const RETRY_CONFIG = {
  maxRetries: 3,
  retryDelay: 1000, // 1 second
  retryOnNetworkError: true,
  retryOnTimeout: true,
};

// Environment-specific configurations
export const ENV_CONFIG = {
  development: {
    enableDebugLogs: true,
    enableMockData: false,
    strictErrorHandling: false,
  },
  production: {
    enableDebugLogs: false,
    enableMockData: false,
    strictErrorHandling: true,
  },
};

// Get current environment configuration
export const getCurrentEnvConfig = () => {
  return ENV_CONFIG[isProduction ? 'production' : 'development'];
};

// Validate API configuration
export const validateConfig = () => {
  if (!API_BASE_URL) {
    throw new Error('API_BASE_URL is not configured');
  }
  
  if (!REQUEST_TIMEOUT || REQUEST_TIMEOUT < 1000) {
    console.warn('REQUEST_TIMEOUT should be at least 1000ms');
  }
  
  return true;
};

// Initialize configuration validation
try {
  validateConfig();
} catch (error) {
  console.error('API configuration validation failed:', error);
}

// Enhanced error handling utilities
export const API_ERROR_TYPES = {
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT_ERROR: 'TIMEOUT_ERROR',
  NOT_FOUND: 'NOT_FOUND',
  METHOD_NOT_ALLOWED: 'METHOD_NOT_ALLOWED',
  SERVER_ERROR: 'SERVER_ERROR',
  VALIDATION_ERROR: 'VALIDATION_ERROR',
};

// Common API endpoint mappings (to handle frontend/backend mismatches)
export const ENDPOINT_MAPPINGS = {
  // Handle plural vs singular vehicle endpoints
  'vehicles': {
    fallbacks: ['vehicle'], // Try singular if plural fails
    operations: {
      'services': '/vehicle/{vehicleId}/services', // Backend uses singular
      'status': '/vehicles/{vehicleId}/status',    // Backend uses plural
    }
  },
  // Handle agent endpoint mappings
  'agent': {
    endpoints: [
      '/agent/ask',
      '/agent/remote-access',
      '/agent/safety-emergency',
      '/agent/charging-energy',
      '/agent/information-services',
      '/agent/feature-control',
      '/agent/diagnostics-battery',
      '/agent/alerts-notifications'
    ]
  }
};

// Enhanced error handler with automatic endpoint correction
export const handleApiError = (error, originalUrl) => {
  const currentEnvConfig = getCurrentEnvConfig();
  
  if (currentEnvConfig.enableDebugLogs) {
    console.group('🔍 API Error Debug Information');
    console.log('Original URL:', originalUrl);
    console.log('Error Type:', error.response?.status || error.code);
    console.log('Error Message:', error.message);
    console.log('Full Error:', error);
    console.groupEnd();
  }

  // Check if this is a 404 error that might be due to endpoint mismatch
  if (error.response?.status === 404 && originalUrl) {
    const suggestion = suggestEndpointCorrection(originalUrl);
    if (suggestion) {
      console.warn(`🔧 Endpoint suggestion: Try "${suggestion}" instead of "${originalUrl}"`);
      return {
        ...error,
        suggestion,
        correctionAvailable: true
      };
    }
  }

  return error;
};

// Suggest correct endpoints based on common mismatches
const suggestEndpointCorrection = (url) => {
  // Handle vehicles vs vehicle mismatch
  if (url.includes('/api/vehicles/') && url.includes('/services')) {
    return url.replace('/api/vehicles/', '/api/vehicle/');
  }
  
  if (url.includes('/api/vehicle/') && url.includes('/status')) {
    return url.replace('/api/vehicle/', '/api/vehicles/');
  }
  
  return null;
};

// Automatic endpoint retry with corrections
export const createRetryInterceptor = (axiosInstance) => {
  axiosInstance.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config;
      
      // Don't retry if we've already retried
      if (originalRequest._retry) {
        return Promise.reject(handleApiError(error, originalRequest.url));
      }
      
      // Check if this is a 404 that we can potentially fix
      if (error.response?.status === 404) {
        const suggestion = suggestEndpointCorrection(originalRequest.url);
        
        if (suggestion && getCurrentEnvConfig().enableDebugLogs) {
          console.log(`🔄 Auto-retrying with corrected endpoint: ${suggestion}`);
          
          // Mark as retried and update URL
          originalRequest._retry = true;
          originalRequest.url = suggestion;
          
          // Retry with corrected URL
          try {
            return axiosInstance(originalRequest);
          } catch (retryError) {
            console.warn('🚫 Retry with corrected endpoint also failed:', retryError.message);
          }
        }
      }
      
      return Promise.reject(handleApiError(error, originalRequest.url));
    }
  );
};

// Development mode helpers
export const DEV_HELPERS = {
  // Log all API calls in development
  logApiCall: (method, url, data) => {
    if (getCurrentEnvConfig().enableDebugLogs) {
      console.log(`📡 API ${method.toUpperCase()}: ${url}`, data ? { data } : '');
    }
  },
  
  // Validate endpoint exists before making call
  validateEndpoint: (url) => {
    const knownEndpoints = [
      '/api/vehicles',
      '/api/vehicles/{vehicleId}/status',
      '/api/vehicle/{vehicleId}/services',
      '/api/vehicle/{vehicleId}/service',
      '/api/vehicle/{vehicleId}/status',
      '/api/command',
      '/api/commands',
      '/api/notifications',
      '/notifications',
      '/vehicles/{vehicleId}/status',
      '/vehicle/{vehicleId}/services',
      '/vehicle/{vehicleId}/service',
      '/vehicle/{vehicleId}/status',
      '/vehicles/{vehicleId}/features/lights',
      '/vehicles/{vehicleId}/features/climate',
      '/vehicles/{vehicleId}/features/windows',
      '/vehicles/{vehicleId}/features/status',
      '/vehicles/{vehicleId}/remote-access/doors',
      '/vehicles/{vehicleId}/remote-access/engine',
      '/vehicles/{vehicleId}/remote-access/locate',
      '/vehicles/{vehicleId}/emergency/call',
      '/vehicles/{vehicleId}/emergency/collision',
      '/vehicles/{vehicleId}/emergency/theft',
      '/vehicles/{vehicleId}/emergency/sos',
      '/simulator/vehicles/{vehicleId}/status',
      // Agent endpoints
      '/agent/ask',
      '/agent/remote-access',
      '/agent/safety-emergency',
      '/agent/charging-energy',
      '/agent/information-services',
      '/agent/feature-control',
      '/agent/diagnostics-battery',
      '/agent/alerts-notifications',
      '/analyze/vehicle-data',
      '/recommend/services',
    ];
    
    // Remove query parameters for validation
    const urlWithoutQuery = url.split('?')[0];
    
    const isKnown = knownEndpoints.some(endpoint => {
      // Replace {vehicleId} with a regex pattern that matches UUIDs or any vehicle ID
      const pattern = endpoint.replace('{vehicleId}', '[a-fA-F0-9-]+');
      const regex = new RegExp(`^${pattern}$`);
      return regex.test(urlWithoutQuery);
    });
    
    if (!isKnown && getCurrentEnvConfig().enableDebugLogs) {
      console.warn(`⚠️ Unknown endpoint pattern: ${url}`);
      console.info(`💡 If this is a valid endpoint, add it to the knownEndpoints list in config.js`);
      console.info(`🔍 Checking agent endpoints: ${ENDPOINT_MAPPINGS.agent.endpoints.join(', ')}`);
    }
    
    return isKnown;
  }
};
