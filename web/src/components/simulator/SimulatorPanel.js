import { useState, useEffect, useCallback } from 'react';
import { Box, Typography, Grid, Paper } from '@mui/material';
import { styled } from '@mui/material/styles';
import CommandPanel from './CommandPanel';
import LogsPanel from './LogsPanel';
import VehicleMetrics from './VehicleMetrics';
import { 
  fetchVehicleStatus, 
  subscribeToVehicleStatus, 
} from '../../api/status';
import { sendVehicleCommand } from '../../api/commands';
import { INTERVALS, createVehicleStatusThrottle } from '../../config/intervals';

// Styled components
const SimulatorContainer = styled(Box)(({ theme }) => ({
  maxWidth: '1600px',
  margin: '0 auto',
  padding: 0,
  height: 'calc(100vh - 120px)',
}));

const Header = styled(Paper)(({ theme }) => ({
  background: theme.palette.primary.main,
  color: 'white',
  padding: theme.spacing(1.5),
  borderRadius: 0,
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  flexShrink: 0,
}));

const StatusIndicator = styled(Box)(({ theme }) => ({
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

const SimulatorPanel = ({ vehicleId }) => {
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
  const [statusCheckInterval, setStatusCheckInterval] = useState(null);
  const [isInitializing, setIsInitializing] = useState(false);
  const [isMounted, setIsMounted] = useState(true);

  // Add log entry
  const addLog = useCallback((message, type) => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs(prevLogs => [
      ...prevLogs,
      { message, type, timestamp }
    ]);
  }, []);

  // Status check function with throttling
  const performStatusCheck = useCallback(async () => {
    if (!vehicleId || !isConnected || !isMounted) return;
    
    try {
      // Only make the call if throttling allows it
      if (createVehicleStatusThrottle(vehicleId)) {
        addLog('Performing status check...', 'info');
        const status = await fetchVehicleStatus(vehicleId);
        
        if (isMounted) {
          const formattedStatus = {
            engineTemp: `${status.Temperature}°C`,
            speed: `${status.Speed} km/h`,
            batteryLevel: `${status.Battery}%`,
            odometer: status.Odometer ? `${status.Odometer} km` : 'N/A'
          };
          
          setVehicleStatus(formattedStatus);
          addLog('Status check completed successfully', 'success');
        }
      }
    } catch (error) {
      if (isMounted) {
        addLog(`Status check failed: ${error.message}`, 'error');
      }
    }
  }, [vehicleId, isConnected, addLog, isMounted]);

  // Enhanced cleanup function
  const cleanup = useCallback(() => {
    // Clean up subscription
    if (subscription) {
      try {
        if (typeof subscription.unsubscribe === 'function') {
          subscription.unsubscribe();
        } else if (typeof subscription.close === 'function') {
          subscription.close();
        }
        if (isMounted) {
          addLog('Subscription cleaned up', 'info');
        }
      } catch (error) {
        if (isMounted) {
          addLog(`Cleanup warning: ${error.message}`, 'warning');
        }
      }
      setSubscription(null);
    }
    
    // Clean up status check interval
    if (statusCheckInterval) {
      clearInterval(statusCheckInterval);
      setStatusCheckInterval(null);
      if (isMounted) {
        addLog('Status check interval cleaned up', 'info');
      }
    }
  }, [subscription, statusCheckInterval, addLog, isMounted]);

  // Initialize connection and get vehicle status
  const initializeConnection = useCallback(async () => {
    if (!vehicleId || !isMounted) {
      if (isMounted) {
        addLog('No vehicle ID provided. Using simulator in demo mode.', 'warning');
      }
      return;
    }
    
    if (isInitializing) {
      if (isMounted) {
        addLog('Initialization already in progress...', 'warning');
      }
      return;
    }
    
    setIsInitializing(true);
    
    try {
      // Clean up any existing connections first
      cleanup();
      
      // Fetch initial vehicle status with throttling
      if (createVehicleStatusThrottle(vehicleId)) {
        addLog('Fetching vehicle status...', 'info');
        const initialStatus = await fetchVehicleStatus(vehicleId);
        
        if (isMounted) {
          // Format the data for display
          const formattedStatus = {
            engineTemp: `${initialStatus.Temperature}°C`,
            speed: `${initialStatus.Speed} km/h`,
            batteryLevel: `${initialStatus.Battery}%`,
            odometer: initialStatus.Odometer ? `${initialStatus.Odometer} km` : 'N/A'
          };
          
          setVehicleStatus(formattedStatus);
          addLog('Vehicle status received successfully', 'success');
        }
      }
      
      // Subscribe to real-time updates
      try {
        const newSubscription = await subscribeToVehicleStatus(
          vehicleId,
          (newStatus) => {
            if (isMounted) {
              // Update the status when changes are received
              const updatedStatus = {
                engineTemp: `${newStatus.Temperature}°C`,
                speed: `${newStatus.Speed} km/h`,
                batteryLevel: `${newStatus.Battery}%`,
                odometer: newStatus.Odometer ? `${newStatus.Odometer} km` : 'N/A'
              };
              
              setVehicleStatus(updatedStatus);
              addLog('Real-time status update received', 'info');
            }
          },
          (error) => {
            if (isMounted) {
              addLog(`Subscription error: ${error.message}`, 'error');
            }
          }
        );
        
        if (isMounted) {
          setSubscription(newSubscription);
          addLog('Real-time connection established', 'success');
        }
      } catch (subscriptionError) {
        if (isMounted) {
          addLog(`Failed to establish real-time connection: ${subscriptionError.message}`, 'warning');
        }
      }

      // Start status check interval using centralized configuration
      const interval = setInterval(performStatusCheck, INTERVALS.SIMULATOR_STATUS_CHECK);
      setStatusCheckInterval(interval);
      if (isMounted) {
        addLog(`Status check interval started (${INTERVALS.SIMULATOR_STATUS_CHECK / 1000} seconds)`, 'info');
      }
      
    } catch (error) {
      if (isMounted) {
        addLog(`Failed to connect: ${error.message}`, 'error');
        setIsConnected(false);
      }
    } finally {
      if (isMounted) {
        setIsInitializing(false);
      }
    }
  }, [vehicleId, addLog, performStatusCheck, cleanup, isInitializing, isMounted]);

  // Initialize on component mount
  useEffect(() => {
    setIsMounted(true);
    
    if (isConnected && vehicleId) {
      initializeConnection();
    } else {
      addLog('Simulator initialized in demo mode', 'info');
    }
    
    // Return cleanup function
    return () => {
      setIsMounted(false);
      cleanup();
    };
  }, [vehicleId, isConnected]); // Remove other dependencies to prevent recreating

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
      } else {
        // Disconnect from real-time updates
        cleanup();
      }
      
      return newState;
    });
  }, [addLog, vehicleId, initializeConnection, cleanup]);

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

  return (
    <SimulatorContainer>
      <Header>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Box component="i" className="fas fa-car" sx={{ fontSize: '1.5rem', mr: 1 }} />
          <Typography variant="h6">
            Car Device Simulator
            {vehicleId && <Typography component="span" variant="subtitle2" sx={{ ml: 1 }}>
              (ID: {vehicleId})
            </Typography>}
          </Typography>
        </Box>
        <StatusIndicator>
          <StatusDot isConnected={isConnected} />
          <span>{isConnected ? 'CONNECTED' : 'DISCONNECTED'}</span>
        </StatusIndicator>
      </Header>
      
      <Box sx={{ p: { xs: 1, md: 2, lg: 3 }, height: 'calc(100% - 80px)', overflow: 'hidden' }}>
        <Grid container spacing={{ xs: 1, md: 2, lg: 3 }} sx={{ height: '100%' }}>
          <Grid item xs={12} lg={6} sx={{ height: { xs: 'auto', lg: '70%' } }}>
            <CommandPanel 
              onSendCommand={handleSendCommand} 
              isConnected={isConnected}
              vehicleId={vehicleId}
            />
          </Grid>
          <Grid item xs={12} lg={6} sx={{ height: { xs: 'auto', lg: '70%' } }}>
            <LogsPanel 
              logs={logs} 
              isConnected={isConnected} 
              onToggleConnection={toggleConnection}
              vehicleId={vehicleId}
            />
          </Grid>
          <Grid item xs={12} sx={{ height: { xs: 'auto', lg: '30%' } }}>
            <VehicleMetrics vehicleStatus={vehicleStatus} />
          </Grid>
        </Grid>
      </Box>
    </SimulatorContainer>
  );
};

export default SimulatorPanel;
