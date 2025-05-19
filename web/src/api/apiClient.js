/**
 * Centralized API client for the Connected Vehicle Platform
 */

import axios from 'axios';
import { API_BASE_URL, REQUEST_TIMEOUT, INCLUDE_CREDENTIALS } from './config';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: REQUEST_TIMEOUT,
  withCredentials: INCLUDE_CREDENTIALS,
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
