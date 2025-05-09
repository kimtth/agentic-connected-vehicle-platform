import React, { useState, useEffect } from 'react';
// eslint-disable-next-line no-unused-vars
import { Paper, Switch, FormControlLabel } from '@mui/material';
// eslint-disable-next-line no-unused-vars
import Navigation from '@mui/icons-material/Navigation';
// eslint-disable-next-line no-unused-vars
import Brightness6 from '@mui/icons-material/Brightness6';
import { 
  Box, Typography, Grid, Slider, Button, Card, CardContent, CircularProgress
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { 
  Speed, LocalGasStation, Battery90, Thermostat, 
  AcUnit, WbSunny, VolumeUp, BluetoothAudio, DirectionsCar, 
  Sync, DeviceThermostat
} from '@mui/icons-material';
import { fetchVehicleStatus, subscribeToVehicleStatus } from '../api/status';

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

const VehicleDashboard = ({ vehicleId }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [temperature, setTemperature] = useState(22);
  const [fanSpeed, setFanSpeed] = useState(2);
  const [acOn, setAcOn] = useState(true);
  const [mediaVolume, setMediaVolume] = useState(60);
  const [lightIntensity, setLightIntensity] = useState(0);

  useEffect(() => {
    let subscription = null;
    
    const initializeStatus = async () => {
      try {
        setLoading(true);
        // Get initial data
        const initialData = await fetchVehicleStatus(vehicleId);
        setStatus(initialData);
        
        // Start the real-time subscription
        subscription = await subscribeToVehicleStatus(vehicleId, (newStatus) => {
          setStatus(newStatus);
          setError(null);
        }, (err) => {
          setError('Error with real-time connection: ' + err.message);
          console.error('Subscription error:', err);
        });
      } catch (err) {
        setError('Error loading vehicle status');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    initializeStatus();
    
    // Cleanup subscription when component unmounts
    return () => {
      if (subscription) {
        subscription.unsubscribe();
      }
    };
  }, [vehicleId]);

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
        <Typography color="error">{error}</Typography>
      </DashboardContainer>
    );
  }

  return (
    <DashboardContainer>
      <Typography variant="h4" gutterBottom sx={{ textAlign: 'center', color: '#1976d2' }}>
        Vehicle Dashboard
      </Typography>
      
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
          </Grid>
        </>
      )}
    </DashboardContainer>
  );
};

export default VehicleDashboard;
