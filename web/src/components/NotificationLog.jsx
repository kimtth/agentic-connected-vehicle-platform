import { useState, useEffect, useCallback } from 'react';
import { Loader2 } from 'lucide-react';
import { fetchNotifications, subscribeToNotificationsStream } from '../api/notifications';

const NotificationLog = ({ vehicleId }) => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadNotifications = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchNotifications(vehicleId);
      setNotifications(data);
    } catch (error) {
      console.error('Error loading notifications:', error);
    } finally {
      setLoading(false);
    }
  }, [vehicleId]);

  useEffect(() => {
    if (!vehicleId) return;
    // Initial load
    loadNotifications();
    // SSE subscription (replaces polling)
    const unsubscribe = subscribeToNotificationsStream(vehicleId, {
      onNotification: (payload) => {
        setNotifications(prev => {
          if (prev.some(n => n.id === payload.id)) return prev;
          return [payload, ...prev];
        });
      }
    });
    return () => {
      unsubscribe && unsubscribe();
    };
  }, [vehicleId, loadNotifications]);

  // Helper function to safely get substring
  const safeSubstring = (str, start, end) => {
    return str ? str.substring(start, end) : 'N/A';
  };

  const formatType = (t) => t ? t.replace(/_/g, ' ') : 'N/A';

  return (
    <div className="p-5">
      <h1 className="text-xl font-semibold mb-3">Notification Log</h1>
      
      {loading && notifications.length === 0 ? (
        <div className="flex justify-center p-6">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      ) : (
        <div className="bg-card rounded-lg border border-border overflow-hidden">
          <div className="max-h-[700px] overflow-auto">
            <table className="w-full">
              <thead className="bg-muted sticky top-0 z-10">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium">ID</th>
                  <th className="px-3 py-2 text-left text-xs font-medium">Type</th>
                  <th className="px-3 py-2 text-left text-xs font-medium">Message</th>
                  <th className="px-3 py-2 text-left text-xs font-medium">Read</th>
                  <th className="px-3 py-2 text-left text-xs font-medium">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {notifications.length > 0 ? (
                  notifications.map((n) => (
                    <tr key={n.id} className="hover:bg-muted/50 transition-colors">
                      <td className="px-3 py-2 text-xs">{safeSubstring(n.id, 0, 8)}</td>
                      <td className="px-3 py-2 text-xs">{formatType(n.type)}</td>
                      <td className="px-3 py-2 text-xs">{n.message || 'N/A'}</td>
                      <td className="px-3 py-2 text-xs">{n.read ? 'Yes' : 'No'}</td>
                      <td className="px-3 py-2 text-xs">{n.timestamp ? new Date(n.timestamp).toLocaleTimeString() : 'N/A'}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-3 py-6 text-center text-xs text-muted-foreground">
                      No notifications found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationLog;
