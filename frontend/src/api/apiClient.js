/**
 * Centralized API client for the Connected Vehicle Platform
 */

import axios from 'axios';

// Base configuration for API URL
export const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

/**
 * Create a configured axios instance
 */
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  }
});

/**
 * Add request and response interceptors if needed
 */
api.interceptors.request.use(
  config => {
    // You can add auth headers or other request processing here
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  response => {
    return response;
  },
  error => {
    console.error('API error:', error);
    return Promise.reject(error);
  }
);
