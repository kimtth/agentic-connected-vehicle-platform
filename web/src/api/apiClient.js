/**
 * Centralized API client for the Connected Vehicle Platform
 */

import axios from 'axios';
import { INTERVALS } from '../config/intervals';
import { createRetryInterceptor, DEV_HELPERS, getCurrentEnvConfig } from './config';

// Get base URL from environment variable or use default
const baseURL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Create axios instance
export const api = axios.create({
  baseURL,
  timeout: INTERVALS.REQUEST_TIMEOUT, // Use centralized timeout configuration
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Add request and response interceptors if needed
 */
// Request interceptor
api.interceptors.request.use(
  (config) => {
    DEV_HELPERS.logApiCall(config.method, config.url, config.data);
    
    // Only validate endpoint in development and only log warning if it's truly unknown
    const currentEnvConfig = getCurrentEnvConfig();
    if (currentEnvConfig.enableDebugLogs) {
      const isValid = DEV_HELPERS.validateEndpoint(config.url);
      // Only show validation details for completely unknown patterns
      if (!isValid && !config.url.includes('vehicles/') && !config.url.includes('notifications')) {
        console.info('🔍 Endpoint validation details:', {
          url: config.url,
          method: config.method,
          baseURL: config.baseURL
        });
      }
    }
    
    return config;
  },
  (error) => {
    console.error('Request error:', error);
    return Promise.reject(error);
  }
);

// Add retry interceptor for automatic endpoint correction
createRetryInterceptor(api);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API error:', error);
    
    // Handle specific error cases
    if (error.code === 'ECONNABORTED') {
      console.error('Request timeout - the server took too long to respond');
      error.message = 'Request timeout - please try again';
    } else if (error.response) {
      // Server responded with error status
      const status = error.response.status;
      const data = error.response.data;
      
      if (status === 404) {
        console.error('Resource not found');
        error.message = data?.detail || 'Resource not found';
      } else if (status === 405) {
        console.error('Method not allowed - check API endpoint configuration');
        error.message = 'Operation not supported by the server';
      } else if (status === 500) {
        console.error('Internal server error');
        error.message = data?.detail || 'Server error - please try again later';
      } else if (status >= 400 && status < 500) {
        console.error('Client error:', data);
        error.message = data?.detail || `Client error: ${status}`;
      } else if (status >= 500) {
        console.error('Server error:', data);
        error.message = data?.detail || 'Server error - please try again later';
      }
    } else if (error.request) {
      // Network error
      console.error('Network error - unable to reach server');
      error.message = 'Unable to connect to server - please check your connection';
    } else {
      // Other error
      console.error('Unexpected error:', error.message);
    }
    
    return Promise.reject(error);
  }
);

export default api;
