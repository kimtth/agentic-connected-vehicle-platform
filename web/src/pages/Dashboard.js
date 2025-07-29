import React, { useState, useEffect } from 'react';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Box,
  Card,
  CardContent,
  CardActionArea,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  Chip,
  Alert,
  Button,
  LinearProgress,
  CircularProgress
} from '@mui/material';
import {
  Speed as SpeedIcon,
  BatteryChargingFull as BatteryIcon,
  Thermostat as TempIcon,
  DirectionsCar as CarIcon,
  Notifications as NotificationIcon,
  Build as ServiceIcon,
  SupportAgent,
  LocalGasStation,
  EnergySavingsLeaf,
  AcUnit
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import VehicleMetrics from '../components/simulator/VehicleMetrics';
import { fetchVehicleStatus } from '../api/status';
import { fetchNotifications } from '../api/notifications';
import { INTERVALS, createVehicleStatusThrottle } from '../config/intervals';

const Dashboard = ({ selectedVehicle }) => {
  const navigate = useNavigate();
  const [vehicleStatus, setVehicleStatus] = useState({
    engineTemp: '0°C',
    speed: '0 km/h',
    batteryLevel: '0%',
    odometer: '0 km',
    Speed: 0,
    Battery: 0,
    Temperature: 0,
    OilRemaining: 0
  });
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const isMounted = React.useRef(true);

  useEffect(() => {
    // Fix: Remove the incorrect early return that prevents effect from running
    isMounted.current = true;

    const loadDashboardData = async () => {
      if (!selectedVehicle || !isMounted.current) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        // Load vehicle status with throttling
        const vehicleId = selectedVehicle.VehicleId || selectedVehicle.vehicleId;
        if (createVehicleStatusThrottle(vehicleId)) {
          const status = await fetchVehicleStatus(vehicleId);
          if (status && Object.keys(status).length > 0 && isMounted.current) {
            setVehicleStatus({
              engineTemp: `${status.Temperature || 0}°C`,
              speed: `${status.Speed || 0} km/h`,
              batteryLevel: `${status.Battery || 0}%`,
              odometer: status.Odometer ? `${status.Odometer} km` : '0 km',
              Speed: status.Speed || 0,
              Battery: status.Battery || 0,
              Temperature: status.Temperature || 0,
              OilRemaining: status.OilRemaining || 0
            });
          }
        }

        // Load recent notifications
        try {
          const notificationData = await fetchNotifications(vehicleId);
          if (Array.isArray(notificationData) && isMounted.current) {
            setNotifications(notificationData.slice(0, 5)); // Show only recent 5
          } else if (isMounted.current) {
            setNotifications([]);
          }
        } catch (notificationError) {
          console.warn('Could not load notifications:', notificationError);
          if (isMounted.current) {
            setNotifications([]);
          }
        }

      } catch (err) {
        console.error('Error loading dashboard data:', err);
        
        if (isMounted.current) {
          // More specific error messages based on error type
          let errorMessage = 'Failed to load dashboard data.';
          if (err.message?.includes('fetch') || err.name === 'TypeError') {
            errorMessage = 'Unable to connect to vehicle services. Please check if the backend is running on port 8000.';
          } else if (err.status === 404) {
            errorMessage = 'Vehicle not found. Please verify the vehicle ID.';
          } else if (err.status >= 500) {
            errorMessage = 'Vehicle services are experiencing issues. Please try again later.';
          }
          
          setError(errorMessage);
        }
      } finally {
        if (isMounted.current) {
          setLoading(false);
        }
      }
    };

    loadDashboardData();
    
    // Use centralized interval configuration with proper cleanup
    const interval = setInterval(() => {
      if (isMounted.current) {
        loadDashboardData();
      }
    }, INTERVALS.DASHBOARD_REFRESH);
    
    return () => {
      isMounted.current = false;
      clearInterval(interval);
    };
  }, [selectedVehicle]);

  const quickStats = [
    {
      label: 'Current Speed',
      value: vehicleStatus.speed,
      rawValue: vehicleStatus.Speed,
      icon: <SpeedIcon />,
      color: 'primary',
      unit: 'km/h'
    },
    {
      label: 'Battery Level',
      value: vehicleStatus.batteryLevel,
      rawValue: vehicleStatus.Battery,
      icon: <BatteryIcon />,
      color: 'success',
      unit: '%',
      showProgress: true
    },
    {
      label: 'Engine Temp',
      value: vehicleStatus.engineTemp,
      rawValue: vehicleStatus.Temperature,
      icon: <TempIcon />,
      color: 'warning',
      unit: '°C'
    },
    {
      label: 'Oil Level',
      value: `${vehicleStatus.OilRemaining}%`,
      rawValue: vehicleStatus.OilRemaining,
      icon: <LocalGasStation />,
      color: 'info',
      unit: '%',
      showProgress: true
    }
  ];

  if (loading) {
    return (
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Alert severity="error">{error}</Alert>
      </Container>
    );
  }

  if (!selectedVehicle) {
    return (
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Alert severity="info">Please select a vehicle to view the dashboard.</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Vehicle Dashboard
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          {selectedVehicle.Make} {selectedVehicle.Model} ({selectedVehicle.VehicleId || selectedVehicle.vehicleId})
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* Enhanced Quick Stats */}
        <Grid item xs={12}>
          <Grid container spacing={2}>
            {quickStats.map((stat, index) => (
              <Grid item xs={12} sm={6} md={3} key={index}>
                <Card sx={{ height: '100%' }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <Box sx={{ color: `${stat.color}.main`, mr: 2 }}>
                        {stat.icon}
                      </Box>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="subtitle2" color="text.secondary">
                          {stat.label}
                        </Typography>
                        <Typography variant="h5" component="div">
                          {typeof stat.rawValue === 'number' ? stat.rawValue : 0}{stat.unit}
                        </Typography>
                      </Box>
                    </Box>
                    {stat.showProgress && (
                      <LinearProgress
                        variant="determinate"
                        value={stat.rawValue || 0}
                        sx={{ height: 8, borderRadius: 4 }}
                        color={stat.color}
                      />
                    )}
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      Last updated: {new Date().toLocaleTimeString()}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Grid>

                {/* Enhanced Quick Actions */}
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <ServiceIcon sx={{ mr: 1 }} />
              Quick Actions
            </Typography>
            <Grid container spacing={3} sx={{ mt: 1 }}>
              <Grid item xs={12} md={4}>
                <Card>
                  <CardActionArea onClick={() => navigate('/agent-chat')}>
                    <CardContent sx={{ textAlign: 'center', p: 3 }}>
                      <SupportAgent sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
                      <Typography variant="h6" component="div" gutterBottom>
                        Agent Chat
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Get assistance and control your vehicle with AI-powered chat
                      </Typography>
                      <Button
                        variant="contained"
                        color="primary"
                        sx={{ mt: 2 }}
                        startIcon={<SupportAgent />}
                      >
                        Start Chat
                      </Button>
                    </CardContent>
                  </CardActionArea>
                </Card>
              </Grid>

              <Grid item xs={12} md={4}>
                <Card>
                  <CardActionArea onClick={() => navigate('/simulator')}>
                    <CardContent sx={{ textAlign: 'center', p: 3 }}>
                      <CarIcon sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
                      <Typography variant="h6" component="div" gutterBottom>
                        Car Simulator
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Test and simulate vehicle commands and responses
                      </Typography>
                      <Button
                        variant="contained"
                        color="primary"
                        sx={{ mt: 2 }}
                        startIcon={<CarIcon />}
                      >
                        Launch Simulator
                      </Button>
                    </CardContent>
                  </CardActionArea>
                </Card>
              </Grid>

              <Grid item xs={12} md={4}>
                <Card>
                  <CardActionArea onClick={() => navigate('/services')}>
                    <CardContent sx={{ textAlign: 'center', p: 3 }}>
                      <ServiceIcon sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
                      <Typography variant="h6" component="div" gutterBottom>
                        Service Status
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        View upcoming maintenance and service details
                      </Typography>
                      <Button
                        variant="contained"
                        color="primary"
                        sx={{ mt: 2 }}
                        startIcon={<ServiceIcon />}
                      >
                        View Services
                      </Button>
                    </CardContent>
                  </CardActionArea>
                </Card>
              </Grid>
            </Grid>

            {/* Vehicle Controls */}
            <Box sx={{ mt: 3 }}>
              <Typography variant="h6" gutterBottom>
                Vehicle Controls
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<EnergySavingsLeaf />}
                    onClick={() => navigate(`/agent-chat?query=enable eco mode&vehicleId=${selectedVehicle.VehicleId || selectedVehicle.vehicleId}`)}
                  >
                    Eco Mode
                  </Button>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<AcUnit />}
                    onClick={() => navigate(`/agent-chat?query=adjust climate control&vehicleId=${selectedVehicle.VehicleId || selectedVehicle.vehicleId}`)}
                  >
                    Climate Control
                  </Button>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<SpeedIcon />}
                    onClick={() => navigate(`/agent-chat?query=run vehicle diagnostics&vehicleId=${selectedVehicle.VehicleId || selectedVehicle.vehicleId}`)}
                  >
                    Diagnostics
                  </Button>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<NotificationIcon />}
                    onClick={() => navigate('/notifications')}
                  >
                    View Alerts
                  </Button>
                </Grid>
              </Grid>
              
              {/* Emergency Controls */}
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                  Emergency Controls
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <Button
                      fullWidth
                      variant="outlined"
                      color="warning"
                      onClick={() => navigate(`/agent-chat?query=initiate emergency call&vehicleId=${selectedVehicle.VehicleId || selectedVehicle.vehicleId}`)}
                      sx={{ color: 'warning.main', borderColor: 'warning.main' }}
                    >
                      Emergency Call
                    </Button>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Button
                      fullWidth
                      variant="outlined"
                      color="error"
                      onClick={() => navigate(`/agent-chat?query=activate SOS&vehicleId=${selectedVehicle.VehicleId || selectedVehicle.vehicleId}`)}
                      sx={{ color: 'error.main', borderColor: 'error.main' }}
                    >
                      SOS Assistance
                    </Button>
                  </Grid>
                </Grid>
              </Box>
            </Box>
          </Paper>
        </Grid>

        {/* Vehicle Metrics Chart */}
        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: '400px' }}>
            <Typography variant="h6" gutterBottom>
              Vehicle Metrics
            </Typography>
            <VehicleMetrics vehicleStatus={vehicleStatus} />
          </Paper>
        </Grid>

        {/* Recent Notifications */}
        <Grid item xs={12} md={4}>
          <Paper sx={{ p: 3, height: '400px', overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <NotificationIcon sx={{ mr: 1 }} />
              Recent Notifications
            </Typography>
            <Divider sx={{ mb: 2 }} />

            {notifications.length > 0 ? (
              <List dense>
                {notifications.map((notification, index) => (
                  <div key={notification.id || index}>
                    <ListItem sx={{ px: 0 }}>
                      <ListItemIcon>
                        <Box
                          sx={{
                            width: 8,
                            height: 8,
                            borderRadius: '50%',
                            bgcolor: notification.severity === 'error' ? 'error.main' :
                              notification.severity === 'warning' ? 'warning.main' : 'info.main'
                          }}
                        />
                      </ListItemIcon>
                      <ListItemText
                        primary={notification.message || notification.title}
                        secondary={
                          <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                            <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
                              {notification.timestamp ? new Date(notification.timestamp).toLocaleString() : 'Recent'}
                            </Typography>
                            {notification.severity && (
                              <Chip
                                label={notification.severity}
                                size="small"
                                color={notification.severity === 'error' ? 'error' :
                                  notification.severity === 'warning' ? 'warning' : 'default'}
                                variant="outlined"
                              />
                            )}
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < notifications.length - 1 && <Divider />}
                  </div>
                ))}
              </List>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', mt: 4 }}>
                No recent notifications
              </Typography>
            )}
            <Button
              fullWidth
              variant="text"
              color="primary"
              sx={{ mt: 2 }}
              onClick={() => navigate('/notifications')}
            >
              View All Notifications
            </Button>
          </Paper>
        </Grid>


      </Grid>
    </Container>
  );
};

export default Dashboard;