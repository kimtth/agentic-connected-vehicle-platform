import React from 'react';
import { Paper, Typography, Grid, Box, CircularProgress } from '@mui/material';
import { styled } from '@mui/material/styles';
import { 
  Speed, LocalGasStation, Battery90, Thermostat,
  SpeedOutlined, BatteryChargingFullOutlined, 
  DeviceThermostat, Timeline 
} from '@mui/icons-material';

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(1),
  backgroundColor: theme.palette.background.paper,
}));

const MetricCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(1),
  display: 'flex',
  alignItems: 'center',
  backgroundColor: theme.palette.action.hover,
  boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
  borderRadius: theme.shape.borderRadius,
}));

const IconWrapper = styled(Box)(({ theme }) => ({
  fontSize: '1.5rem',
  marginRight: theme.spacing(1),
  color: theme.palette.primary.main,
}));

const VehicleMetrics = ({ vehicleStatus, loading = false }) => {
  const metrics = [
    { 
      label: 'Engine Temperature', 
      value: vehicleStatus?.engineTemp || 'N/A',
      icon: <Thermostat fontSize="large" />, 
      color: vehicleStatus?.engineTemp?.includes('85') ? 'error.main' : 'primary.main'
    },
    { 
      label: 'Speed', 
      value: vehicleStatus?.speed || 'N/A',
      icon: <SpeedOutlined fontSize="large" />, 
      color: 'primary.main'
    },
    { 
      label: 'Battery Level', 
      value: vehicleStatus?.batteryLevel || 'N/A',
      icon: <BatteryChargingFullOutlined fontSize="large" />, 
      color: 'primary.main'
    },
    { 
      label: 'Odometer', 
      value: vehicleStatus?.odometer || 'N/A',
      icon: <Timeline fontSize="large" />, 
      color: 'primary.main'
    }
  ];

  if (loading) {
    return (
      <StyledPaper elevation={3} sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '120px' }}>
        <CircularProgress />
      </StyledPaper>
    );
  }

  return (
    <StyledPaper elevation={3}>
      <Typography variant="subtitle1" gutterBottom sx={{ mb: 1 }}>
        <Box component="i" className="fas fa-tachometer-alt" sx={{ mr: 1 }} />
        Vehicle Status
      </Typography>
      
      <Grid container spacing={1}>
        {metrics.map((metric, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <MetricCard>
              <IconWrapper>
                <Box sx={{ color: metric.color }}>
                  {metric.icon}
                </Box>
              </IconWrapper>
              <Box>
                <Typography variant="caption" color="textSecondary">
                  {metric.label}
                </Typography>
                <Typography variant="subtitle2">
                  {metric.value}
                </Typography>
              </Box>
            </MetricCard>
          </Grid>
        ))}
      </Grid>
    </StyledPaper>
  );
};

export default VehicleMetrics;
