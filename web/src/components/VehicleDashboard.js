import { useState, useEffect } from 'react';
import { 
  Box, Typography, Grid, Slider, Button, Card, CardContent, CircularProgress,
  IconButton, Menu, MenuItem, ListItemIcon, ListItemText
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { 
  Speed, LocalGasStation, Battery90, Thermostat, 
  AcUnit, WbSunny, VolumeUp, BluetoothAudio, DirectionsCar, 
  Sync, DeviceThermostat, MoreVert, Build,
  Lightbulb, Lock, LockOpen, PowerSettingsNew, Stop,
  KeyboardArrowUp, KeyboardArrowDown, Warning, LocalHospital
} from '@mui/icons-material';
import { fetchVehicleStatus, subscribeToVehicleStatus, updateVehicleStatus, updateClimateSettings } from '../api/status';
import { useNavigate } from 'react-router-dom';

// Custom styled components for the dashboard
const DashboardContainer = styled(Box)(({ theme }) => ({
  background: '#111',
  borderRadius: theme.spacing(2),
  padding: theme.spacing(3),
  color: '#fff',
  minHeight: '600px',
  boxShadow: '0 0 20px rgba(0,0,0,0.5)'
}));

const GaugeContainer = styled(Box)(({ theme }) => ({
  position: 'relative',
  textAlign: 'center',
  width: '180px',
  height: '180px',
  margin: '0 auto',
  display: 'flex',
  flexDirection: 'column',
  justifyContent: 'center',
  alignItems: 'center'
}));

const GaugeCircle = styled(Box)(({ value, max, color }) => {
  const progressValue = Math.min(100, Math.max(0, (value / max) * 100));
  return {
    width: '100%',
    height: '100%',
    borderRadius: '50%',
    background: `radial-gradient(circle closest-side, #111 79%, transparent 80% 100%), 
                conic-gradient(${color} ${progressValue}%, #333 0)`,
    position: 'absolute',
    zIndex: 1
  };
});

const ControlPanel = styled(Card)(({ theme }) => ({
  background: '#222',
  color: '#fff',
  marginTop: theme.spacing(2),
  borderRadius: theme.spacing(1)
}));

const ControlGrid = styled(Grid)(({ theme }) => ({
  padding: theme.spacing(2)
}));

const VehicleControlSection = styled(Card)(({ theme }) => ({
  background: 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
  color: '#fff',
  marginBottom: theme.spacing(2),
  borderRadius: theme.spacing(2),
}));

const ControlButton = styled(Button)(({ theme, variant: buttonVariant = 'primary' }) => ({
  margin: theme.spacing(0.5),
  minWidth: '120px',
  color: buttonVariant === 'emergency' ? theme.palette.error.contrastText : '#fff',
  backgroundColor: buttonVariant === 'emergency' 
    ? theme.palette.error.main 
    : 'rgba(255, 255, 255, 0.1)',
  border: `1px solid ${buttonVariant === 'emergency' 
    ? theme.palette.error.main 
    : 'rgba(255, 255, 255, 0.3)'}`,
  '&:hover': {
    backgroundColor: buttonVariant === 'emergency' 
      ? theme.palette.error.dark 
      : 'rgba(255, 255, 255, 0.2)',
  },
}));

const VehicleDashboard = ({ vehicleId }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [temperature, setTemperature] = useState(22);
  const [fanSpeed, setFanSpeed] = useState(2);
  const [acOn, setAcOn] = useState(true);
  const [mediaVolume, setMediaVolume] = useState(60);
  const [isUpdating, setIsUpdating] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [anchorEl, setAnchorEl] = useState(null);
  const [vehicleFeatures, setVehicleFeatures] = useState({
    lights: { headlights: 'off', interior: 'off', hazard: 'off' },
    doors: { locked: true },
    engine: { status: 'off' },
    windows: { driver: 'up', passenger: 'up', rear_left: 'up', rear_right: 'up' },
    climate: { temperature: 22, auto: true, ac: 'off' }
  });
  const navigate = useNavigate();

  useEffect(() => {
    let subscription = null;
    
    const initializeStatus = async () => {
      try {
        setLoading(true);
        // Get initial data
        const initialData = await fetchVehicleStatus(vehicleId);
        setStatus(initialData);
        
        // Start the real-time subscription with better error handling
        subscription = await subscribeToVehicleStatus(vehicleId, (newStatus) => {
          setStatus(newStatus);
          setError(null);
        }, (err) => {
          // More robust error handling
          const errorMessage = err ? (err.message || 'Unknown error') : 'Connection failed';
          setError('Error with real-time connection: ' + errorMessage);
          console.error('Subscription error:', err);
        });
      } catch (err) {
        // Also improve error handling here
        const errorMessage = err ? (err.message || 'Unknown error') : 'Unknown error';
        setError('Error loading vehicle status: ' + errorMessage);
        console.error('Vehicle status error:', err);
      } finally {
        setLoading(false);
      }
    };

    initializeStatus();
    
    // Cleanup subscription when component unmounts
    return () => {
      if (subscription && typeof subscription.unsubscribe === 'function') {
        subscription.unsubscribe();
      }
    };
  }, [vehicleId]);

  // Handler for climate control updates
  const handleClimateUpdate = async () => {
    if (!vehicleId || !status) return;
    
    setIsUpdating(true);
    setStatusMessage('Updating climate settings...');
    
    try {
      // Create climate settings object
      const climateSettings = {
        temperature: temperature,
        fanSpeed: fanSpeed === 0 ? 'off' : fanSpeed === 1 ? 'low' : fanSpeed === 2 ? 'medium' : 'high',
        isAirConditioningOn: acOn,
        isHeatingOn: !acOn
      };
      
      // Send update to the API
      await updateClimateSettings(vehicleId, climateSettings);
      
      setStatusMessage('Climate settings updated successfully!');
      
      // Clear message after a few seconds
      setTimeout(() => setStatusMessage(''), 3000);
    } catch (err) {
      console.error('Failed to update climate settings:', err);
      setStatusMessage('Failed to update climate settings. Please try again.');
    } finally {
      setIsUpdating(false);
    }
  };
  
  // Handler for media volume update
  const handleMediaUpdate = async () => {
    if (!vehicleId || !status) return;
    
    setIsUpdating(true);
    setStatusMessage('Updating media settings...');
    
    try {
      // Create a partial status update with media settings
      const mediaSettings = {
        mediaSettings: {
          volume: mediaVolume,
          source: 'bluetooth' // Default source
        }
      };
      
      // Send update to the API
      await updateVehicleStatus(vehicleId, mediaSettings);
      
      setStatusMessage('Media settings updated successfully!');
      
      // Clear message after a few seconds
      setTimeout(() => setStatusMessage(''), 3000);
    } catch (err) {
      console.error('Failed to update media settings:', err);
      setStatusMessage('Failed to update media settings. Please try again.');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleMenuOpen = (event) => {
    setAnchorEl(event.currentTarget);
  };
  
  const handleMenuClose = () => {
    setAnchorEl(null);
  };
  
  const launchSimulator = () => {
    navigate(`/simulator?vehicleId=${vehicleId}`);
    handleMenuClose();
  };

  const handleFeatureControl = async (feature, action, params = {}) => {
    try {
      const response = await fetch(`/api/vehicles/${vehicleId}/features/${feature}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, ...params })
      });
      
      if (response.ok) {
        const result = await response.json();
        // Update local state based on the action
        setVehicleFeatures(prev => ({
          ...prev,
          [feature]: { ...prev[feature], ...result.data }
        }));
      }
    } catch (error) {
      console.error(`Error controlling ${feature}:`, error);
    }
  };

  const handleRemoteAccess = async (action, params = {}) => {
    try {
      const endpoint = action.includes('door') ? 'doors' : 
                     action.includes('engine') ? 'engine' : 'locate';
      
      const response = await fetch(`/api/vehicles/${vehicleId}/remote/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: action.replace('_doors', '').replace('_engine', ''), ...params })
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('Remote access result:', result);
      }
    } catch (error) {
      console.error('Error with remote access:', error);
    }
  };

  const handleEmergency = async (emergencyType) => {
    try {
      const response = await fetch(`/api/vehicles/${vehicleId}/emergency/${emergencyType}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          emergency_type: emergencyType,
          location: { latitude: 43.6532, longitude: -79.3832 } // Toronto coordinates
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        alert(`Emergency ${emergencyType} activated: ${result.message}`);
      }
    } catch (error) {
      console.error('Error activating emergency:', error);
    }
  };

  if (loading && !status) {
    return (
      <DashboardContainer sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <CircularProgress color="primary" />
      </DashboardContainer>
    );
  }

  if (error) {
    return (
      <DashboardContainer>
        {/* <Typography color="error">{error}</Typography> */}
      </DashboardContainer>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      <DashboardContainer>
        <Typography variant="h4" gutterBottom sx={{ 
          textAlign: 'center', 
          color: '#1976d2',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          Vehicle Dashboard
          <IconButton onClick={handleMenuOpen} sx={{ color: '#fff' }}>
            <MoreVert />
          </IconButton>
        </Typography>
        
        <Menu
          anchorEl={anchorEl}
          open={Boolean(anchorEl)}
          onClose={handleMenuClose}
        >
          <MenuItem onClick={launchSimulator}>
            <ListItemIcon>
              <DirectionsCar fontSize="small" />
            </ListItemIcon>
            <ListItemText primary="Launch Simulator" />
          </MenuItem>
          <MenuItem onClick={handleMenuClose}>
            <ListItemIcon>
              <Build fontSize="small" />
            </ListItemIcon>
            <ListItemText primary="Vehicle Diagnostics" />
          </MenuItem>
        </Menu>
        
        {status && (
          <>
            {/* Primary Gauges */}
            <Grid container spacing={3} sx={{ marginBottom: 3 }}>
              {/* Speedometer */}
              <Grid item xs={12} md={4}>
                <GaugeContainer>
                  <GaugeCircle value={status.Speed} max={200} color="#1976d2" />
                  <Box sx={{ position: 'relative', zIndex: 2 }}>
                    <Speed sx={{ fontSize: 40, color: '#1976d2', mb: 1 }} />
                    <Typography variant="h3" sx={{ fontWeight: 'bold' }}>
                      {status.Speed}
                    </Typography>
                    <Typography variant="subtitle1">km/h</Typography>
                  </Box>
                </GaugeContainer>
              </Grid>
              
              {/* Battery Level */}
              <Grid item xs={12} md={4}>
                <GaugeContainer>
                  <GaugeCircle value={status.Battery} max={100} color="#4caf50" />
                  <Box sx={{ position: 'relative', zIndex: 2 }}>
                    <Battery90 sx={{ fontSize: 40, color: '#4caf50', mb: 1 }} />
                    <Typography variant="h3" sx={{ fontWeight: 'bold' }}>
                      {status.Battery}
                    </Typography>
                    <Typography variant="subtitle1">% Battery</Typography>
                  </Box>
                </GaugeContainer>
              </Grid>
              
              {/* Oil Level */}
              <Grid item xs={12} md={4}>
                <GaugeContainer>
                  <GaugeCircle value={status.OilRemaining} max={100} color="#ff9800" />
                  <Box sx={{ position: 'relative', zIndex: 2 }}>
                    <LocalGasStation sx={{ fontSize: 40, color: '#ff9800', mb: 1 }} />
                    <Typography variant="h3" sx={{ fontWeight: 'bold' }}>
                      {status.OilRemaining}
                    </Typography>
                    <Typography variant="subtitle1">% Oil</Typography>
                  </Box>
                </GaugeContainer>
              </Grid>
            </Grid>
            
            {/* Control Panels */}
            <Grid container spacing={2}>
              {/* Climate Controls */}
              <Grid item xs={12} md={6}>
                <ControlPanel>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      <DeviceThermostat sx={{ verticalAlign: 'middle', mr: 1 }} />
                      Climate Control
                    </Typography>
                    
                    <ControlGrid container spacing={2} alignItems="center">
                      <Grid item xs={8}>
                        <Typography>Temperature ({temperature}°C)</Typography>
                        <Slider
                          value={temperature}
                          onChange={(e, newValue) => setTemperature(newValue)}
                          min={16}
                          max={30}
                          step={0.5}
                          valueLabelDisplay="auto"
                          sx={{ color: '#1976d2' }}
                        />
                      </Grid>
                      <Grid item xs={4}>
                        <Button 
                          variant="contained" 
                          color="primary" 
                          startIcon={acOn ? <AcUnit /> : <WbSunny />}
                          onClick={() => setAcOn(!acOn)}
                          fullWidth
                        >
                          {acOn ? 'A/C' : 'Heat'}
                        </Button>
                      </Grid>
                      
                      <Grid item xs={12}>
                        <Typography>Fan Speed (Level {fanSpeed})</Typography>
                        <Slider
                          value={fanSpeed}
                          onChange={(e, newValue) => setFanSpeed(newValue)}
                          min={0}
                          max={5}
                          step={1}
                          marks
                          valueLabelDisplay="auto"
                          sx={{ color: '#1976d2' }}
                        />
                      </Grid>
                      
                      {/* Add a button to apply changes */}
                      <Grid item xs={12}>
                        <Button 
                          variant="contained" 
                          color="primary"
                          onClick={handleClimateUpdate}
                          disabled={isUpdating}
                          fullWidth
                          sx={{ mt: 2 }}
                        >
                          {isUpdating ? <CircularProgress size={24} /> : 'Apply Climate Settings'}
                        </Button>
                      </Grid>
                    </ControlGrid>
                  </CardContent>
                </ControlPanel>
              </Grid>
              
              {/* Entertainment Controls */}
              <Grid item xs={12} md={6}>
                <ControlPanel>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>
                      <VolumeUp sx={{ verticalAlign: 'middle', mr: 1 }} />
                      Entertainment System
                    </Typography>
                    
                    <ControlGrid container spacing={2} alignItems="center">
                      <Grid item xs={8}>
                        <Typography>Volume ({mediaVolume}%)</Typography>
                        <Slider
                          value={mediaVolume}
                          onChange={(e, newValue) => setMediaVolume(newValue)}
                          min={0}
                          max={100}
                          valueLabelDisplay="auto"
                          sx={{ color: '#1976d2' }}
                        />
                      </Grid>
                      <Grid item xs={4}>
                        <Button 
                          variant="contained" 
                          color="primary" 
                          startIcon={<BluetoothAudio />}
                          fullWidth
                        >
                          Bluetooth
                        </Button>
                      </Grid>
                      
                      <Grid item xs={12} sx={{ mt: 1 }}>
                        <Grid container spacing={1}>
                          <Grid item xs={4}>
                            <Button variant="outlined" fullWidth sx={{ color: '#fff', borderColor: '#555' }}>
                              Radio
                            </Button>
                          </Grid>
                          <Grid item xs={4}>
                            <Button variant="outlined" fullWidth sx={{ color: '#fff', borderColor: '#555' }}>
                              Media
                            </Button>
                          </Grid>
                          <Grid item xs={4}>
                            <Button variant="outlined" fullWidth sx={{ color: '#fff', borderColor: '#555' }}>
                              Phone
                            </Button>
                          </Grid>
                        </Grid>
                      </Grid>
                      
                      {/* Add a button to apply changes */}
                      <Grid item xs={12}>
                        <Button 
                          variant="contained" 
                          color="primary"
                          onClick={handleMediaUpdate}
                          disabled={isUpdating}
                          fullWidth
                          sx={{ mt: 2 }}
                        >
                          {isUpdating ? <CircularProgress size={24} /> : 'Apply Media Settings'}
                        </Button>
                      </Grid>
                    </ControlGrid>
                  </CardContent>
                </ControlPanel>
              </Grid>
              
              {/* Vehicle Stats */}
              <Grid item xs={12}>
                <ControlPanel>
                  <CardContent>
                    <Grid container spacing={2}>
                      <Grid item xs={6} md={3}>
                        <Typography variant="body2" color="text.secondary">Engine Temperature</Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Thermostat sx={{ color: status.Temperature > 70 ? '#f44336' : '#4caf50', mr: 1 }} />
                          <Typography variant="h6">{status.Temperature}°C</Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={6} md={3}>
                        <Typography variant="body2" color="text.secondary">Outside Temperature</Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <DeviceThermostat sx={{ color: '#1976d2', mr: 1 }} />
                          <Typography variant="h6">24°C</Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={6} md={3}>
                        <Typography variant="body2" color="text.secondary">Trip Distance</Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <DirectionsCar sx={{ color: '#1976d2', mr: 1 }} />
                          <Typography variant="h6">78.5 km</Typography>
                        </Box>
                      </Grid>
                      <Grid item xs={6} md={3}>
                        <Typography variant="body2" color="text.secondary">System Status</Typography>
                        <Box sx={{ display: 'flex', alignItems: 'center' }}>
                          <Sync sx={{ color: '#4caf50', mr: 1 }} />
                          <Typography variant="h6">Connected</Typography>
                        </Box>
                      </Grid>
                    </Grid>
                  </CardContent>
                </ControlPanel>
              </Grid>
              
              {/* Vehicle Feature Controls */}
              <Grid item xs={12}>
                <VehicleControlSection>
                  <CardContent>
                    <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
                      <DirectionsCar sx={{ mr: 1 }} />
                      Vehicle Controls
                    </Typography>
                    
                    {/* Lights Control */}
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="subtitle2" gutterBottom>Lighting</Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        <ControlButton
                          startIcon={<Lightbulb />}
                          onClick={() => handleFeatureControl('lights', 
                            vehicleFeatures.lights.headlights === 'on' ? 'off' : 'on',
                            { light_type: 'headlights' }
                          )}
                        >
                          Headlights {vehicleFeatures.lights.headlights === 'on' ? 'OFF' : 'ON'}
                        </ControlButton>
                        <ControlButton
                          startIcon={<Lightbulb />}
                          onClick={() => handleFeatureControl('lights', 
                            vehicleFeatures.lights.interior === 'on' ? 'off' : 'on',
                            { light_type: 'interior_lights' }
                          )}
                        >
                          Interior {vehicleFeatures.lights.interior === 'on' ? 'OFF' : 'ON'}
                        </ControlButton>
                        <ControlButton
                          startIcon={<Warning />}
                          onClick={() => handleFeatureControl('lights', 
                            vehicleFeatures.lights.hazard === 'on' ? 'off' : 'on',
                            { light_type: 'hazard_lights' }
                          )}
                        >
                          Hazards {vehicleFeatures.lights.hazard === 'on' ? 'OFF' : 'ON'}
                        </ControlButton>
                      </Box>
                    </Box>

                    {/* Climate Control */}
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="subtitle2" gutterBottom>Climate Control</Typography>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                        <Typography variant="body2">Temperature: {vehicleFeatures.climate.temperature}°C</Typography>
                        <Button
                          size="small"
                          onClick={() => handleFeatureControl('climate', 'set_temperature', 
                            { temperature: vehicleFeatures.climate.temperature - 1 }
                          )}
                        >-</Button>
                        <Button
                          size="small"
                          onClick={() => handleFeatureControl('climate', 'set_temperature', 
                            { temperature: vehicleFeatures.climate.temperature + 1 }
                          )}
                        >+</Button>
                      </Box>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        <ControlButton
                          startIcon={<AcUnit />}
                          onClick={() => handleFeatureControl('climate', 'cooling', { temperature: 18 })}
                        >
                          Cooling
                        </ControlButton>
                        <ControlButton
                          startIcon={<WbSunny />}
                          onClick={() => handleFeatureControl('climate', 'heating', { temperature: 26 })}
                        >
                          Heating
                        </ControlButton>
                      </Box>
                    </Box>

                    {/* Windows Control */}
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="subtitle2" gutterBottom>Windows</Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        <ControlButton
                          startIcon={<KeyboardArrowUp />}
                          onClick={() => handleFeatureControl('windows', 'up', { windows: 'all' })}
                        >
                          All Windows UP
                        </ControlButton>
                        <ControlButton
                          startIcon={<KeyboardArrowDown />}
                          onClick={() => handleFeatureControl('windows', 'down', { windows: 'all' })}
                        >
                          All Windows DOWN
                        </ControlButton>
                      </Box>
                    </Box>

                    {/* Remote Access */}
                    <Box sx={{ mb: 3 }}>
                      <Typography variant="subtitle2" gutterBottom>Remote Access</Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        <ControlButton
                          startIcon={vehicleFeatures.doors.locked ? <LockOpen /> : <Lock />}
                          onClick={() => handleRemoteAccess(vehicleFeatures.doors.locked ? 'unlock_doors' : 'lock_doors')}
                        >
                          {vehicleFeatures.doors.locked ? 'UNLOCK' : 'LOCK'} Doors
                        </ControlButton>
                        <ControlButton
                          startIcon={vehicleFeatures.engine.status === 'running' ? <Stop /> : <PowerSettingsNew />}
                          onClick={() => handleRemoteAccess(
                            vehicleFeatures.engine.status === 'running' ? 'stop_engine' : 'start_engine'
                          )}
                        >
                          {vehicleFeatures.engine.status === 'running' ? 'STOP' : 'START'} Engine
                        </ControlButton>
                        <ControlButton
                          startIcon={<VolumeUp />}
                          onClick={() => handleRemoteAccess('locate')}
                        >
                          Horn & Lights
                        </ControlButton>
                      </Box>
                    </Box>

                    {/* Emergency Controls */}
                    <Box>
                      <Typography variant="subtitle2" gutterBottom>Emergency</Typography>
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                        <ControlButton
                          variant="emergency"
                          startIcon={<LocalHospital />}
                          onClick={() => handleEmergency('sos')}
                        >
                          SOS Emergency
                        </ControlButton>
                        <ControlButton
                          variant="emergency"
                          startIcon={<Warning />}
                          onClick={() => handleEmergency('collision')}
                        >
                          Report Collision
                        </ControlButton>
                      </Box>
                    </Box>
                  </CardContent>
                </VehicleControlSection>
              </Grid>

              {/* Status message */}
              {statusMessage && (
                <Grid item xs={12}>
                  <Box sx={{ 
                    mt: 2, 
                    p: 2, 
                    bgcolor: statusMessage.includes('Failed') ? 'error.dark' : 'success.dark',
                    borderRadius: 1
                  }}>
                    <Typography align="center">{statusMessage}</Typography>
                  </Box>
                </Grid>
              )}
            </Grid>
          </>
        )}
      </DashboardContainer>
    </Box>
  );
};

export default VehicleDashboard;
