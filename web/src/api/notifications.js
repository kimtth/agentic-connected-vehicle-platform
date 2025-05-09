import { api } from './apiClient';

/**
 * Fetch notifications from the backend API
 * @param {string} vehicleId - Optional vehicle ID to filter notifications
 * @returns {Promise<Array>} Array of notification objects
 */
export const fetchNotifications = async (vehicleId) => {
  try {
    const url = vehicleId ? `/notifications?vehicleId=${vehicleId}` : '/notifications';
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
