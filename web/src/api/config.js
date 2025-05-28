/**
 * API configuration
 */

// Determine environment
const isProduction = process.env.NODE_ENV === 'production';

// Base URL for all API requests - environment-dependent
export let API_BASE_URL = isProduction
  ? `${window.location.origin}/api` // Use current origin in production
  : 'http://localhost:8000/api';    // Development endpoint

// Allow override via environment variable if available
// if (process.env.REACT_APP_API_BASE_URL) {
//     API_BASE_URL = process.env.REACT_APP_API_BASE_URL;
// }

console.log(`Using API endpoint: ${API_BASE_URL} (${isProduction ? 'production' : 'development'})`);

// Default request timeout in milliseconds
export const REQUEST_TIMEOUT = 30000;

// Whether to include credentials in requests
export const INCLUDE_CREDENTIALS = false;
