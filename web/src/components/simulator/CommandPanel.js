import { useState } from 'react';
import { 
  Paper, Typography, Grid, Button, TextField, Box 
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { 
  Lock, LockOpen, PowerSettingsNew, Stop, 
  DirectionsCar, Lightbulb, Warning, AcUnit, WbSunny,
  KeyboardArrowUp, KeyboardArrowDown, LocalHospital,
  BatteryChargingFull, Navigation
} from '@mui/icons-material';

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  height: '100%',
  backgroundColor: theme.palette.background.paper,
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
}));

const CommandButton = styled(Button)(({ theme }) => ({
  width: '100%',
  textAlign: 'left',
  justifyContent: 'flex-start',
  padding: theme.spacing(1.5),
  backgroundColor: theme.palette.action.hover,
  color: theme.palette.text.primary,
  '&:hover': {
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.primary.contrastText,
    transform: 'translateY(-2px)',
    boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)'
  }
}));

const EmergencyCommandButton = styled(Button)(({ theme }) => ({
  width: '100%',
  textAlign: 'left',
  justifyContent: 'flex-start',
  padding: theme.spacing(1.5),
  backgroundColor: theme.palette.error.main,
  color: theme.palette.error.contrastText,
  '&:hover': {
    backgroundColor: theme.palette.error.dark,
    transform: 'translateY(-2px)',
    boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)'
  }
}));

const EmergencyButton = styled(Button)(({ theme }) => ({
  backgroundColor: theme.palette.error.main,
  color: 'white',
  '&:hover': {
    backgroundColor: theme.palette.error.dark,
  },
  fontWeight: 'bold',
  minHeight: '48px',
}));

const CustomCommandSection = styled(Box)(({ theme }) => ({
  marginTop: theme.spacing(1),
  flexShrink: 0,
}));

const ScrollableContent = styled(Box)(({ theme }) => ({
  flex: 1,
  overflowY: 'auto',
  marginBottom: theme.spacing(1),
}));

