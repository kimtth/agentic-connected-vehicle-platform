import React, { useState } from 'react';
import { 
  Paper, Typography, Grid, Button, TextField, Box 
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { 
  Lock, LockOpen, PowerSettingsNew, Stop, 
  DirectionsCar, Lightbulb, Warning 
} from '@mui/icons-material';
import { sendVehicleCommand } from '../../api/commands';

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  height: '100%',
  backgroundColor: theme.palette.background.paper,
}));

const CommandButton = styled(Button)(({ theme, emergency }) => ({
  width: '100%',
  textAlign: 'left',
  justifyContent: 'flex-start',
  padding: theme.spacing(1.5),
  backgroundColor: emergency ? theme.palette.error.main : theme.palette.action.hover,
  color: emergency ? theme.palette.error.contrastText : theme.palette.text.primary,
  '&:hover': {
    backgroundColor: emergency 
      ? theme.palette.error.dark 
      : theme.palette.primary.main,
    color: theme.palette.primary.contrastText,
    transform: 'translateY(-2px)',
    boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)'
  }
}));

const CustomCommandSection = styled(Box)(({ theme }) => ({
  marginTop: theme.spacing(2)
}));

const CommandPanel = ({ onSendCommand, isConnected, vehicleId }) => {
  const [customCommand, setCustomCommand] = useState('');
  const [isSending, setIsSending] = useState(false);

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

  // Define commands with their icons and labels
  const commandButtons = [
    { command: 'LOCK', icon: <Lock />, label: 'Lock Doors' },
    { command: 'UNLOCK', icon: <LockOpen />, label: 'Unlock Doors' },
    { command: 'START', icon: <PowerSettingsNew />, label: 'Start Engine' },
    { command: 'STOP', icon: <Stop />, label: 'Stop Engine' },
    { command: 'TRUNK_OPEN', icon: <DirectionsCar />, label: 'Open Trunk' },
    { command: 'TRUNK_CLOSE', icon: <DirectionsCar />, label: 'Close Trunk' },
    { command: 'LIGHTS_ON', icon: <Lightbulb />, label: 'Lights On' },
    { command: 'LIGHTS_OFF', icon: <Lightbulb />, label: 'Lights Off' }
  ];

  return (
    <StyledPaper elevation={3}>
      <Typography variant="h6" gutterBottom>
        <Box component="i" className="fas fa-terminal" sx={{ mr: 1 }} />
        Send Commands
      </Typography>
      
      <Grid container spacing={1}>
        {commandButtons.map(({ command, icon, label }) => (
          <Grid item xs={6} key={command}>
            <CommandButton
              variant="contained"
              startIcon={icon}
              onClick={() => handleSendCommand(command)}
              disabled={!isConnected || isSending}
            >
              {label}
            </CommandButton>
          </Grid>
        ))}
        
        <Grid item xs={12}>
          <CommandButton
            variant="contained"
            startIcon={<Warning />}
            onClick={() => onSendCommand('SOS')}
            emergency={true}
            disabled={!isConnected}
          >
            EMERGENCY SOS
          </CommandButton>
        </Grid>
      </Grid>
      
      <CustomCommandSection>
        <Typography variant="subtitle1" gutterBottom>
          <Box component="i" className="fas fa-code" sx={{ mr: 1 }} />
          Custom Command
        </Typography>
        <TextField
          fullWidth
          multiline
          rows={3}
          placeholder="Enter your custom command here..."
          value={customCommand}
          onChange={(e) => setCustomCommand(e.target.value)}
          margin="normal"
          variant="outlined"
        />
        <Button
          fullWidth
          variant="contained"
          color="primary"
          onClick={handleCustomCommand}
          disabled={!isConnected}
          sx={{ mt: 1 }}
        >
          <Box component="i" className="fas fa-paper-plane" sx={{ mr: 1 }} />
          Send Custom Command
        </Button>
      </CustomCommandSection>
    </StyledPaper>
  );
};

export default CommandPanel;
