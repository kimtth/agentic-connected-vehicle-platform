/**
 * Centralized interval configuration for the Connected Vehicle Platform
 * All timing values are in milliseconds
 */

// Real-time status updates
export const STATUS_UPDATE_INTERVALS = {
  // Real-time subscription polling fallback
  // Used by: status.js (setupPolling function)
  REALTIME_POLLING: 30000, // Increased from 15s to 30s

  // Dashboard status refresh
  // Used by: Dashboard.js (main dashboard page)
  DASHBOARD_REFRESH: 45000, // Increased from 20s to 45s
  
  // Vehicle dashboard status check
  // Used by: VehicleDashboard.js
  VEHICLE_DASHBOARD_CHECK: 60000, // Increased from 30s to 60s
};

// Component refresh intervals
export const COMPONENT_INTERVALS = {
  // Notification log polling
  // Used by: NotificationLog.js
  NOTIFICATIONS_POLLING: 30000, // Increased from 10s to 30s
  
  // Command log polling
  // Used by: CommandLog.js
  COMMANDS_POLLING: 30000, // Increased from 10s to 30s
  
  // Simulator status check interval
  // Used by: SimulatorPanel.js
  SIMULATOR_STATUS_CHECK: 45000, // Increased from 30s to 45s
};

// API request timeouts and intervals
export const API_INTERVALS = {
  // Standard API request timeout
  // Used by: apiClient.js, vehicles.js, commands.js, status.js
  REQUEST_TIMEOUT: 30000, // 30 seconds for API requests
  
  // File upload timeout (longer for large files)
  // Used by: file upload components
  UPLOAD_TIMEOUT: 120000, // 2 minutes
  
  // Health check interval
  // Used by: health monitoring components
  HEALTH_CHECK_INTERVAL: 60000, // 1 minute
};

// Connection and retry configuration
export const CONNECTION_INTERVALS = {
  // Connection retry delay (exponential backoff base)
  // Used by: vehicles.js, status.js for retrying failed connections
  RETRY_DELAY_BASE: 3000, // Increased from 2s to 3s
  
  // Maximum retry attempts for API calls
  // Used by: vehicles.js, commands.js
  MAX_RETRY_ATTEMPTS: 2, // Reduced from 3 to 2
  
  // WebSocket reconnection delay
  // Used by: WebSocketClient.js, socket.js
  WEBSOCKET_RECONNECT_DELAY: 10000, // Increased from 5s to 10s
  
  // Auto-retry interval for offline mode
  // Used by: App.js for auto-retry when backend is down
  OFFLINE_MODE_RETRY: 30000, // Increased from 10s to 30s
};

// Add throttling configuration
export const THROTTLING_CONFIG = {
  // Minimum time between status API calls per vehicle
  STATUS_CALL_THROTTLE: 5000, // 5 seconds minimum between calls
  
  // Maximum concurrent status requests
  MAX_CONCURRENT_STATUS_REQUESTS: 3,
  
  // Debounce time for rapid status updates
  STATUS_UPDATE_DEBOUNCE: 1000, // 1 second debounce
};

// Export all intervals as a single object for easy import
export const INTERVALS = {
  ...STATUS_UPDATE_INTERVALS,
  ...COMPONENT_INTERVALS,
  ...API_INTERVALS,
  ...CONNECTION_INTERVALS,
  ...THROTTLING_CONFIG,
};

// Helper functions for common interval operations
export const createInterval = (callback, interval) => {
  return setInterval(callback, interval);
};

// Add throttling helper
export const createThrottledFunction = (fn, delay) => {
  let lastCall = 0;
  return (...args) => {
    const now = Date.now();
    if (now - lastCall >= delay) {
      lastCall = now;
      return fn(...args);
    }
  };
};

// Add vehicle-specific throttling
const vehicleStatusCalls = new Map();

export const createVehicleStatusThrottle = (vehicleId) => {
  if (!vehicleId) {
    console.warn('Vehicle ID is required for throttling');
    return false;
  }
  
  const key = `status_${vehicleId}`;
  const lastCall = vehicleStatusCalls.get(key) || 0;
  const now = Date.now();
  
  if (now - lastCall < THROTTLING_CONFIG.STATUS_CALL_THROTTLE) {
    return false; // Too soon, throttle this call
  }
  
  vehicleStatusCalls.set(key, now);
  return true; // Allow this call
};

// Cleanup function for throttling cache
export const clearThrottlingCache = () => {
  vehicleStatusCalls.clear();
};

// Get throttling status for debugging
export const getThrottlingStatus = (vehicleId) => {
  if (!vehicleId) return null;
  
  const key = `status_${vehicleId}`;
  const lastCall = vehicleStatusCalls.get(key) || 0;
  const now = Date.now();
  const timeSinceLastCall = now - lastCall;
  const throttleRemaining = Math.max(0, THROTTLING_CONFIG.STATUS_CALL_THROTTLE - timeSinceLastCall);
  
  return {
    lastCall: lastCall ? new Date(lastCall).toISOString() : null,
    timeSinceLastCall,
    throttleRemaining,
    canMakeCall: timeSinceLastCall >= THROTTLING_CONFIG.STATUS_CALL_THROTTLE
  };
};