const CommandPanel = ({ onSendCommand, isConnected, vehicleId }) => {
  const [customCommand, setCustomCommand] = useState('');
  const [isSending, setIsSending] = useState(false);
  const selectedCategory = 'vehicle_features';

  const handleSendCommand = async (command) => {
    if (!isConnected) {
      alert('Please connect to server first!');
      return;
    }
    
    setIsSending(true);
    try {
      await onSendCommand(command);
    } finally {
      setIsSending(false);
    }
  };

  const handleCustomCommand = async () => {
    if (customCommand.trim()) {
      setIsSending(true);
      try {
        await onSendCommand(customCommand, true);
        setCustomCommand('');
      } finally {
        setIsSending(false);
      }
    } else {
      alert('Please enter a command');
    }
  };

  const handleEmergencyCommand = async (command) => {
    if (!isConnected) {
      alert('Please connect to server first!');
      return;
    }
    
    setIsSending(true);
    try {
      await onSendCommand(command);
    } finally {
      setIsSending(false);
    }
  };

  // Enhanced command categories
  const commandCategories = {
    vehicle_features: {
      title: 'Vehicle Features',
      icon: <DirectionsCar />,
      commands: [
        { command: 'LIGHTS_ON', icon: <Lightbulb />, label: 'Turn On Headlights', params: { light_type: 'headlights' } },
        { command: 'LIGHTS_OFF', icon: <Lightbulb />, label: 'Turn Off Headlights', params: { light_type: 'headlights' } },
        { command: 'CLIMATE_CONTROL', icon: <AcUnit />, label: 'Set Climate 20°C', params: { temperature: 20, action: 'cooling' } },
        { command: 'CLIMATE_CONTROL', icon: <WbSunny />, label: 'Set Climate 26°C', params: { temperature: 26, action: 'heating' } },
        { command: 'WINDOWS_UP', icon: <KeyboardArrowUp />, label: 'Windows Up', params: { windows: 'all' } },
        { command: 'WINDOWS_DOWN', icon: <KeyboardArrowDown />, label: 'Windows Down', params: { windows: 'all' } }
      ]
    },
    remote_access: {
      title: 'Remote Access',
      icon: <Lock />,
      commands: [
        { command: 'LOCK_DOORS', icon: <Lock />, label: 'Lock Doors', params: { doors: 'all' } },
        { command: 'UNLOCK_DOORS', icon: <LockOpen />, label: 'Unlock Doors', params: { doors: 'all' } },
        { command: 'START_ENGINE', icon: <PowerSettingsNew />, label: 'Start Engine', params: { remote: true } },
        { command: 'STOP_ENGINE', icon: <Stop />, label: 'Stop Engine', params: { remote: true } },
        { command: 'HORN_LIGHTS', icon: <Warning />, label: 'Horn & Lights', params: { duration: 10 } }
      ]
    },
    emergency: {
      title: 'Emergency & Safety',
      icon: <LocalHospital />,
      emergency: true,
      commands: [
        { command: 'SOS_REQUEST', icon: <LocalHospital />, label: 'SOS Emergency', params: { priority: 'critical' } },
        { command: 'EMERGENCY_CALL', icon: <LocalHospital />, label: 'Emergency Call', params: { call_type: 'manual' } },
        { command: 'COLLISION_ALERT', icon: <Warning />, label: 'Report Collision', params: { severity: 'minor' } },
        { command: 'THEFT_NOTIFICATION', icon: <Warning />, label: 'Report Theft', params: { reported_by: 'owner' } }
      ]
    },
    charging: {
      title: 'Charging & Energy',
      icon: <BatteryChargingFull />,
      commands: [
        { command: 'START_CHARGING', icon: <BatteryChargingFull />, label: 'Start Charging', params: {} },
        { command: 'STOP_CHARGING', icon: <Stop />, label: 'Stop Charging', params: {} },
        { command: 'SET_CHARGING_SCHEDULE', icon: <BatteryChargingFull />, label: 'Set Charge Schedule', 
          params: { schedule: { start_time: '22:00', end_time: '06:00' } } }
      ]
    },
    information: {
      title: 'Information & Navigation',
      icon: <Navigation />,
      commands: [
        { command: 'GET_WEATHER', icon: <Navigation />, label: 'Get Weather Info', params: {} },
        { command: 'FIND_CHARGING_STATIONS', icon: <BatteryChargingFull />, label: 'Find Charging Stations', params: {} },
        { command: 'GET_TRAFFIC', icon: <Navigation />, label: 'Traffic Information', params: {} },
        { command: 'FIND_POI', icon: <Navigation />, label: 'Find Points of Interest', params: { category: 'restaurant' } }
      ]
    }
  };

  const emergencyCommands = [
    { label: 'Emergency Stop', command: 'EMERGENCY_STOP' },
    { label: 'Emergency Brake', command: 'EMERGENCY_BRAKE' },
    { label: 'Hazard Lights On', command: 'HAZARD_ON' },
    { label: 'Call Emergency', command: 'CALL_911' }
  ];

  const isEmergencyCategory = commandCategories[selectedCategory]?.emergency;

  return (
    <StyledPaper elevation={3}>
      <Typography variant="h6" gutterBottom sx={{ flexShrink: 0 }}>
        <Box component="i" className="fas fa-terminal" sx={{ mr: 1 }} />
        Send Commands
      </Typography>
      
      <ScrollableContent>
        <Grid container spacing={1}>
          {commandCategories[selectedCategory]?.commands.map((cmd, index) => (
            <Grid item xs={12} sm={6} key={index}>
              {isEmergencyCategory ? (
                <EmergencyCommandButton
                  startIcon={cmd.icon}
                  onClick={() => handleSendCommand(`${cmd.command}:${JSON.stringify(cmd.params)}`)}
                  disabled={isSending || !isConnected}
                  fullWidth
                >
                  {cmd.label}
                </EmergencyCommandButton>
              ) : (
                <CommandButton
                  startIcon={cmd.icon}
                  onClick={() => handleSendCommand(`${cmd.command}:${JSON.stringify(cmd.params)}`)}
                  disabled={isSending || !isConnected}
                  fullWidth
                >
                  {cmd.label}
                </CommandButton>
              )}
            </Grid>
          ))}
          
          <Grid item xs={12}>
            <EmergencyCommandButton
              startIcon={<Warning />}
              onClick={() => onSendCommand('SOS')}
              disabled={!isConnected}
              fullWidth
            >
              EMERGENCY SOS
            </EmergencyCommandButton>
          </Grid>
        </Grid>

        {/* Emergency Commands Section */}
        <Box sx={{ mb: 2, mt: 1 }}>
          <Typography variant="subtitle2" gutterBottom color="error">
            Emergency Commands
          </Typography>
          <Grid container spacing={1}>
            {emergencyCommands.map((cmd) => (
              <Grid item xs={6} key={cmd.command}>
                <EmergencyButton
                  fullWidth
                  size="small"
                  onClick={() => handleEmergencyCommand(cmd.command)}
                  disabled={!isConnected}
                >
                  {cmd.label}
                </EmergencyButton>
              </Grid>
            ))}
          </Grid>
        </Box>
      </ScrollableContent>
      
      <CustomCommandSection>
        <Typography variant="subtitle2" gutterBottom>
          <Box component="i" className="fas fa-code" sx={{ mr: 1 }} />
          Custom Command
        </Typography>
        <TextField
          fullWidth
          multiline
          rows={2}
          placeholder="Enter custom command..."
          value={customCommand}
          onChange={(e) => setCustomCommand(e.target.value)}
          margin="dense"
          variant="outlined"
          size="small"
        />
        <Button
          fullWidth
          variant="contained"
          color="primary"
          onClick={handleCustomCommand}
          disabled={!isConnected || isSending}
          sx={{ mt: 0.5 }}
          size="small"
          startIcon={<Box component="i" className="fas fa-paper-plane" />}
        >
          Send Custom Command
        </Button>

        {vehicleId && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
            Target: Vehicle {vehicleId}
          </Typography>
        )}
      </CustomCommandSection>
    </StyledPaper>
  );
};

export default CommandPanel;
