import React, { useState, useEffect } from 'react';
import { 
  Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, Paper, Typography, Box,
  CircularProgress
} from '@mui/material';
import { fetchNotifications } from '../api/notifications';

const NotificationLog = () => {
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadNotifications();
    // Poll for updates every 5 seconds
    const interval = setInterval(loadNotifications, 5000);
    return () => clearInterval(interval);
  }, []);

  const loadNotifications = async () => {
    try {
      setLoading(true);
      const data = await fetchNotifications();
      setNotifications(data);
    } catch (error) {
      console.error('Error loading notifications:', error);
    } finally {
      setLoading(false);
    }
  };

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
        <TableContainer component={Paper} sx={{ maxHeight: 200 }}>
          <Table stickyHeader aria-label="notification log table" size="small" className="notification-log-table">
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Command ID</TableCell>
                <TableCell>Vehicle ID</TableCell>
                <TableCell>Message</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Timestamp</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {notifications.length > 0 ? (
                notifications.map((notification) => (
                  <TableRow key={notification.notificationId}>
                    <TableCell>{notification.notificationId.substring(0, 8)}</TableCell>
                    <TableCell>{notification.commandId.substring(0, 8)}</TableCell>
                    <TableCell>{notification.vehicleId}</TableCell>
                    <TableCell>{notification.message}</TableCell>
                    <TableCell>{notification.status}</TableCell>
                    <TableCell>{new Date(notification.timestamp).toLocaleTimeString()}</TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={6} align="center">
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
