import { api, apiFetch } from './apiClient';
import { API_BASE_URL } from './config';
import { INTERVALS } from '../config/intervals';

/**
 * Retry mechanism for failed requests
 * @param {Function} fn - Function to retry
 * @param {number} retries - Number of retries
 * @param {number} delay - Delay between retries
 */
const retryRequest = async (fn, retries = 3, delay = 1000) => {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === retries - 1) throw error;
      if (error.name === 'AbortError') throw error; // Don't retry aborted requests
      if (error.code === 'USER_NOT_AUTHENTICATED') throw error; // Don't retry auth errors

      console.log(`Status API retry attempt ${i + 1}/${retries} after ${delay}ms`);
      const wait = delay;
      await new Promise(resolve => setTimeout(resolve, wait));
      delay *= 1.5; // Exponential backoff
    }
  }
}

// ---- Added: fetch throttling / caching state ----
const FETCH_STATUS_MIN_INTERVAL = 5000; // ms throttle to avoid background hammering
const statusFetchCache = new Map(); // vehicleId -> { data, ts }
const statusInFlight = new Map();   // vehicleId -> Promise

// ---- Added: shared stream manager (single EventSource per vehicle) ----
const activeStatusStreams = new Map();
/*
Structure:
activeStatusStreams.set(vehicleId, {
  eventSource,
  handlers: Set<{ onStatusUpdate, onError }>,
  refCount,
  started,
  connect()
})
*/

/**
 * Fetch the current vehicle status
 * @param {string} vehicleId 
 * @param {number} retries Number of retries if request fails (default: 2)
 * @returns {Promise<Object>} Vehicle status data
 */
export const fetchVehicleStatus = async (vehicleId, retries = 2, options = {}) => {
  // options: { force?: boolean, signal?: AbortSignal }
  const { force = false, signal } = options || {};
  const now = Date.now();
  const cached = statusFetchCache.get(vehicleId);

  // Skip network if streaming already active and we have any cache
  const streamRec = activeStatusStreams.get(vehicleId);
  if (!force && streamRec && streamRec.eventSource && cached) return cached.data;

  // Throttle if not forced and we have relatively fresh data
  if (!force && cached && (now - cached.ts) < FETCH_STATUS_MIN_INTERVAL) {
    return cached.data;
  }

  // Coalesce concurrent fetches
  if (!force && statusInFlight.has(vehicleId)) {
    return statusInFlight.get(vehicleId);
  }

  const fetchPromise = (async () => {
    try {
      return await retryRequest(async () => {
        // Support abort via AbortController
        const controller = new AbortController();
        if (signal) {
          if (signal.aborted) {
            controller.abort();
          } else {
            signal.addEventListener('abort', () => controller.abort(), { once: true });
          }
        }
        const response = await api.get(`/api/vehicles/${encodeURIComponent(vehicleId)}/status`, {
          signal: controller.signal
        });
        if (response.data) {
          statusFetchCache.set(vehicleId, { data: response.data, ts: Date.now() });
          return response.data;
        }
        throw new Error("No status data returned");
      }, retries);
    } finally {
      statusInFlight.delete(vehicleId);
    }
  })();

  statusInFlight.set(vehicleId, fetchPromise);
  return fetchPromise;
};

/**
 * Stream vehicle status updates
 * @param {string} vehicleId 
 * @param {function} onStatusUpdate Callback for status updates
 * @param {function} onError Callback for errors
 * @returns {function} Cleanup function to stop streaming
 */
export const streamVehicleStatus = async (vehicleId, onStatusUpdate, onError) => {
  // Defensive: manage a single EventSource per vehicle with ref counting
  let record = activeStatusStreams.get(vehicleId);

  if (!record) {
    record = {
      eventSource: null,
      handlers: new Set(),
      refCount: 0,
      started: false,
      controller: null,
      reader: null,
      connect() {
        if (record.started || (typeof document !== 'undefined' && document.hidden)) return;
        record.started = true;
        const url = `${API_BASE_URL}/api/vehicle/${encodeURIComponent(vehicleId)}/status/stream`;
        (async () => {
          record.controller = new AbortController();
          try {
            const res = await apiFetch(url, {
              method: 'GET',
              headers: { Accept: 'text/event-stream' },
              signal: record.controller.signal
            });
            if (!res.ok || !res.body) {
              const err = new Error(`Status stream failed (${res.status})`);
              err.code = 'STREAM_ERROR';
              record.handlers.forEach(h => h.onError?.(err));
              record.started = false;
              return;
            }
            const reader = res.body.getReader();
            record.reader = reader;
            const decoder = new TextDecoder('utf-8');
            let buffer = '';
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              buffer += decoder.decode(value, { stream: true });
              let idx;
              while ((idx = buffer.indexOf('\n\n')) >= 0) {
                const raw = buffer.slice(0, idx).trim();
                buffer = buffer.slice(idx + 2);
                if (!raw || !raw.startsWith('data:')) continue;
                const payload = raw.replace(/^data:\s*/, '');
                try {
                  const json = JSON.parse(payload);
                  if (json?.error) {
                    const err = new Error(json.error);
                    err.code = 'STREAM_ERROR';
                    record.handlers.forEach(h => h.onError?.(err));
                  } else {
                    // cache latest
                    try { statusFetchCache.set(vehicleId, { data: json, ts: Date.now() }); } catch { }
                    record.handlers.forEach(h => h.onStatusUpdate?.(json));
                  }
                } catch (e) {
                  record.handlers.forEach(h => h.onError?.(e));
                }
              }
            }
          } catch (e) {
            if (e.name !== 'AbortError') {
              record.handlers.forEach(h => h.onError?.(e));
            }
          } finally {
            record.started = false;
          }
        })();
      }
    };
    activeStatusStreams.set(vehicleId, record);
    // Visibility handling
    if (typeof document !== 'undefined') {
      const visibilityHandler = () => {
        if (!activeStatusStreams.has(vehicleId)) {
          document.removeEventListener('visibilitychange', visibilityHandler);
          return;
        }
        if (!document.hidden && !record.started) {
          record.connect();
        } else if (document.hidden && record.controller) {
          try { record.controller.abort(); } catch { }
        }
      };
      document.addEventListener('visibilitychange', visibilityHandler);
      visibilityHandler();
    } else {
      record.connect();
    }
  }

  // Register handlers
  const handlerObj = { onStatusUpdate, onError };
  record.handlers.add(handlerObj);
  record.refCount += 1;
  record.connect();

  let cleaned = false;
  const cleanup = () => {
    if (cleaned) return;
    cleaned = true;
    if (!activeStatusStreams.has(vehicleId)) return;
    record.handlers.delete(handlerObj);
    record.refCount -= 1;
    if (record.refCount <= 0) {
      try { record.controller && record.controller.abort(); } catch { }
      activeStatusStreams.delete(vehicleId);
    }
  };
  return cleanup;
};

