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
import ThemeToggle from './components/ThemeToggle';

// Create theme factory function
const createAppTheme = (mode) => createTheme({
  palette: {
    mode: mode,
    // Quick Action category colors
    quickActions: {
      features: '#5DADE2',  // Vehicle Features - Soft Blue
      remote:   '#85C1E9',  // Remote Access - Sky Blue
      emergency:'#F1948A',  // Emergency & Safety - Light Coral
      charging: '#F5B041',  // Charging & Energy - Light Orange
      info:     '#BB8FCE',  // Information Services - Soft Purple
    },
    ...(mode === 'dark' ? {
      primary: { main: '#1976d2' },
      secondary: { main: '#2979FF' },            // brighter electric blue
      success: { main: '#2ba18d' },
      warning: { main: '#BB8FCE' },
      error: { main: '#ff1900ff' },
      info: { main: '#0288d1' },                 // cooler info blue
      background: {
        default: '#05080F',
        paper: 'rgba(10,18,32,0.9)'             // deeper glass surface
      },
      text: {
        primary: '#E6F7FF',                      // slightly brighter
        secondary: '#A7C0DF'                     // cooler secondary
      }
    } : {
      primary: { main: '#1976d2' },
      secondary: { main: '#7c85ae' },
      success: { main: '#2ba18d' },
      warning: { main: '#BB8FCE' },
      error: { main: '#ff1900ff' },
      info: { main: '#0288d1' },
      background: {
        default: '#ffffff',
        paper: '#ffffff'
      },
      text: {
        primary: '#1a1a1a',
        secondary: '#666666'
      }
    })
  },
  shape: { borderRadius: 12 },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: mode === 'dark' ? {
          background:
            'radial-gradient(1200px 500px at 50% 120%, rgba(0,230,255,0.08), transparent 60%), linear-gradient(180deg, #0B1220 0%, #09101C 40%, #05080F 100%)',
          color: '#E6F7FF',
          accentColor: '#00E6FF',
          WebkitFontSmoothing: 'antialiased',
          MozOsxFontSmoothing: 'grayscale'
        } : {
          background: '#ffffff',
          color: '#1a1a1a',
          WebkitFontSmoothing: 'antialiased',
          MozOsxFontSmoothing: 'grayscale'
        }
      }
    },
    MuiPaper: {
      styleOverrides: {
        root: mode === 'dark' ? {
          backgroundImage: 'linear-gradient(180deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.03) 100%)',
          backdropFilter: 'blur(10px) saturate(140%)',
          border: '1px solid rgba(255,255,255,0.14)',
          boxShadow: '0 10px 30px rgba(0,0,0,0.55)'   // slightly deeper shadow
        } : {
          backgroundColor: '#ffffff',
          border: '1px solid #e5e7eb',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
        }
      }
    },
    MuiCard: {
      styleOverrides: {
        root: mode === 'dark' ? {
          backgroundImage: 'linear-gradient(180deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.03) 100%)',
          backdropFilter: 'blur(10px) saturate(140%)',
          border: '1px solid rgba(255,255,255,0.14)',
          boxShadow: '0 10px 30px rgba(0,0,0,0.55)'
        } : {
          backgroundColor: '#ffffff',
          border: '1px solid #e5e7eb',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
        }
      }
    },
    MuiAppBar: {
      styleOverrides: {
        colorPrimary: mode === 'dark' ? {
          backgroundImage:
            'linear-gradient(180deg, rgba(0,230,255,0.22) 0%, rgba(0,151,209,0.12) 100%), linear-gradient(180deg, #0B1220 0%, #09101C 50%, #05080F 100%)',
          backdropFilter: 'blur(12px) saturate(140%)',
          borderBottom: '1px solid rgba(255,255,255,0.14)',
          boxShadow: '0 10px 30px rgba(0,0,0,0.55)'
        } : {
          backgroundColor: '#1976d2',
          color: '#ffffff',
          borderBottom: '1px solid #e5e7eb',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          '& .MuiTypography-root': {
            color: '#ffffff'
          },
          '& .MuiIconButton-root': {
            color: '#ffffff'
          },
          '& .MuiFormControl-root .MuiInputLabel-root': {
            color: '#ffffff !important'
          },
          '& .MuiSelect-root': {
            color: '#ffffff'
          },
          '& .MuiOutlinedInput-notchedOutline': {
            borderColor: 'rgba(255,255,255,0.5) !important'
          }
        }
      }
    },
    MuiDrawer: {
      styleOverrides: {
        paper: mode === 'dark' ? {
          backgroundImage: 'linear-gradient(180deg, rgba(13,22,38,0.95) 0%, rgba(5,8,15,0.95) 100%)',
          backdropFilter: 'blur(10px) saturate(140%)',
          borderRight: '1px solid rgba(255,255,255,0.14)'
          // keep font/icon colors untouched
        } : {
          backgroundColor: '#f8f9fa',
          borderRight: '1px solid #e5e7eb',
          // no font color overrides in light mode
          '& .MuiListItemButton-root:hover': {
            backgroundColor: 'rgba(25, 118, 210, 0.08)'
          }
        }
      }
    },
    MuiButton: {
      styleOverrides: {
        containedPrimary: mode === 'dark' ? {
          backgroundImage: 'linear-gradient(180deg, rgba(0,230,255,0.26) 0%, rgba(0,151,209,0.18) 100%)',
          border: '1px solid rgba(0,230,255,0.35)',
          boxShadow: '0 0 0 2px rgba(0,230,255,0.2), 0 0 30px rgba(0,230,255,0.25)',
          '&:hover': {
            boxShadow: '0 0 0 2px rgba(0,230,255,0.35), 0 0 45px rgba(0,230,255,0.28)'
          }
        } : {},
        outlined: {
          borderColor: mode === 'dark' ? 'rgba(255,255,255,0.24)' : '#e5e7eb'
        }
      }
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: mode === 'dark' ? {
          background: 'linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02))',
          '& fieldset': { borderColor: 'rgba(255,255,255,0.24)' },
          '&:hover fieldset': { borderColor: 'rgba(0,230,255,0.6)' },
          '&.Mui-focused fieldset': {
            borderColor: '#00E6FF',
            boxShadow: '0 0 0 2px rgba(0,230,255,0.35)'
          }
        } : {
          '& fieldset': { borderColor: '#e5e7eb' },
          '&:hover fieldset': { borderColor: '#1976d2' },
          '&.Mui-focused fieldset': {
            borderColor: '#1976d2'
          }
        }
      }
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: { height: 8, borderRadius: 4 },
        bar: { borderRadius: 4 }
      }
    },
    MuiChip: {
      styleOverrides: {
        outlined: { 
          borderColor: mode === 'dark' ? 'rgba(255,255,255,0.24)' : '#e5e7eb'
        }
      }
    }
  }
});

function App() {
  const [vehicles, setVehicles] = useState([]);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [themeMode, setThemeMode] = useState(() => {
    return localStorage.getItem('themeMode') || 'dark';
  });

  const theme = createAppTheme(themeMode);

  const toggleTheme = () => {
    const newMode = themeMode === 'dark' ? 'light' : 'dark';
    setThemeMode(newMode);
    localStorage.setItem('themeMode', newMode);
  };

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
          extraHeaderRight={<AuthButtons />}
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
                        <Typography variant="h6" gutterBottom>Theme Settings</Typography>
                        <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
                          Choose between light and dark theme.
                        </Typography>
                        <ThemeToggle 
                          currentTheme={themeMode} 
                          onToggleTheme={toggleTheme}
                        />
                      </Paper>
                    </Grid>
                    <Grid item xs={12} md={6}>
                      <Paper sx={{ p: 2 }}>
                        <Typography variant="h6" gutterBottom>Application Settings</Typography>
                        <Typography variant="body2" color="textSecondary">
                          Set your language and notification preferences.
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