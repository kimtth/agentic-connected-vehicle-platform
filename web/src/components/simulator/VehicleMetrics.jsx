import { Paper, Typography, Grid, Box, CircularProgress } from '@mui/material';
import { styled } from '@mui/material/styles';
import { 
  Thermostat, SpeedOutlined, BatteryChargingFullOutlined, Timeline 
} from '@mui/icons-material';

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(1),
  backgroundColor: theme.palette.background.paper,
}));

const MetricCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(1),
  display: 'flex',
  alignItems: 'center',
  background: theme.palette.mode === 'dark'
    ? 'linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.03))'
    : theme.palette.action.hover,
  border: `1px solid ${theme.palette.divider}`,
  boxShadow: '0 2px 4px rgba(0, 0, 0, 0.05)',
  borderRadius: theme.shape.borderRadius,
}));

const IconWrapper = styled(Box)(({ theme }) => ({
  fontSize: '1.5rem',
  marginRight: theme.spacing(1),
  color: theme.palette.primary.main,
}));

// Simplified: payload already provides raw numbers
const num = (v) => {
  if (v === 0) return 0;
  return (v === undefined || v === null) ? null : (typeof v === 'number' ? v : (isNaN(Number(v)) ? null : Number(v)));
};

const VehicleMetrics = ({ vehicleStatus, loading = false }) => {
  const engineTempValue = num(vehicleStatus?.engineTemp);
  const speedValue = num(vehicleStatus?.speed);
  const batteryValue = num(vehicleStatus?.battery); // removed batteryLevel fallback
  const odometerValue = num(vehicleStatus?.odometer);
  const cabinTempValue = num(vehicleStatus?.temperature); 
  const oilRemainingValue = num(vehicleStatus?.oilRemaining); 

  const engineColor = engineTempValue == null
    ? 'primary.main'
    : engineTempValue >= 100
      ? 'error.main'
      : engineTempValue >= 90
        ? 'warning.main'
        : 'primary.main';

  const metrics = [
    { 
      label: 'Engine Temperature',
      value: engineTempValue != null ? `${engineTempValue}°C` : 'N/A',
      icon: <Thermostat fontSize="large" />,
      color: engineColor
    },
    { 
      label: 'Cabin Temperature',
      value: cabinTempValue != null ? `${cabinTempValue}°C` : 'N/A',
      icon: <Thermostat fontSize="large" />,
      color: 'primary.main'
    },
    { 
      label: 'Speed',
      value: speedValue != null ? `${speedValue} km/h` : 'N/A',
      icon: <SpeedOutlined fontSize="large" />,
      color: 'primary.main'
    },
    { 
      label: 'Battery Level',
      value: batteryValue != null ? `${batteryValue}%` : 'N/A',
      icon: <BatteryChargingFullOutlined fontSize="large" />,
      color: 'primary.main'
    },
    { 
      label: 'Oil Remaining',
      value: oilRemainingValue != null ? `${oilRemainingValue}%` : 'N/A',
      icon: <Timeline fontSize="large" />,
      color: 'primary.main'
    },
    { 
      label: 'Odometer',
      value: odometerValue != null ? `${odometerValue} km` : 'N/A',
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
                <Typography variant="caption" color="text.secondary">
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
 