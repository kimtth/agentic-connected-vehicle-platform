import React, { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box, Container, Grid, Paper, Typography } from '@mui/material';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import Dashboard from './components/Dashboard';
import CarStatus from './components/CarStatus';
import CommandLog from './components/CommandLog';
import NotificationLog from './components/NotificationLog';
import ServiceInfo from './components/ServiceInfo';
import VehicleDashboard from './components/VehicleDashboard';
import AgentChat from './components/AgentChat';
import CarSimulator from './components/CarSimulator';
import { fetchVehicles } from './api/vehicles';
import './App.css';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
});

function App() {
  const [vehicles, setVehicles] = useState([]);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  // eslint-disable-next-line no-unused-vars
  const navigate = useNavigate();
  // eslint-disable-next-line no-unused-vars
  const location = useLocation();

  useEffect(() => {
    const loadVehicles = async () => {
      try {
        const data = await fetchVehicles();
        setVehicles(data);
        if (data.length > 0) {
          setSelectedVehicle(data[0]);
        }
      } catch (error) {
        console.error('Error loading vehicles:', error);
      }
    };

    loadVehicles();
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box className="App">
        <Dashboard 
          vehicles={vehicles} 
          selectedVehicle={selectedVehicle} 
          onVehicleChange={setSelectedVehicle}
        >
          <Routes>
            <Route path="/" element={
              selectedVehicle ? (
                <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                  <Grid container spacing={3}>
                    {/* Car Status */}
                    <Grid item xs={12} md={6}>
                      <Paper
                        sx={{
                          p: 2,
                          display: 'flex',
                          flexDirection: 'column',
                          height: 280,
                        }}
                      >
                        <CarStatus vehicleId={selectedVehicle.VehicleId} />
                      </Paper>
                    </Grid>
                    
                    {/* Service Info */}
                    <Grid item xs={12} md={6}>
                      <Paper
                        sx={{
                          p: 2,
                          display: 'flex',
                          flexDirection: 'column',
                          height: 280,
                        }}
                      >
                        <ServiceInfo vehicleId={selectedVehicle.VehicleId} />
                      </Paper>
                    </Grid>
                    
                    {/* Command Log */}
                    <Grid item xs={12} md={6}>
                      <Paper
                        sx={{
                          p: 2,
                          display: 'flex',
                          flexDirection: 'column',
                          height: 270,
                        }}
                      >
                        <CommandLog vehicleId={selectedVehicle.VehicleId} />
                      </Paper>
                    </Grid>
                    
                    {/* Notification Log */}
                    <Grid item xs={12} md={6}>
                      <Paper
                        sx={{
                          p: 2,
                          display: 'flex',
                          flexDirection: 'column',
                          height: 270,
                        }}
                      >
                        <NotificationLog vehicleId={selectedVehicle.VehicleId} />
                      </Paper>
                    </Grid>
                  </Grid>
                </Container>
              ) : (
                <Container maxWidth="sm" sx={{ mt: 10, textAlign: 'center' }}>
                  <Typography variant="h5" color="textSecondary">
                    No vehicles available. Please add a vehicle to start.
                  </Typography>
                </Container>
              )
            } />
            
            {/* Vehicle Dashboard Route - now will work with proper navigation */}
            <Route path="/vehicle-dashboard" element={
              selectedVehicle ? (
                <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                  <VehicleDashboard vehicleId={selectedVehicle.VehicleId} />
                </Container>
              ) : (
                <Container maxWidth="sm" sx={{ mt: 10, textAlign: 'center' }}>
                  <Typography variant="h5" color="textSecondary">
                    No vehicles available. Please select a vehicle first.
                  </Typography>
                </Container>
              )
            } />
            
            {/* Agent Chat Route */}
            <Route path="/agent-chat" element={
              <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                <AgentChat vehicleId={selectedVehicle ? selectedVehicle.VehicleId : null} />
              </Container>
            } />
            
            {/* Car Simulator Route */}
            <Route path="/car-simulator" element={
              <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                <CarSimulator />
              </Container>
            } />
            
            {/* Services Route */}
            <Route path="/services" element={
              <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h4" gutterBottom>
                    Services
                  </Typography>
                  <Typography variant="body1" paragraph>
                    This page displays all available services for your vehicles.
                  </Typography>
                  {selectedVehicle ? (
                    <ServiceInfo vehicleId={selectedVehicle.VehicleId} />
                  ) : (
                    <Typography variant="subtitle1" color="text.secondary">
                      Please select a vehicle to view services.
                    </Typography>
                  )}
                </Paper>
              </Container>
            } />
            
            {/* Notifications Route */}
            <Route path="/notifications" element={
              <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h4" gutterBottom>
                    Notifications
                  </Typography>
                  <Typography variant="body1" paragraph>
                    This page displays all notifications from your connected vehicles.
                  </Typography>
                  <NotificationLog vehicleId={selectedVehicle?.VehicleId} />
                </Paper>
              </Container>
            } />
            
            {/* Other routes */}
            {/* ...existing code... */}
          </Routes>
        </Dashboard>
      </Box>
    </ThemeProvider>
  );
}

export default App;
