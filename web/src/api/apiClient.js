/**
 * Centralized API client for the Connected Vehicle Platform
 */

import axios from 'axios';
import { createRetryInterceptor } from './config';
import { msalInstance, acquireApiToken, getAuthorizationHeader } from '../auth/msalConfig'; // ensure single shared instance

// Support both env var names for base URL
// Prefer explicit env; otherwise default to backend (avoid relying on a proxy that may not exist)
const explicitBase =
  process.env.NODE_ENV === 'development'
    ? process.env.REACT_APP_API_DEV_BASE_URL: '';

function normalizeBase(url) {
  return url ? url.replace(/\/+$/, '') : url;
}

const baseURL = normalizeBase(
  explicitBase ||
    (process.env.NODE_ENV === 'development'
      ? 'http://localhost:8000'
      : 'http://localhost:8000')
);

// Create axios instance
export const api = axios.create({
  baseURL,
  timeout: 30000, // 30 seconds timeout for regular API requests
  headers: {
    'Content-Type': 'application/json',
  },
});

// Create a separate axios instance for agent operations with longer timeout
export const agentClient = axios.create({
  baseURL,
  timeout: 180000, // 180 seconds timeout for agent operations
  headers: {
    'Content-Type': 'application/json',
  },
});

// Helper to create a correlation/request id
function createRequestId() {
  try {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  } catch {}
  return 'req-' + Math.random().toString(36).slice(2);
}

/**
 * Add request and response interceptors if needed
 */
// Authorization + correlation id interceptor (silent token injection)
api.interceptors.request.use(async (config) => {
  // Correlation ID
  if (!config.headers['X-Client-Request-Id']) {
    config.headers['X-Client-Request-Id'] = createRequestId();
  }
  // Identify client for backend auditing
  if (!config.headers['X-Client-App']) {
    config.headers['X-Client-App'] = 'web';
  }
  
  try {
    const accounts = msalInstance.getAllAccounts();
    if (accounts.length) {
      const acct = accounts[0];
      const userName = acct.username;

      // Prevent API calls if user_name is null or empty
      if (!userName || userName.trim() === '') {
        const error = new Error('User not authenticated - username is required');
        error.code = 'USER_NOT_AUTHENTICATED';
        throw error;
      }

      if (!config.headers['X-User-Name']) {
        config.headers['X-User-Name'] = userName;
      }
      if (!config.headers.Authorization) {
        const token = await acquireApiToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        } else if (process.env.NODE_ENV === 'development') {
          console.debug('[apiClient] Token acquisition returned null (no Authorization header set).');
        }
      }
    } else {
      // No accounts available - user not logged in
      const error = new Error('User not authenticated - no valid account found');
      error.code = 'USER_NOT_AUTHENTICATED';
      throw error;
    }
  } catch (e) {
    if (e.code === 'USER_NOT_AUTHENTICATED') {
      throw e; // Re-throw authentication errors
    }
    if (process.env.NODE_ENV === 'development') {
      console.debug('[apiClient] MSAL not ready, sending request without token.', e?.message);
    }
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

// Agent client correlation id (keep separate to avoid duplication)
agentClient.interceptors.request.use(async (config) => {
  if (!config.headers['X-Client-Request-Id']) {
    config.headers['X-Client-Request-Id'] = createRequestId();
  }
  // Identify client for backend auditing
  if (!config.headers['X-Client-App']) {
    config.headers['X-Client-App'] = 'web-agent';
  }
  
  try {
    const accounts = msalInstance.getAllAccounts();
    if (accounts.length) {
      const acct = accounts[0];
      const userName = acct.username;

      // Prevent API calls if user_name is null or empty
      if (!userName || userName.trim() === '') {
        const error = new Error('User not authenticated - username is required for agent operations');
        error.code = 'USER_NOT_AUTHENTICATED';
        throw error;
      }

      if (!config.headers['X-User-Id']) {
        config.headers['X-User-Id'] = acct.homeAccountId || acct.localAccountId || userName;
      }
      if (!config.headers['X-User-Name']) {
        config.headers['X-User-Name'] = userName;
      }
      if (!config.headers.Authorization) {
        const token = await acquireApiToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        } else if (process.env.NODE_ENV === 'development') {
          console.debug('[agentClient] No token acquired (Authorization header not set).');
        }
      }
    } else {
      // No accounts available - user not logged in
      const error = new Error('User not authenticated - no valid account found for agent operations');
      error.code = 'USER_NOT_AUTHENTICATED';
      throw error;
    }
  } catch (e) {
    if (e.code === 'USER_NOT_AUTHENTICATED') {
      throw e; // Re-throw authentication errors
    }
    // For other errors, continue without auth headers in development
  }
  
  if (process.env.NODE_ENV === 'development') {
    console.log('🚀 Agent API Request:', {
      url: config.url,
      method: config.method,
      data: config.data,
      timeout: config.timeout
    });
  }
  return config;
}, (error) => {
  console.error('❌ Agent API Request Error:', error);
  return Promise.reject(error);
});

// Add retry interceptor for automatic endpoint correction
createRetryInterceptor(api);

// Response interceptor for main API
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API error:', error);
    
    // Handle authentication errors
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      console.error('Authentication required - user must be logged in');
      error.message = 'Please log in to access this feature';
      return Promise.reject(error);
    }
    
    // Handle CORS errors
    if (error.code === 'ERR_NETWORK' && error.message.includes('CORS')) {
      console.error('CORS error - backend may not be configured for cross-origin requests');
      error.message = 'Unable to connect to server. Please ensure the backend is running and configured for CORS.';
      error.isCorsError = true;
      return Promise.reject(error);
    }
    
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
        console.error('Internal server error - possible backend endpoint issue');
        error.message = data?.detail || 'Server error - the backend may have an issue with this endpoint';
      } else if (status === 502) {
        console.error('Bad Gateway - backend server may be down');
        error.message = 'Backend service unavailable - please try again later';
      } else if (status === 503) {
        console.error('Service Unavailable - backend may be restarting');
        error.message = 'Service temporarily unavailable - please try again in a moment';
      } else if (status >= 400 && status < 500) {
        console.error('Client error:', data);
        error.message = data?.detail || `Client error: ${status}`;
      } else if (status >= 500) {
        console.error('Server error:', data);
        error.message = data?.detail || 'Server error - please try again later';
      }
    } else if (error.request) {
      // Network error - could be CORS
      console.error('Network error - unable to reach server (possible CORS issue)');
      error.message = 'Unable to connect to server - please check your connection and ensure backend is running';
      error.isNetworkError = true;
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
      console.error('🌐 Network error - unable to reach the server (possible CORS issue)');
      error.isNetworkError = true;
      error.userMessage = 'Unable to connect to the server. Please ensure the backend is running on port 8000 and configured for CORS.';
    }
    
    if (process.env.NODE_ENV === 'development') {
      console.error('❌ Agent API Response Error:', {
        url: error.config?.url,
        message: error.message,
        code: error.code,
        response: error.response?.data,
        isCorsError: error.message?.includes('CORS')
      });
    }
    
    return Promise.reject(error);
  }
);

