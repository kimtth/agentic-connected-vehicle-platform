import React, { useState, useEffect } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box, Container, Grid, Paper, Typography } from '@mui/material';
import Dashboard from './components/Dashboard';
import CarStatus from './components/CarStatus';
import CommandLog from './components/CommandLog';
import NotificationLog from './components/NotificationLog';
import ServiceInfo from './components/ServiceInfo';
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
          {selectedVehicle ? (
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
                    <CommandLog />
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
                    <NotificationLog />
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
          )}
        </Dashboard>
      </Box>
    </ThemeProvider>
  );
}

export default App;