/**
 * Update vehicle status
 * @param {string} vehicleId 
 * @param {Object} statusData 
 * @returns {Promise<Object>} Updated status
 */
export const updateVehicleStatus = async (vehicleId, statusData) => {
  try {
    return await retryRequest(async () => {
      const response = await api.put(`/api/vehicle/${encodeURIComponent(vehicleId)}/status`, statusData);
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      console.error('Authentication required: User must be logged in to update vehicle status');
      throw new Error('Please log in to update vehicle status');
    }
    console.error(`Error updating vehicle status for ${vehicleId}:`, error);
    throw error;
  }
};

/**
 * Partially update vehicle status
 * @param {string} vehicleId 
 * @param {Object} statusUpdates 
 * @returns {Promise<Object>} Updated status
 */
export const patchVehicleStatus = async (vehicleId, statusUpdates) => {
  try {
    return await retryRequest(async () => {
      const response = await api.patch(`/api/vehicle/${encodeURIComponent(vehicleId)}/status`, statusUpdates);
      return response.data;
    });
  } catch (error) {
    if (error.code === 'USER_NOT_AUTHENTICATED') {
      console.error('Authentication required: User must be logged in to update vehicle status');
      throw new Error('Please log in to update vehicle status');
    }
    console.error(`Error patching vehicle status for ${vehicleId}:`, error);
    throw error;
  }
};

/**
 * Subscribe to vehicle status updates (wrapper for streamVehicleStatus)
 * @param {string} vehicleId 
 * @param {function} onStatusUpdate Callback for status updates
 * @param {function} onError Callback for errors
 * @returns {function} Cleanup function to stop streaming
 */
export const subscribeToVehicleStatus = (vehicleId, onStatusUpdate, onError) => {
  return streamVehicleStatus(vehicleId, onStatusUpdate, onError);
};

// ---- Added global unsubscribe helper ----
export const unsubscribeAllVehicleStatusStreams = () => {
  activeStatusStreams.forEach(rec => {
    try { rec.eventSource && rec.eventSource.close(); } catch { }
  });
  activeStatusStreams.clear();
};

/**
 * Update climate settings for a vehicle
 * @param {string} vehicleId 
 * @param {Object} climateSettings - Climate settings to update
 * @returns {Promise<Object>} Updated status
 */
export const updateClimateSettings = async (vehicleId, climateSettings) => {
  try {
    const statusUpdate = {
      climateSettings: {
        temperature: climateSettings.temperature ?? 22,
        fanSpeed: climateSettings.fanSpeed ?? 0,
        mode: climateSettings.mode ?? 'off',
        ...climateSettings
      },
      timestamp: new Date().toISOString()
    };
    const response = await patchVehicleStatus(vehicleId, statusUpdate);
    return response;
  } catch (error) {
    console.error(`Error updating climate settings for ${vehicleId}:`, error);
    throw error;
  }
};

/**
 * Setup polling for vehicle status (fallback when streaming is not available)
 * @param {string} vehicleId 
 * @param {function} onStatusUpdate Callback for status updates
 * @param {function} onError Callback for errors
 * @param {number} interval Polling interval in milliseconds
 * @returns {function} Cleanup function to stop polling
 */
export const setupPolling = (vehicleId, onStatusUpdate, onError, interval = INTERVALS.REALTIME_POLLING) => {
  let isActive = true;

  const poll = async () => {
    if (!isActive) return;

    try {
      const status = await fetchVehicleStatus(vehicleId);
      if (isActive) {
        onStatusUpdate(status);
      }
    } catch (error) {
      if (isActive) {
        console.error('Polling error:', error);
        onError(error);
      }
    }

    if (isActive) {
      setTimeout(poll, interval);
    }
  };

  // Start polling
  poll();

  // Return cleanup function
  return () => {
    isActive = false;
  };
};