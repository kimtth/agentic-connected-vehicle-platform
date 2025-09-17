import React, { useState, useEffect, useCallback } from 'react';
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
  AcUnit,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { RecordVoiceOver } from '@mui/icons-material'; // added
import { useNavigate } from 'react-router-dom';
import VehicleMetrics from '../components/simulator/VehicleMetrics';
import { fetchVehicleStatus } from '../api/status';
import { fetchNotifications } from '../api/notifications';
import { useTheme } from '@mui/material/styles';

const Dashboard = ({ selectedVehicle }) => {
  const theme = useTheme();
  const navigate = useNavigate();
  const [vehicleStatus, setVehicleStatus] = useState({
    speed: 0,
    battery: 0,
    temperature: 0,
    engineTemp: 0,
    oilRemaining: 0,
    odometer: 0,
    // engine: 'off', // added
    timestamp: null
  });
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refreshDashboard = useCallback(async () => {
    if (!selectedVehicle) {
      setLoading(false);
      return;
    }
    const vehicleId = selectedVehicle.vehicleId;
    try {
      setLoading(true);
      setError(null);
      // Fetch status
      const status = await fetchVehicleStatus(vehicleId).catch(() => null);
      if (status) {
        setVehicleStatus({
          speed: status.speed ?? 0,
          battery: status.battery ?? 0,
          temperature: status.temperature ?? 0,
          engineTemp: status.engineTemp ?? status.temperature ?? 0,
          oilRemaining: status.oilRemaining ?? 0,
          odometer: status.odometer ?? 0,
          // engine: status.engine ?? status.engineStatus ?? ((status.speed ?? 0) > 0 ? 'on' : 'off'), // added
          timestamp: status.timestamp || new Date().toISOString()
        });
      }
      // Fetch notifications
      const notificationData = await fetchNotifications(vehicleId).catch(() => []);
      setNotifications(Array.isArray(notificationData) ? notificationData.slice(0, 5) : []);
    } catch {
      setError('Failed to load dashboard data. Is the backend running on port 8000?');
    } finally {
      setLoading(false);
    }
  }, [selectedVehicle]);

  useEffect(() => {
    refreshDashboard();
  }, [refreshDashboard]);

  useEffect(() => {
    // Apply theme class to body for CSS variables
    document.body.setAttribute('data-theme', theme?.palette?.mode || 'dark');
    
    return () => {
      document.body.removeAttribute('data-theme');
    };
  }, [theme?.palette?.mode]);

  const quickStats = [
    {
      label: 'Current Speed',
      rawValue: vehicleStatus.speed,
      icon: <SpeedIcon />,
      color: 'primary',
      unit: 'km/h'
    },
    {
      label: 'Battery Level',
      rawValue: vehicleStatus.battery,
      icon: <BatteryIcon />,
      color: 'success',
      unit: '%',
      showProgress: true
    },
    {
      label: 'Engine Temp',
      rawValue: vehicleStatus.engineTemp,
      icon: <TempIcon />,
      color: 'warning',
      unit: '°C'
    },
    {
      label: 'Oil Level',
      rawValue: vehicleStatus.oilRemaining,
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
    <Box sx={{ 
      py: 3,
      overflow: 'hidden',
      '&::-webkit-scrollbar': { display: 'none' },
      msOverflowStyle: 'none',
      scrollbarWidth: 'none',
    }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h5" gutterBottom>
          Vehicle Dashboard
        </Typography>
        <Typography variant="subtitle1" color="text.secondary">
          {selectedVehicle.make} {selectedVehicle.model} ({selectedVehicle.vehicleId})
        </Typography>
        <Box sx={{ mt: 2 }}>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={refreshDashboard}
            disabled={loading || !selectedVehicle}
          >
            {loading ? 'Refreshing...' : 'Refresh'}
          </Button>
        </Box>
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
                      Last updated: {vehicleStatus.timestamp ? new Date(vehicleStatus.timestamp).toLocaleTimeString() : '-'}
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
              <Grid item xs={12} md={3}>
                <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <CardActionArea
                    component="div"
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate('/agent-chat')}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate('/agent-chat'); } }}
                  >
                    <CardContent sx={{ textAlign: 'center', p: 3, flexGrow: 1 }}>
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

              <Grid item xs={12} md={3}>
                <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <CardActionArea
                    component="div"
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate('/simulator')}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate('/simulator'); } }}
                  >
                    <CardContent sx={{ textAlign: 'center', p: 3, flexGrow: 1 }}>
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

              <Grid item xs={12} md={3}>
                <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <CardActionArea
                    component="div"
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate('/services')}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate('/services'); } }}
                  >
                    <CardContent sx={{ textAlign: 'center', p: 3, flexGrow: 1 }}>
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

              <Grid item xs={12} md={3}>
                <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                  <CardActionArea
                    component="div"
                    role="button"
                    tabIndex={0}
                    onClick={() => navigate(`/voice-control?vehicleId=${selectedVehicle.vehicleId}`)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(`/voice-control?vehicleId=${selectedVehicle.vehicleId}`); } }}
                  >
                    <CardContent sx={{ textAlign: 'center', p: 3, flexGrow: 1 }}>
                      <RecordVoiceOver sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
                      <Typography variant="h6" component="div" gutterBottom>
                        Voice Control
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        Use real-time speech & avatar assistant
                      </Typography>
                      <Button
                        variant="contained"
                        color="primary"
                        sx={{ mt: 2 }}
                        startIcon={<RecordVoiceOver />}
                      >
                        Launch
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
                    onClick={() => navigate(`/agent-chat?query=enable eco mode&vehicleId=${selectedVehicle.vehicleId}`)}
                  >
                    Eco Mode
                  </Button>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<AcUnit />}
                    onClick={() => navigate(`/agent-chat?query=adjust climate control&vehicleId=${selectedVehicle.vehicleId}`)}
                  >
                    Climate Control
                  </Button>
                </Grid>
                <Grid item xs={12} sm={6} md={3}>
                  <Button
                    fullWidth
                    variant="outlined"
                    startIcon={<SpeedIcon />}
                    onClick={() => navigate(`/agent-chat?query=run vehicle diagnostics&vehicleId=${selectedVehicle.vehicleId}`)}
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
                      onClick={() => navigate(`/agent-chat?query=initiate emergency call&vehicleId=${selectedVehicle.vehicleId}`)}
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
                      onClick={() => navigate(`/agent-chat?query=activate SOS&vehicleId=${selectedVehicle.vehicleId}`)}
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
                        secondaryTypographyProps={{ component: 'div' }}
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
    </Box>
  );
};

export default Dashboard;