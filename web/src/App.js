import { useState, useEffect, useCallback } from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box, Container, Grid, Paper, Typography, CircularProgress } from '@mui/material';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import DashboardLayout from './components/DashboardLayout';
import NotificationLog from './components/NotificationLog';
import ServiceInfo from './components/ServiceInfo';
import AgentChat from './components/AgentChat';
import SimulatorPanel from './components/simulator/SimulatorPanel';
import { fetchVehicles } from './api/vehicles';
import './App.css';
import Dashboard from './pages/Dashboard';
import AuthButtons from './components/auth/AuthButtons';
import ProtectedRoute from './auth/ProtectedRoute';

const theme = createTheme({
  palette: {
    primary: { main: '#1976d2' },
    secondary: { main: '#dc004e' },
    background: { default: '#f5f5f5' },
  },
});

function App() {
  const [vehicles, setVehicles] = useState([]);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [loading, setLoading] = useState(true);
  // eslint-disable-next-line no-unused-vars
  const navigate = useNavigate();
  // eslint-disable-next-line no-unused-vars
  const location = useLocation();

  const loadVehicles = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchVehicles();
      setVehicles(data || []);
      if ((data || []).length > 0) {
        setSelectedVehicle(data[0]);
      }
    } catch {
      // Simple fallback for hackathon use
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
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVehicles();
  }, [loadVehicles]);

  if (loading && vehicles.length === 0) {
    return (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Container maxWidth="sm" sx={{ textAlign: 'center', display: 'flex', flexDirection: 'column', justifyContent: 'center', minHeight: '100vh' }}>
          <CircularProgress />
          <Typography variant="h6" sx={{ mt: 2 }}>
            Loading vehicles...
          </Typography>
        </Container>
      </ThemeProvider>
    );
  }

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box className="App">
        <DashboardLayout
          vehicles={vehicles}
          selectedVehicle={selectedVehicle}
          onVehicleChange={setSelectedVehicle}
          extraHeaderRight={<AuthButtons />} // if DashboardLayout supports custom header slot
        >
          <Routes>
            <Route path="/" element={
              <ProtectedRoute>
                {selectedVehicle ? (
                  <Dashboard selectedVehicle={selectedVehicle} />
                ) : (
                  <Container maxWidth="sm" sx={{ textAlign: 'center' }}>
                    <Typography variant="h5" color="textSecondary">
                      No vehicles available. Please add a vehicle to start.
                    </Typography>
                  </Container>
                )}
              </ProtectedRoute>
            } />
            <Route path="/agent-chat" element={
              <ProtectedRoute>
                <Container maxWidth="lg">
                  <AgentChat vehicleId={selectedVehicle ? selectedVehicle.VehicleId : null} />
                </Container>
              </ProtectedRoute>
            } />
            <Route path="/simulator" element={
              <ProtectedRoute>
                <Container maxWidth="lg">
                  <SimulatorPanel vehicleId={selectedVehicle ? selectedVehicle.VehicleId : null} />
                </Container>
              </ProtectedRoute>
            } />
            {/* Public example route (About) left unprotected */}
            {/* Services Route */}
            <Route path="/services" element={
              <ProtectedRoute>
                <Container maxWidth="lg">
                  <Paper sx={{ p: 3 }}>
                    <Typography variant="h4" gutterBottom>Services</Typography>
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
              </ProtectedRoute>
            } />
            {/* Notifications Route */}
            <Route path="/notifications" element={
              <Container maxWidth="lg">
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h4" gutterBottom>Notifications</Typography>
                  <Typography variant="body1" paragraph>
                    This page displays all notifications from your connected vehicles.
                  </Typography>
                  <NotificationLog vehicleId={selectedVehicle?.VehicleId} />
                </Paper>
              </Container>
            } />
            {/* Settings */}
            <Route path="/settings" element={
              <Container maxWidth="lg">
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h4" gutterBottom>Settings</Typography>
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
            {/* Security */}
            <Route path="/security" element={
              <Container maxWidth="lg">
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h4" gutterBottom>Security</Typography>
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
            {/* About */}
            <Route path="/about" element={
              <Container maxWidth="lg">
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h4" gutterBottom>About</Typography>
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
            {/* Profile */}
            <Route path="/profile" element={
              <Container maxWidth="lg">
                <Paper sx={{ p: 3 }}>
                  <Typography variant="h4" gutterBottom>User Profile</Typography>
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