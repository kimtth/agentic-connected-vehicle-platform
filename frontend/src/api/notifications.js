import { api } from './apiClient';

/**
 * Fetch notifications from the backend API
 * @returns {Promise<Array>} Array of notification objects
 */
export const fetchNotifications = async () => {
  try {
    const response = await api.get('/notifications');
    if (!response.data) {
      return [];
    }

    // Map the data to match the expected format in UI
    const notifications = response.data.map((notification) => ({
      notificationId: notification.id || notification.notificationId,
      commandId: notification.commandId || '',
      vehicleId: notification.vehicleId,
      message: notification.message,
      status: notification.type || notification.status || 'info',
      timestamp: notification.timestamp || notification.createdTime,
      read: notification.isRead || notification.read || false,
    }));

    // Sort by timestamp - most recent first
    return notifications.sort(
      (a, b) => new Date(b.timestamp) - new Date(a.timestamp)
    );
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
      `/notification/${notificationId}/read`,
      { read: true }
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
    await api.delete(`/notification/${notificationId}`);
  } catch (error) {
    console.error('Error deleting notification:', error);
    throw error;
  }
};
