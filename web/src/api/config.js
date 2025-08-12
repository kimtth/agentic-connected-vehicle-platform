/**
 * Minimal API configuration for hackathon use
 */

// Base URL for all API requests
export const API_BASE_URL =
  process.env.REACT_APP_API_URL ||
  (process.env.NODE_ENV === 'production'
    ? `${window.location.origin}`
    : 'http://localhost:8000');

// Simple timeout and headers
export const REQUEST_TIMEOUT = 10000; // 10s
export const INCLUDE_CREDENTIALS = false;
export const DEFAULT_HEADERS = {
  'Content-Type': 'application/json',
  'Accept': 'application/json',
};

// No-op error handler/interceptor/helpers to keep API surface stable
export const handleApiError = (error) => error;

export const createRetryInterceptor = (axiosInstance) => axiosInstance;

export const DEV_HELPERS = {
  logApiCall: () => {},
  validateEndpoint: () => true,
};

export function getCurrentEnvConfig() {
  return {
    API_BASE_URL,
    DEFAULT_HEADERS,
    INCLUDE_CREDENTIALS,
    REQUEST_TIMEOUT,
    DEV_HELPERS,
    createRetryInterceptor,
    handleApiError,
  };
}