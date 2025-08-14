/**
 * Centralized API client for the Connected Vehicle Platform
 */

import axios from 'axios';
import { INTERVALS } from '../config/intervals';
import { createRetryInterceptor, DEV_HELPERS, getCurrentEnvConfig } from './config';
import { msalInstance, acquireApiToken } from '../auth/msalConfig'; // ensure path inside src

// Support both env var names for base URL
const baseURL = process.env.REACT_APP_API_BASE_URL || process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance
export const api = axios.create({
  baseURL,
  timeout: INTERVALS.REQUEST_TIMEOUT, // Use centralized timeout configuration
  headers: {
    'Content-Type': 'application/json',
  },
});

// Create a separate axios instance for agent operations with longer timeout
export const agentClient = axios.create({
  baseURL,
  timeout: 60000, // 60 seconds timeout for agent operations
  headers: {
    'Content-Type': 'application/json',
  },
});

/**
 * Add request and response interceptors if needed
 */
// Authorization interceptor (silent token injection)
api.interceptors.request.use(async (config) => {
  try {
    // Simple readiness check – if internal cache not ready getAllAccounts may throw
    const accounts = msalInstance.getAllAccounts();
    if (accounts.length && !config.headers.Authorization) {
      const token = await acquireApiToken();
      if (token) config.headers.Authorization = `Bearer ${token}`;
    }
  } catch {
    // MSAL not initialized yet – proceed without token
  }
  return config;
}, (error) => {
  console.error('Authorization error:', error);
  return Promise.reject(error);
});

// Request interceptor for main API
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

// Request interceptor for agent client
agentClient.interceptors.request.use(
  (config) => {
    if (process.env.NODE_ENV === 'development') {
      console.log('🚀 Agent API Request:', {
        url: config.url,
        method: config.method,
        data: config.data,
        timeout: config.timeout
      });
    }
    return config;
  },
  (error) => {
    console.error('❌ Agent API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add retry interceptor for automatic endpoint correction
createRetryInterceptor(api);

// Response interceptor for main API
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

// Response interceptor for agent client with enhanced error handling
agentClient.interceptors.response.use(
  (response) => {
    if (process.env.NODE_ENV === 'development') {
      console.log('✅ Agent API Response:', {
        url: response.config.url,
        status: response.status,
        data: response.data
      });
    }
    return response;
  },
  (error) => {
    // Enhanced error handling for agent operations
    if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
      console.error('⏱️ Request timeout - the operation took too long');
      error.isTimeout = true;
    } else if (error.code === 'ERR_NETWORK') {
      console.error('🌐 Network error - unable to reach the server');
      error.isNetworkError = true;
    }
    
    if (process.env.NODE_ENV === 'development') {
      console.error('❌ Agent API Response Error:', {
        url: error.config?.url,
        message: error.message,
        code: error.code,
        response: error.response?.data
      });
    }
    
    return Promise.reject(error);
  }
);

// Agent endpoint primary + fallback (configurable)
const PRIMARY_AGENT_PATH = process.env.REACT_APP_AGENT_ENDPOINT || '/agent/ask';
const FALLBACK_AGENT_PATH = process.env.REACT_APP_AGENT_ENDPOINT_FALLBACK || '/api/agent/ask';

/**
 * Agent-specific API function
 * Ask an agent to process a query with endpoint fallback
 * @param {Object} payload - The request payload
 * @returns {Promise} The agent response
 */
export const askAgent = async (payload) => {
  // Try primary endpoint first
  try {
    const res = await agentClient.post(PRIMARY_AGENT_PATH, payload);
    return res.data;
  } catch (err) {
    const status = err?.response?.status;
    // Fallback on 404/405 typical "not found" or "method not allowed"
    if (status === 404 || status === 405) {
      if (process.env.NODE_ENV === 'development') {
        console.warn(`Primary endpoint ${PRIMARY_AGENT_PATH} failed with ${status}, trying fallback ${FALLBACK_AGENT_PATH}`);
      }
      try {
        const res = await agentClient.post(FALLBACK_AGENT_PATH, payload);
        return res.data;
      } catch (fallbackErr) {
        // Decorate error for UI
        if (fallbackErr.code === 'ECONNABORTED' && fallbackErr.message.includes('timeout')) {
          fallbackErr.isTimeout = true;
          fallbackErr.userMessage = 'The request is taking longer than expected. The server might be processing a complex operation. Please try again.';
        } else if (fallbackErr.code === 'ERR_NETWORK') {
          fallbackErr.isNetworkError = true;
          fallbackErr.userMessage = 'Unable to connect to the server. Please check if the backend service is running.';
        }
        throw fallbackErr;
      }
    }
    // Decorate error for UI
    if (err.code === 'ECONNABORTED' && err.message.includes('timeout')) {
      err.isTimeout = true;
      err.userMessage = 'The request is taking longer than expected. The server might be processing a complex operation. Please try again.';
    } else if (err.code === 'ERR_NETWORK') {
      err.isNetworkError = true;
      err.userMessage = 'Unable to connect to the server. Please check if the backend service is running.';
    }
    throw err;
  }
};

export default api;