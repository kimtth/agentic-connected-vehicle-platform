import { api, apiFetch } from './apiClient';

/**
 * Fetch notifications from the backend API
 * @param {string} vehicleId - Optional vehicle ID to filter notifications
 * @returns {Promise<Array>} Array of notification objects
 */
export const fetchNotifications = async (vehicleId) => {
  try {
    const url = vehicleId
      ? `/api/notifications?vehicleId=${encodeURIComponent(vehicleId)}`
      : '/api/notifications';
    const response = await api.get(url);
    return response.data;
  } catch (error) {
    console.error('Error fetching notifications:', error);
    throw error;
  }
};

/**
 * Mark a notification as read
 * @param {string} notificationId
 * @returns {Promise<Object>} Updated notification
 */
export const markNotificationRead = async (notificationId) => {
  try {
    const response = await api.put(
      `/api/notifications/${encodeURIComponent(notificationId)}/read`
    );
    return response.data;
  } catch (error) {
    console.error('Error marking notification as read:', error);
    throw error;
  }
};

/**
 * Delete a notification
 * @param {string} notificationId
 * @returns {Promise<void>}
 */
export const deleteNotification = async (notificationId) => {
  try {
    await api.delete(
      `/api/notifications/${encodeURIComponent(notificationId)}`
    );
  } catch (error) {
    console.error('Error deleting notification:', error);
    throw error;
  }
};

/**
 * Create a new notification
 * @param {Object} notificationData
 * @returns {Promise<Object>} Created notification
 */
export const createNotification = async (notificationData) => {
  try {
    const response = await api.post('/api/notifications', notificationData);
    return response.data;
  } catch (error) {
    console.error('Error creating notification:', error);
    throw error;
  }
};

/**
 * Subscribe to live notifications stream (SSE) for a vehicle.
 * Tries authenticated fetch-based SSE first (supports Authorization header).
 * Falls back to EventSource with access token query (middleware supports query extraction).
 */
export const subscribeToNotificationsStream = (vehicleId, handlers = {}) => {
  if (!vehicleId) return () => {};
  const { onNotification, onError } = handlers;

  const url = `/api/notifications/stream?vehicleId=${encodeURIComponent(vehicleId)}`;
  const controller = new AbortController();

  (async () => {
    try {
      const res = await apiFetch(url, {
        method: 'GET',
        headers: { Accept: 'text/event-stream' },
        signal: controller.signal
      });
      if (!res.ok || !res.body) {
        const err = new Error(`Notifications stream failed (${res.status})`);
        err.code = 'STREAM_ERROR';
        onError && onError(err);
        return;
      }
      const reader = res.body.getReader();
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
            if (!raw.startsWith('data:')) continue;
            const payload = raw.replace(/^data:\s*/, '');
            try {
              const json = JSON.parse(payload);
              if (!json.error) {
                onNotification && onNotification(json);
              } else {
                const err = new Error(json.error);
                err.code = 'STREAM_ERROR';
                onError && onError(err);
              }
            } catch (e) {
              onError && onError(e);
            }
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') onError && onError(e);
    }
  })();

  return () => {
    try { controller.abort(); } catch {}
  };
};
