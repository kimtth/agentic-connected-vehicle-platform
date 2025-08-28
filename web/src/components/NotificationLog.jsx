import { useState, useEffect, useCallback } from 'react';
import { 
  Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, Paper, Typography, Box,
  CircularProgress
} from '@mui/material';
import { fetchNotifications } from '../api/notifications';
import { INTERVALS } from '../config/intervals';

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
    loadNotifications();
    // Poll for updates using centralized interval configuration
    const interval = setInterval(loadNotifications, INTERVALS.NOTIFICATIONS_POLLING);
    return () => clearInterval(interval);
  }, [loadNotifications]);

  // Helper function to safely get substring
  const safeSubstring = (str, start, end) => {
    return str ? str.substring(start, end) : 'N/A';
  };

  const formatType = (t) => t ? t.replace(/_/g, ' ') : 'N/A';

  return (
    <>
      <Typography variant="h6" component="h2" gutterBottom>
        Notification Log
      </Typography>
      
      {loading && notifications.length === 0 ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
          <CircularProgress size={24} />
        </Box>
      ) : (
        <TableContainer component={Paper} sx={{ maxHeight: 800 }}>
          <Table stickyHeader aria-label="notification log table" size="small" className="notification-log-table">
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Type</TableCell>
                <TableCell>Message</TableCell>
                <TableCell>Read</TableCell>
                <TableCell>Timestamp</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {notifications.length > 0 ? (
                notifications.map((n) => (
                  <TableRow key={n.id}>
                    <TableCell>{safeSubstring(n.id, 0, 8)}</TableCell>
                    <TableCell>{formatType(n.type)}</TableCell>
                    <TableCell>{n.message || 'N/A'}</TableCell>
                    <TableCell>{n.read ? 'Yes' : 'No'}</TableCell>
                    <TableCell>{n.timestamp ? new Date(n.timestamp).toLocaleTimeString() : 'N/A'}</TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={5} align="center">
                    No notifications found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </>
  );
};

export default NotificationLog;