// Agent endpoint (fallback removed)
const AGENT_AGENT_PATH = process.env.REACT_APP_AGENT_ENDPOINT || '/api/agent/ask';

/**
 * Agent-specific API function
 * Ask an agent to process a query with endpoint fallback
 * @param {Object} payload - The request payload
 * @returns {Promise} The agent response
 */
export const askAgent = async (payload) => {
  // Add request validation
  if (!payload || typeof payload !== 'object') {
    throw new Error('Invalid payload - request data is required');
  }

  // Try primary endpoint first
  try {
    const res = await agentClient.post(AGENT_AGENT_PATH, payload);
    
    // Validate response
    if (!res || !res.data) {
      throw new Error('Invalid response from server - no data received');
    }
    
    return res.data;
  } catch (err) {
    const status = err?.response?.status;

    // Decorate error for UI
    if (err.code === 'ECONNABORTED' && err.message.includes('timeout')) {
      err.isTimeout = true;
      err.userMessage = 'The request is taking longer than expected. The server might be processing a complex operation. Please try again.';
    } else if (err.code === 'ERR_NETWORK') {
      err.isNetworkError = true;
      err.userMessage = 'Unable to connect to the server. Please check if the backend service is running.';
    } else if (status >= 500) {
      err.userMessage = 'The server encountered an error. Please try again later.';
    }
    throw err;
  }
};

/**
 * apiFetch wraps window.fetch adding Authorization header (if available).
 * Usage: const data = await apiFetch('/api/vehicles').then(r => r.json());
 */
export async function apiFetch(input, init = {}) {
  const auth = await getAuthorizationHeader();
  const headers = {
    ...(init.headers || {}),
    ...(auth || {}),
    'Content-Type': init.body && !(init.headers && init.headers['Content-Type']) ? 'application/json' : (init.headers || {})['Content-Type']
  };
  return fetch(input, { ...init, headers });
}

/**
 * Convenience JSON helpers
 */
export async function getJson(url) {
  const r = await apiFetch(url);
  if (!r.ok) throw new Error(`GET ${url} failed: ${r.status}`);
  return r.json();
}

export async function postJson(url, body) {
  const r = await apiFetch(url, {
    method: 'POST',
    body: JSON.stringify(body)
  });
  if (!r.ok) throw new Error(`POST ${url} failed: ${r.status}`);
  return r.json();
}

export default api;