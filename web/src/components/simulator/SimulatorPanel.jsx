import { useState, useEffect, useCallback, useRef } from 'react';
import { Car } from 'lucide-react';
import CommandPanel from './CommandPanel';
import LogsPanel from './LogsPanel';
import VehicleMetrics from './VehicleMetrics';
import { 
  fetchVehicleStatus, 
  subscribeToVehicleStatus, 
} from '../../api/status';
import { sendVehicleCommand } from '../../api/commands';
import { INTERVALS, createVehicleStatusThrottle } from '../../config/intervals';

const SimulatorPanel = ({ vehicleId }) => {
  // State
  const [isConnected, setIsConnected] = useState(true);
  const [logs, setLogs] = useState([]);
  const [vehicleStatus, setVehicleStatus] = useState({
    engineTemp: null,
    temperature: null,
    speed: null,
    battery: null,
    oilRemaining: null,
    odometer: null,
    timestamp: null,
  });
  const [subscription, setSubscription] = useState(null);
  const [statusCheckInterval, setStatusCheckInterval] = useState(null);
  const [isInitializing, setIsInitializing] = useState(false);
  const [isMounted, setIsMounted] = useState(true);

  // Prevent duplicate "Real-time status update received" spam
  const lastStatusRef = useRef(null);
  const lastRealtimeLogTsRef = useRef(0);

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
          // Store raw numeric payload directly
          setVehicleStatus({
            engineTemp: status.engineTemp,
            temperature: status.temperature,
            speed: status.speed,
            battery: status.battery,
            oilRemaining: status.oilRemaining,
            odometer: status.odometer,
            timestamp: status.timestamp,
          });
          addLog('Status check completed successfully', 'success');
        }
      }
    } catch (error) {
      if (isMounted) addLog(`Status check failed: ${error.message}`, 'error');
    }
  }, [vehicleId, isConnected, addLog, isMounted]);

  // Enhanced cleanup function
  const cleanup = useCallback(() => {
    if (subscription) {
      try {
        // subscription is now a cleanup function
        subscription();
        if (isMounted) addLog('Subscription cleaned up', 'info');
      } catch (e) {
        if (isMounted) addLog(`Cleanup warning: ${e.message}`, 'warning');
      }
      setSubscription(null);
    }
    if (statusCheckInterval) {
      clearInterval(statusCheckInterval);
      setStatusCheckInterval(null);
      if (isMounted) addLog('Status check interval cleaned up', 'info');
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
          setVehicleStatus({
            engineTemp: initialStatus.engineTemp,
            temperature: initialStatus.temperature,
            speed: initialStatus.speed,
            battery: initialStatus.battery,
            oilRemaining: initialStatus.oilRemaining,
            odometer: initialStatus.odometer,
            timestamp: initialStatus.timestamp,
          });
          addLog('Vehicle status received successfully', 'success');
        }
      }
      
      // Subscribe to real-time updates
      try {
        const newSubscription = await subscribeToVehicleStatus(
          vehicleId,
          (newStatus) => {
            if (isMounted) {
              const prev = lastStatusRef.current;
              const fields = ['engineTemp','temperature','speed','battery','oilRemaining','odometer'];
              const hasChange = !prev || fields.some(k => prev[k] !== newStatus[k]);
              if (hasChange) {
                setVehicleStatus({
                  engineTemp: newStatus.engineTemp,
                  temperature: newStatus.temperature,
                  speed: newStatus.speed,
                  battery: newStatus.battery,
                  oilRemaining: newStatus.oilRemaining,
                  odometer: newStatus.odometer,
                  timestamp: newStatus.timestamp,
                });
                // cache snapshot
                lastStatusRef.current = {
                  engineTemp: newStatus.engineTemp,
                  temperature: newStatus.temperature,
                  speed: newStatus.speed,
                  battery: newStatus.battery,
                  oilRemaining: newStatus.oilRemaining,
                  odometer: newStatus.odometer,
                  timestamp: newStatus.timestamp,
                };
                const now = Date.now();
                if (now - lastRealtimeLogTsRef.current > 3000) { // throttle to 1 log / 3s
                  addLog('Real-time status update received', 'info');
                  lastRealtimeLogTsRef.current = now;
                }
              }
            }
          },
          (error) => {
            if (isMounted) addLog(`Subscription error: ${error.message}`, 'error');
          }
        );
        if (isMounted) {
          setSubscription(() => newSubscription); // store cleanup fn
          addLog('Real-time connection established', 'success');
        }
      } catch (subscriptionError) {
        if (isMounted) addLog(`Failed to establish real-time connection: ${subscriptionError.message}`, 'warning');
      }
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
      if (isMounted) setIsInitializing(false);
    }
  }, [vehicleId, addLog, performStatusCheck, cleanup, isInitializing, isMounted]);

  /* eslint-disable react-hooks/exhaustive-deps */
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
  }, [vehicleId, isConnected]);

  useEffect(() => {
    initializeConnection();
    return cleanup;
  }, []);
  /* eslint-enable react-hooks/exhaustive-deps */

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

  // Debug logging
  console.log('SimulatorPanel - vehicleId:', vehicleId);
  console.log('SimulatorPanel - vehicleStatus:', vehicleStatus);

  return (
    <div className="max-w-[1600px] mx-auto h-[calc(100vh-160px)] overflow-hidden" style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}>
      <div className="bg-gradient-to-b from-primary to-primary/90 dark:from-[#0B1220] dark:to-[#05080F] text-primary-foreground dark:text-foreground p-3 flex justify-between items-center border-b border-border">
        <div className="flex items-center gap-2">
          <Car className="h-5 w-5" />
          <h1 className="text-lg font-semibold">
            Car Device Simulator
            {vehicleId ? (
              <span className="text-sm ml-2 opacity-80">(ID: {vehicleId})</span>
            ) : (
              <span className="text-sm ml-2 opacity-80 text-yellow-400">(No Vehicle Selected)</span>
            )}
          </h1>
        </div>
        <div className="flex items-center gap-2 bg-background text-foreground px-3 py-1 rounded-full font-semibold text-sm">
          <div className={`w-2.5 h-2.5 rounded-full ${
            isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
          }`} />
          <span>{isConnected ? 'CONNECTED' : 'DISCONNECTED'}</span>
        </div>
      </div>
      
      <div className="p-2 md:p-3 lg:p-4 h-[calc(100%-60px)] overflow-auto">
        {!vehicleId && (
          <div className="mb-4 p-4 bg-yellow-50 dark:bg-yellow-950/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
            <p className="text-sm text-yellow-800 dark:text-yellow-200">
              ⚠️ No vehicle selected. Please select a vehicle from the header dropdown to view live data.
            </p>
          </div>
        )}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-2 md:gap-4 lg:gap-6">
          <div className="h-auto">
            <CommandPanel 
              onSendCommand={handleSendCommand} 
              isConnected={isConnected}
              vehicleId={vehicleId}
            />
          </div>
          <div className="h-auto">
            <LogsPanel 
              logs={logs} 
              isConnected={isConnected} 
              onToggleConnection={toggleConnection}
              vehicleId={vehicleId}
            />
          </div>
          <div className="lg:col-span-2">
            <VehicleMetrics vehicleStatus={vehicleStatus} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default SimulatorPanel;
