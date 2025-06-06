import { useState, useEffect, useCallback } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box, Container, Grid, Paper, Typography, Alert, CircularProgress } from '@mui/material';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import DashboardLayout from './components/DashboardLayout';
import NotificationLog from './components/NotificationLog';
import ServiceInfo from './components/ServiceInfo';
import AgentChat from './components/AgentChat';
import SimulatorPanel from './components/simulator/SimulatorPanel';
import { fetchVehicles } from './api/vehicles';
import './App.css';
import Dashboard from './pages/Dashboard';

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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);
  const [offlineMode, setOfflineMode] = useState(false);
  // eslint-disable-next-line no-unused-vars
  const navigate = useNavigate();
  // eslint-disable-next-line no-unused-vars
  const location = useLocation();

  const loadVehicles = useCallback(async (isRetry = false) => {
    if (!isRetry) {
      setLoading(true);
      setError(null);
    }
    
    try {
      const data = await fetchVehicles();
      setVehicles(data);
      if (data.length > 0) {
        setSelectedVehicle(data[0]);
      }
      setOfflineMode(false);
      setRetryCount(0);
    } catch (error) {
      console.error('Error loading vehicles:', error);
      
      // Check if this is a connection error
      if (error.message.includes('backend server') || error.message.includes('timeout') || error.message.includes('not reachable')) {
        setOfflineMode(true);
        setError('Backend server is not available. Running in offline mode.');
        
        // Create mock data for offline mode
        const mockVehicles = [
          {
            VehicleId: 'demo-vehicle-001',
            vehicleId: 'demo-vehicle-001',
            Make: 'Demo',
            Model: 'Car',
            Year: 2024,
            Status: 'Demo Mode'
          }
        ];
        setVehicles(mockVehicles);
        setSelectedVehicle(mockVehicles[0]);
      } else {
        setError('Failed to load vehicles. Please check your connection and try again.');
      }
      
      setRetryCount(prev => prev + 1);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleRetry = useCallback(() => {
    loadVehicles(true);
  }, [loadVehicles]);

  useEffect(() => {
    loadVehicles();
  }, [loadVehicles]);

  // Auto-retry logic for connection issues
  useEffect(() => {
    if (offlineMode && retryCount < 3) {
      const retryTimeout = setTimeout(() => {
        console.log(`Auto-retry attempt ${retryCount + 1}/3`);
        loadVehicles(true);
      }, 10000 * (retryCount + 1)); // 10s, 20s, 30s delays
      
      return () => clearTimeout(retryTimeout);
    }
  }, [offlineMode, retryCount, loadVehicles]);

  // Show loading state
  if (loading && vehicles.length === 0) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Container maxWidth="sm" sx={{ textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '100vh' }}>
          <CircularProgress />
          <Typography variant="h6" sx={{ mt: 2 }}>
            Loading vehicles data...
          </Typography>
          {retryCount > 0 && (
            <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
              Retry attempt {retryCount}...
            </Typography>
          )}
        </Container>
      </ThemeProvider>
    );
  }

  // Show error state with retry option
  if (error && !offlineMode) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Container maxWidth="sm" sx={{ p: 2 }}>
          <Alert 
            severity="error" 
            sx={{ mb: 2 }}
            action={
              <button onClick={handleRetry} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer' }}>
                Retry
              </button>
            }
          >
            {error}
          </Alert>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h5" gutterBottom>
              Connection Error
            </Typography>
            <Typography variant="body1" paragraph>
              Could not connect to the backend server. Please verify:
            </Typography>
            <Typography component="ol" sx={{ pl: 2 }}>
              <li>The backend server is running on port 8000</li>
              <li>There are no firewall or network issues blocking the connection</li>
              <li>The API URL in the .env file is correctly configured</li>
            </Typography>
          </Paper>
        </Container>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box className="App">
        {offlineMode && (
          <Alert severity="warning" sx={{ mb: 0, borderRadius: 0 }}>
            Running in offline mode - some features may be limited. 
            {retryCount < 3 && ` Retrying connection... (${retryCount}/3)`}
          </Alert>
        )}
        <DashboardLayout 
          vehicles={vehicles} 
          selectedVehicle={selectedVehicle} 
          onVehicleChange={setSelectedVehicle}
        >
          <Routes>
            <Route path="/" element={
              selectedVehicle ? (
                <Dashboard selectedVehicle={selectedVehicle} />
              ) : (
                <Container maxWidth="sm" sx={{ textAlign: 'center' }}>
                  <Typography variant="h5" color="textSecondary">
                    No vehicles available. Please add a vehicle to start.
                  </Typography>
                </Container>
              )
            } />
            
            {/* Agent Chat Route */}
            <Route path="/agent-chat" element={
              <Container maxWidth="lg">
                <AgentChat vehicleId={selectedVehicle ? selectedVehicle.VehicleId : null} />
              </Container>
            } />
            
            {/* Car Simulator Route */}
            <Route path="/simulator" element={
              <Container maxWidth="lg">
                <SimulatorPanel vehicleId={selectedVehicle ? selectedVehicle.VehicleId : null} />
              </Container>
            } />
            
            {/* Services Route */}
            <Route path="/services" element={
              <Container maxWidth="lg">
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
              <Container maxWidth="lg">
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
            
            {/* Settings Route */}
            <Route path="/settings" element={
              <Container maxWidth="lg">
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h4" gutterBottom>
                    Settings
                  </Typography>
                  <Typography variant="body1" paragraph>
                    Configure your account and application preferences.
                  </Typography>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Paper sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Application Settings</Typography>
                        <Typography variant="body2" color="textSecondary">
                          Set your theme, language, and notification preferences.
                        </Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Paper sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Vehicle Settings</Typography>
                        <Typography variant="body2" color="textSecondary">
                          Configure settings for your connected vehicles.
                        </Typography>
                      </Paper>
                    </Grid>
                  </Grid>
                </Paper>
              </Container>
            } />
            
            {/* Security Route */}
            <Route path="/security" element={
              <Container maxWidth="lg">
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h4" gutterBottom>
                    Security
                  </Typography>
                  <Typography variant="body1" paragraph>
                    Manage your security settings and access control.
                  </Typography>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Paper sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Password & Authentication</Typography>
                        <Typography variant="body2" color="textSecondary">
                          Change your password and set up two-factor authentication.
                        </Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Paper sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Access Logs</Typography>
                        <Typography variant="body2" color="textSecondary">
                          View recent account activity and login history.
                        </Typography>
                      </Paper>
                    </Grid>
                  </Grid>
                </Paper>
              </Container>
            } />
            
            {/* About Route */}
            <Route path="/about" element={
              <Container maxWidth="lg">
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h4" gutterBottom>
                    About
                  </Typography>
                  <Typography variant="body1" paragraph>
                    Learn more about the Connected Vehicle Platform.
                  </Typography>
                  <Grid container spacing={3}>
                    <Grid item xs={12}>
                      <Paper sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Version</Typography>
                        <Typography variant="body2" color="textSecondary">
                          Current version: 1.0.0
                        </Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={12}>
                      <Paper sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Support</Typography>
                        <Typography variant="body2" color="textSecondary">
                          For assistance, please contact support@connected-car-platform.com
                        </Typography>
                      </Paper>
                    </Grid>
                  </Grid>
                </Paper>
              </Container>
            } />
            
            {/* Profile Route */}
            <Route path="/profile" element={
              <Container maxWidth="lg">
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h4" gutterBottom>
                    User Profile
                  </Typography>
                  <Typography variant="body1" paragraph>
                    Manage your personal information and account settings.
                  </Typography>
                  <Grid container spacing={3}>
                    <Grid item xs={12} md={6}>
                      <Paper sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Personal Information</Typography>
                        <Typography variant="body2" color="textSecondary">
                          Update your name, email, and contact details.
                        </Typography>
                      </Paper>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Paper sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Preferences</Typography>
                        <Typography variant="body2" color="textSecondary">
                          Set your account preferences and notification settings.
                        </Typography>
                      </Paper>
                    </Grid>
                  </Grid>
                </Paper>
              </Container>
            } />
          </Routes>
        </DashboardLayout>
      </Box>
    </ThemeProvider>
  );
}

export default App;
