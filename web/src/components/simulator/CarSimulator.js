import React, { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Grid, Paper } from '@mui/material';
import { styled } from '@mui/material/styles';
import CommandPanel from './CommandPanel';
import LogsPanel from './LogsPanel';
import VehicleMetrics from './VehicleMetrics';
// Remove simulated API imports
// import { simulateNotification, simulateCommandResponse } from './simulatorApi';
// Import real API functions
import { 
  fetchVehicleStatus, 
  subscribeToVehicleStatus, 
  updateVehicleStatus 
} from '../../api/status';
import { sendVehicleCommand } from '../../api/commands';

// Styled components
const SimulatorContainer = styled(Box)(({ theme }) => ({
  maxWidth: '1200px',
  margin: '0 auto',
  padding: theme.spacing(2),
}));

const Header = styled(Paper)(({ theme, isConnected }) => ({
  background: theme.palette.primary.main,
  color: 'white',
  padding: theme.spacing(2),
  borderRadius: `${theme.spacing(1)} ${theme.spacing(1)} 0 0`,
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
}));

const StatusIndicator = styled(Box)(({ theme, isConnected }) => ({
  display: 'flex',
  alignItems: 'center',
  backgroundColor: theme.palette.background.paper,
  padding: '5px 15px',
  borderRadius: '20px',
  color: theme.palette.text.primary,
  fontWeight: 'bold',
}));

const StatusDot = styled(Box)(({ theme, isConnected }) => ({
  width: '12px',
  height: '12px',
  borderRadius: '50%',
  backgroundColor: isConnected ? theme.palette.success.main : theme.palette.error.main,
  marginRight: theme.spacing(1),
  animation: isConnected ? 'pulse 2s infinite' : 'none',
  '@keyframes pulse': {
    '0%': { opacity: 1 },
    '50%': { opacity: 0.4 },
    '100%': { opacity: 1 },
  },
}));

const CarSimulator = ({ vehicleId }) => {
  // State
  const [isConnected, setIsConnected] = useState(true);
  const [logs, setLogs] = useState([]);
  const [vehicleStatus, setVehicleStatus] = useState({
    engineTemp: '56°C',
    speed: '0 km/h',
    batteryLevel: '82%',
    odometer: '12,456 km'
  });
  const [subscription, setSubscription] = useState(null);

  // Add log entry
  const addLog = useCallback((message, type) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prevLogs => [
      ...prevLogs,
      { message, type, timestamp }
    ]);
  }, []);

  // Toggle connection
  const toggleConnection = useCallback(() => {
    setIsConnected(prevState => {
      const newState = !prevState;
      addLog(
        newState ? 'Connection established with server' : 'Connection lost with server',
        newState ? 'success' : 'error'
      );
      
      if (newState && vehicleId) {
        // Connect to real-time updates
        initializeConnection();
      } else if (subscription) {
        // Disconnect from real-time updates
        subscription.unsubscribe();
        setSubscription(null);
      }
      
      return newState;
    });
  }, [addLog, vehicleId, subscription]);

  // Initialize connection and get vehicle status
  const initializeConnection = useCallback(async () => {
    if (!vehicleId) {
      addLog('No vehicle ID provided. Using simulator in demo mode.', 'warning');
      return;
    }
    
    try {
      // Fetch initial vehicle status
      addLog('Fetching vehicle status...', 'info');
      const initialStatus = await fetchVehicleStatus(vehicleId);
      
      // Format the data for display
      const formattedStatus = {
        engineTemp: `${initialStatus.Temperature}°C`,
        speed: `${initialStatus.Speed} km/h`,
        batteryLevel: `${initialStatus.Battery}%`,
        odometer: initialStatus.Odometer ? `${initialStatus.Odometer} km` : 'N/A'
      };
      
      setVehicleStatus(formattedStatus);
      addLog('Vehicle status received successfully', 'success');
      
      // Subscribe to real-time updates
      const newSubscription = await subscribeToVehicleStatus(
        vehicleId,
        (newStatus) => {
          // Update the status when changes are received
          const updatedStatus = {
            engineTemp: `${newStatus.Temperature}°C`,
            speed: `${newStatus.Speed} km/h`,
            batteryLevel: `${newStatus.Battery}%`,
            odometer: newStatus.Odometer ? `${newStatus.Odometer} km` : 'N/A'
          };
          
          setVehicleStatus(updatedStatus);
          addLog('Real-time status update received', 'info');
        },
        (error) => {
          addLog(`Subscription error: ${error.message}`, 'error');
        }
      );
      
      setSubscription(newSubscription);
      addLog('Real-time connection established', 'success');
    } catch (error) {
      addLog(`Failed to connect: ${error.message}`, 'error');
      setIsConnected(false);
    }
  }, [vehicleId, addLog]);

  // Handle command sending - using real API
  const handleSendCommand = useCallback(async (command, isCustom = false) => {
    if (!isConnected) {
      alert('Please connect to server first!');
      return;
    }

    const cmdText = isCustom ? `Custom command: ${command}` : `Command: ${command}`;
    addLog(`${cmdText} sent`, 'sent');

    try {
      // Use the real API to send commands
      if (vehicleId) {
        const response = await sendVehicleCommand(vehicleId, command, isCustom);
        addLog(`Server response: ${response.message || 'Command processed'}`, response.status || 'success');
        
        // If the command updated metrics, they'll come through the subscription
      } else {
        // Demo mode - simulate response after short delay
        setTimeout(() => {
          addLog(`Demo mode: Command would have been sent to the vehicle`, 'info');
        }, 500);
      }
    } catch (error) {
      addLog(`Command failed: ${error.message}`, 'error');
    }
  }, [isConnected, addLog, vehicleId]);

  // Initialize on component mount
  useEffect(() => {
    if (isConnected && vehicleId) {
      initializeConnection();
    } else {
      addLog('Simulator initialized in demo mode', 'info');
    }
    
    return () => {
      // Cleanup subscription when component unmounts
      if (subscription && typeof subscription.unsubscribe === 'function') {
        subscription.unsubscribe();
      }
    };
  }, [vehicleId, isConnected, initializeConnection]);

  return (
    <SimulatorContainer>
      <Header>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Box component="i" className="fas fa-car" sx={{ fontSize: '2rem', mr: 1 }} />
          <Typography variant="h5">
            Car Device Simulator
            {vehicleId && <Typography component="span" variant="subtitle1" sx={{ ml: 1 }}>
              (ID: {vehicleId})
            </Typography>}
          </Typography>
        </Box>
        <StatusIndicator>
          <StatusDot isConnected={isConnected} />
          <span>{isConnected ? 'CONNECTED' : 'DISCONNECTED'}</span>
        </StatusIndicator>
      </Header>
      
      <Grid container spacing={2} sx={{ mt: 2 }}>
        <Grid item xs={12} md={6}>
          <CommandPanel 
            onSendCommand={handleSendCommand} 
            isConnected={isConnected}
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <LogsPanel 
            logs={logs} 
            isConnected={isConnected} 
            onToggleConnection={toggleConnection}
          />
        </Grid>
        <Grid item xs={12}>
          <VehicleMetrics vehicleStatus={vehicleStatus} />
        </Grid>
      </Grid>
    </SimulatorContainer>
  );
};

export default CarSimulator;
