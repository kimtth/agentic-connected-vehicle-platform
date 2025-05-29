import React, { useState, useEffect } from 'react';
import { 
  Grid, Typography, Card, CardContent, CardActionArea, 
  Box, Paper, Button, Divider, CircularProgress, Alert, LinearProgress
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { 
  DirectionsCar, Speed, Battery90, Notifications, 
  SupportAgent, Settings, EnergySavingsLeaf, AcUnit, 
  LocalGasStation, Build
} from '@mui/icons-material';
import { fetchVehicleStatus } from '../api/status';

const Dashboard = ({ selectedVehicle }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [vehicleStatus, setVehicleStatus] = useState(null);
  const [statusError, setStatusError] = useState(null);

  // Fetch vehicle status when a vehicle is selected
  useEffect(() => {
    const getVehicleStatus = async () => {
      if (!selectedVehicle) return;
      
      setLoading(true);
      try {
        const status = await fetchVehicleStatus(selectedVehicle.VehicleId);
        setVehicleStatus(status);
        setStatusError(null);
      } catch (error) {
        console.error('Error fetching vehicle status:', error);
        setStatusError('Failed to load vehicle status. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    getVehicleStatus();
  }, [selectedVehicle]);

  // Navigation handlers
  const handleViewVehicleDashboard = () => {
    navigate('/vehicle-dashboard');
  };

  const handleViewNotifications = () => {
    navigate('/notifications');
  };

  const handleViewServices = () => {
    navigate('/services');
  };

  const handleChatWithAgent = () => {
    navigate('/agent-chat');
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Connected Vehicle Platform
      </Typography>
      
      {statusError && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {statusError}
        </Alert>
      )}
      
      {!selectedVehicle ? (
        <Alert severity="info" sx={{ mb: 3 }}>
          Please select a vehicle from the dropdown to view its details.
        </Alert>
      ) : (
        <Paper sx={{ p: 3, mb: 4, bgcolor: 'primary.main', color: 'white' }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} md={6}>
              <Typography variant="h5">
                {selectedVehicle.Make} {selectedVehicle.Model}
              </Typography>
              <Typography variant="subtitle1">
                Vehicle ID: {selectedVehicle.VehicleId}
              </Typography>
              <Typography variant="body2" sx={{ mt: 1 }}>
                Year: {selectedVehicle.Year} • VIN: {selectedVehicle.VIN}
              </Typography>
            </Grid>
            <Grid item xs={12} md={6} sx={{ textAlign: { xs: 'left', md: 'right' } }}>
              <Button 
                variant="contained" 
                color="secondary"
                onClick={handleViewVehicleDashboard}
                sx={{ mr: 1 }}
              >
                View Full Dashboard
              </Button>
              <Button 
                variant="outlined" 
                color="inherit"
                onClick={() => navigate(`/simulator?vehicleId=${selectedVehicle.VehicleId}`)}
              >
                Test Simulator
              </Button>
            </Grid>
          </Grid>
        </Paper>
      )}
      
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', my: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <Typography variant="h5" gutterBottom sx={{ mt: 3, mb: 2 }}>
            Vehicle Status
          </Typography>
          
          <Grid container spacing={3} sx={{ mb: 4 }}>
            {selectedVehicle && vehicleStatus ? (
              <>
                <Grid item xs={12} sm={6} md={3}>
                  <Card sx={{ height: '100%' }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Speed color="primary" sx={{ fontSize: '2.5rem', mr: 2 }} />
                        <Box>
                          <Typography color="textSecondary" variant="body2">
                            Current Speed
                          </Typography>
                          <Typography variant="h4" component="div">
                            {vehicleStatus.Speed} km/h
                          </Typography>
                        </Box>
                      </Box>
                      <Typography variant="body2" color="textSecondary">
                        Last updated: {new Date().toLocaleTimeString()}
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
                
                <Grid item xs={12} sm={6} md={3}>
                  <Card sx={{ height: '100%' }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <Battery90 color="success" sx={{ fontSize: '2.5rem', mr: 2 }} />
                        <Box>
                          <Typography color="textSecondary" variant="body2">
                            Battery Level
                          </Typography>
                          <Typography variant="h4" component="div">
                            {vehicleStatus.Battery}%
                          </Typography>
                        </Box>
                      </Box>
                      <LinearProgress 
                        variant="determinate"
                        value={vehicleStatus.Battery} 
                        sx={{ mb: 1, height: 8, borderRadius: 4 }}
                        color="success"
                      />
                    </CardContent>
                  </Card>
                </Grid>
                
                <Grid item xs={12} sm={6} md={3}>
                  <Card sx={{ height: '100%' }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <LocalGasStation color="warning" sx={{ fontSize: '2.5rem', mr: 2 }} />
                        <Box>
                          <Typography color="textSecondary" variant="body2">
                            Oil Level
                          </Typography>
                          <Typography variant="h4" component="div">
                            {vehicleStatus.OilRemaining}%
                          </Typography>
                        </Box>
                      </Box>
                      <LinearProgress 
                        variant="determinate"
                        value={vehicleStatus.OilRemaining} 
                        sx={{ mb: 1, height: 8, borderRadius: 4 }}
                        color="warning"
                      />
                    </CardContent>
                  </Card>
                </Grid>
                
                <Grid item xs={12} sm={6} md={3}>
                  <Card sx={{ height: '100%' }}>
                    <CardContent>
                      <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                        <AcUnit color="info" sx={{ fontSize: '2.5rem', mr: 2 }} />
                        <Box>
                          <Typography color="textSecondary" variant="body2">
                            Temperature
                          </Typography>
                          <Typography variant="h4" component="div">
                            {vehicleStatus.Temperature}°C
                          </Typography>
                        </Box>
                      </Box>
                      <Typography variant="body2" color="textSecondary">
                        Outside: 24°C
                      </Typography>
                    </CardContent>
                  </Card>
                </Grid>
              </>
            ) : (
              <Grid item xs={12}>
                <Paper sx={{ p: 3, textAlign: 'center' }}>
                  <Typography color="textSecondary">
                    No vehicle data available. Please select a vehicle.
                  </Typography>
                </Paper>
              </Grid>
            )}
          </Grid>
          
          <Divider sx={{ my: 4 }} />
          
          <Typography variant="h5" gutterBottom sx={{ mt: 3, mb: 2 }}>
            Quick Actions
          </Typography>
          
          <Grid container spacing={3}>
            <Grid item xs={12} md={4}>
              <Card>
                <CardActionArea onClick={handleChatWithAgent}>
                  <CardContent sx={{ textAlign: 'center', p: 3 }}>
                    <SupportAgent sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
                    <Typography variant="h5" component="div" gutterBottom>
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
                    <DirectionsCar sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
                    <Typography variant="h5" component="div" gutterBottom>
                      Car Simulator
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Test and simulate vehicle commands and responses
                    </Typography>
                    <Button 
                      variant="contained" 
                      color="primary" 
                      sx={{ mt: 2 }}
                      startIcon={<DirectionsCar />}
                    >
                      Launch Simulator
                    </Button>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={4}>
              <Card>
                <CardActionArea onClick={handleViewServices}>
                  <CardContent sx={{ textAlign: 'center', p: 3 }}>
                    <Build sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
                    <Typography variant="h5" component="div" gutterBottom>
                      Service Status
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      View upcoming maintenance and service details
                    </Typography>
                    <Button 
                      variant="contained" 
                      color="primary" 
                      sx={{ mt: 2 }}
                      startIcon={<Build />}
                    >
                      View Services
                    </Button>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          </Grid>
          
          {/* Enhanced Quick Settings with Vehicle Features */}
          <Grid container spacing={3} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <Card>
                <CardActionArea onClick={handleViewNotifications}>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <Notifications color="secondary" sx={{ fontSize: '2rem', mr: 2 }} />
                      <Typography variant="h6">Recent Notifications</Typography>
                    </Box>
                    <Divider sx={{ mb: 2 }} />
                    {selectedVehicle ? (
                      <Box>
                        <Typography variant="body2" sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
                          <Box component="span" sx={{ 
                            display: 'inline-block', 
                            width: 8, 
                            height: 8, 
                            borderRadius: '50%', 
                            bgcolor: 'error.main',
                            mr: 1
                          }} />
                          Low tire pressure detected in rear left tire
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 1, display: 'flex', alignItems: 'center' }}>
                          <Box component="span" sx={{ 
                            display: 'inline-block', 
                            width: 8, 
                            height: 8, 
                            borderRadius: '50%', 
                            bgcolor: 'warning.main',
                            mr: 1
                          }} />
                          Scheduled maintenance due in 500km
                        </Typography>
                        <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center' }}>
                          <Box component="span" sx={{ 
                            display: 'inline-block', 
                            width: 8, 
                            height: 8, 
                            borderRadius: '50%', 
                            bgcolor: 'info.main',
                            mr: 1
                          }} />
                          Weather alert: Heavy rain expected in your location
                        </Typography>
                      </Box>
                    ) : (
                      <Typography color="textSecondary">
                        Select a vehicle to view notifications
                      </Typography>
                    )}
                    <Button 
                      fullWidth 
                      variant="text" 
                      color="primary" 
                      sx={{ mt: 2 }}
                    >
                      View All Notifications
                    </Button>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
            
            <Grid item xs={12} md={6}>
              <Card>
                <CardActionArea onClick={() => navigate('/settings')}>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                      <Settings color="primary" sx={{ fontSize: '2rem', mr: 2 }} />
                      <Typography variant="h6">Vehicle Controls</Typography>
                    </Box>
                    <Divider sx={{ mb: 2 }} />
                    <Grid container spacing={2}>
                      <Grid item xs={6}>
                        <Button 
                          fullWidth 
                          variant="outlined" 
                          startIcon={<EnergySavingsLeaf />}
                          onClick={() => selectedVehicle && navigate(`/agent-chat?action=eco_mode&vehicleId=${selectedVehicle.VehicleId}`)}
                          disabled={!selectedVehicle}
                        >
                          Eco Mode
                        </Button>
                      </Grid>
                      <Grid item xs={6}>
                        <Button 
                          fullWidth 
                          variant="outlined" 
                          startIcon={<AcUnit />}
                          onClick={() => selectedVehicle && navigate(`/agent-chat?action=climate&vehicleId=${selectedVehicle.VehicleId}`)}
                          disabled={!selectedVehicle}
                        >
                          Climate Control
                        </Button>
                      </Grid>
                      <Grid item xs={6}>
                        <Button 
                          fullWidth 
                          variant="outlined" 
                          startIcon={<Speed />}
                          onClick={() => selectedVehicle && navigate(`/agent-chat?action=diagnostics&vehicleId=${selectedVehicle.VehicleId}`)}
                          disabled={!selectedVehicle}
                        >
                          Diagnostics
                        </Button>
                      </Grid>
                      <Grid item xs={6}>
                        <Button 
                          fullWidth 
                          variant="outlined" 
                          startIcon={<Notifications />}
                          onClick={() => navigate('/notifications')}
                        >
                          Alerts
                        </Button>
                      </Grid>
                    </Grid>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          </Grid>
        </>
      )}
    </Box>
  );
};

export default Dashboard;