import React, { useState, useEffect } from 'react';
import { Box, Typography, CircularProgress, Grid } from '@mui/material';
import { Battery90, Thermostat, Speed, LocalGasStation } from '@mui/icons-material';
import { fetchVehicleStatus, subscribeToVehicleStatus } from '../api/status';

const StatusGauge = ({ value, max, icon, label, color }) => {
  // Calculate progress value and use it in the component styling
  const progressValue = Math.min(100, Math.max(0, (value / max) * 100));
  
  return (
    <Box className="gauge-container" sx={{ 
      position: 'relative',
      textAlign: 'center',
      // Use progressValue to add a visual indicator of the gauge value
      background: `radial-gradient(circle closest-side, white 79%, transparent 80% 100%), 
                  conic-gradient(${color} ${progressValue}%, #e0e0e0 0)`,
      borderRadius: '50%',
      width: '120px',
      height: '120px',
      margin: '0 auto',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center'
    }}>
      {icon}
      <Typography variant="h5" color={color}>
        {value}{label === 'Speed' ? ' km/h' : '%'}
      </Typography>
      <Typography className="gauge-label">
        {label}
      </Typography>
    </Box>
  );
};

const CarStatus = ({ vehicleId }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [, setError] = useState(null);

  useEffect(() => {
    let subscription = null;
    
    const initializeStatus = async () => {
      try {
        setLoading(true);
        // Get initial data
        const initialData = await fetchVehicleStatus(vehicleId);
        setStatus(initialData);
        
        // Start the real-time subscription to Cosmos DB Change Feed
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
    
    // Cleanup: close subscription when component unmounts
    return () => {
      if (subscription) {
        subscription.unsubscribe();
      }
    };
  }, [vehicleId]);

  if (loading && !status) {
    return <CircularProgress />;
  }

  return (
    <>
      <Typography variant="h6" component="h2" gutterBottom>
        Car Status
      </Typography>
      {status && (
        <Grid container spacing={2}>
          <Grid item xs={6} md={3}>
            <StatusGauge 
              value={status.Battery} 
              max={100} 
              icon={<Battery90 color="primary" fontSize="large" />} 
              label="Battery" 
              color="primary" 
            />
          </Grid>
          <Grid item xs={6} md={3}>
            <StatusGauge 
              value={status.Temperature} 
              max={100} 
              icon={<Thermostat color="secondary" fontSize="large" />} 
              label="Temperature" 
              color="secondary" 
            />
          </Grid>
          <Grid item xs={6} md={3}>
            <StatusGauge 
              value={status.Speed} 
              max={200} 
              icon={<Speed color="action" fontSize="large" />} 
              label="Speed" 
              color="text.primary" 
            />
          </Grid>
          <Grid item xs={6} md={3}>
            <StatusGauge 
              value={status.OilRemaining} 
              max={100} 
              icon={<LocalGasStation color="success" fontSize="large" />} 
              label="Oil" 
              color="success" 
            />
          </Grid>
        </Grid>
      )}
    </>
  );
};

export default CarStatus;
