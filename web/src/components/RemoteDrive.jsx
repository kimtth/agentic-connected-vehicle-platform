import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Box, Paper, Grid, Typography, Button, IconButton,
  Card, CardContent, Chip, Alert, Slider, TextField, 
  Divider, CircularProgress,
} from '@mui/material';
import {
  KeyboardArrowUp, KeyboardArrowDown, KeyboardArrowLeft, KeyboardArrowRight,
  Stop, Home, Videocam, VideocamOff, WifiTethering, WifiTetheringOff,
  RotateRight, VolumeUp, VolumeOff
} from '@mui/icons-material';
import VideoStreamService from '../services/videoStreamService';
import RemoteControlService from '../services/remoteControlService';

const RemoteDrive = () => {
  // Connection states
  const [videoConnected, setVideoConnected] = useState(false);
  const [controlConnected, setControlConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  
  // Video states
  const [videoUrl, setVideoUrl] = useState('');
  const [videoError, setVideoError] = useState('');
  const videoRef = useRef(null);
  
  // Control states
  const [, setIsMoving] = useState(false);
  const [speed, setSpeed] = useState(50);
  const [servo1, setServo1] = useState(90);
  const [servo2, setServo2] = useState(90);
  const [buzzerOn, setBuzzerOn] = useState(false);
  const [ledsOn, setLedsOn] = useState(false);
  
  // Telemetry states
  const [ultrasonic,setUltrasonic] = useState(null);
  const [light,setLight] = useState(null);
  const [power,setPower] = useState(null); // percent
  
  // Service instances
  const videoService = useRef(null);
  const controlService = useRef(null);
  const frameUnsubRef = useRef(null);
  
  // Server configuration
  const [videoServerUrl, setVideoServerUrl] = useState('ws://localhost:8000');
  const [controlServerUrl, setControlServerUrl] = useState('http://localhost:5000');
  
  // Activity log
  const [activityLog, setActivityLog] = useState([]);
  
  const addLog = useCallback((message, type = 'info') => {
    setActivityLog(prev => [{
      timestamp: new Date().toLocaleTimeString(),
      message,
      type
    }, ...prev.slice(0, 49)]);
  }, []);

  // Disconnect from servers (moved up to satisfy no-use-before-define)
  const disconnect = useCallback(() => {
    if (frameUnsubRef.current) {
      frameUnsubRef.current();
      frameUnsubRef.current = null;
    }
    if (videoService.current) {
      videoService.current.disconnect();
      setVideoConnected(false);
      setVideoUrl('');
    }
    if (controlService.current) {
      controlService.current.disconnect();
      setControlConnected(false);
    }
    setUltrasonic(null);
    setLight(null);
    setPower(null);
    addLog('Disconnected from servers', 'info');
  }, [addLog]);

  // Initialize services
  useEffect(() => {
    videoService.current = new VideoStreamService();
    controlService.current = new RemoteControlService();
    
    return () => {
      if (frameUnsubRef.current) frameUnsubRef.current();
      disconnect();
    };
  }, [disconnect]);

  // Telemetry handler
  const handleTelemetry = useCallback((t) => {
    if (!t) return;
    if (t.type === 'CMD_SONIC') setUltrasonic(t.distance);
    if (t.type === 'CMD_LIGHT') setLight({ left: t.left, right: t.right });
    if (t.type === 'CMD_POWER') setPower(t.percent);
    // Log raw message type
    if (t.raw) addLog(`Telemetry: ${t.raw}`, 'success');
  }, [addLog]);

  // Connect to servers
  const connect = async () => {
    setIsConnecting(true);
    setVideoError('');
    
    try {
      // Connect to video stream
      addLog('Connecting to video stream...', 'info');
      await videoService.current.connect(videoServerUrl);
      // Subscribe to frame updates (live refresh)
      if (frameUnsubRef.current) frameUnsubRef.current();
      frameUnsubRef.current = videoService.current.onFrame((url) => {
        setVideoUrl(url);
      });
      setVideoConnected(true); // mark connected even if first frame not arrived yet
      setVideoUrl(videoService.current.getVideoUrl() || '');
      addLog('Video stream connected', 'success');
    } catch (error) {
      setVideoError(error.message);
      addLog(`Video connection failed: ${error.message}`, 'error');
    }
    
    try {
      // Connect to control server
      addLog('Connecting to control server...', 'info');
      await controlService.current.connect(controlServerUrl);
      controlService.current.setTelemetryHandler(handleTelemetry);
      setControlConnected(true);
      addLog('Control server connected', 'success');
    } catch (error) {
      addLog(`Control connection failed: ${error.message}`, 'error');
    }
    
    setIsConnecting(false);
  };

  // Movement controls
  const sendCommand = useCallback(async (command, params = {}) => {
    if (!controlConnected) {
      addLog('Control not connected', 'warning');
      return;
    }
    
    try {
      await controlService.current.sendCommand(command, params);
      addLog(`Command sent: ${command}`, 'info');
    } catch (error) {
      addLog(`Command failed: ${error.message}`, 'error');
    }
  }, [controlConnected, addLog]);

  const handleMove = useCallback((direction) => {
    setIsMoving(true);
    const speedValue = Math.round(speed * 15); // Convert percentage to motor value
    
    switch(direction) {
      case 'forward':
        sendCommand('CMD_MOTOR', { values: [speedValue, speedValue, speedValue, speedValue] });
        break;
      case 'backward':
        sendCommand('CMD_MOTOR', { values: [-speedValue, -speedValue, -speedValue, -speedValue] });
        break;
      case 'left':
        sendCommand('CMD_MOTOR', { values: [-speedValue, -speedValue, speedValue, speedValue] });
        break;
      case 'right':
        sendCommand('CMD_MOTOR', { values: [speedValue, speedValue, -speedValue, -speedValue] });
        break;
      default:
        addLog(`Unknown direction: ${direction}`, 'warning');
        break;
    }
  }, [speed, sendCommand, addLog]);

  const handleStop = useCallback(() => {
    setIsMoving(false);
    sendCommand('CMD_MOTOR', { values: [0, 0, 0, 0] });
  }, [sendCommand]);

  const handleServoChange = (servo, value) => {
    if (servo === 1) {
      setServo1(value);
      sendCommand('CMD_SERVO', { servo: 0, angle: value });
    } else {
      setServo2(value);
      sendCommand('CMD_SERVO', { servo: 1, angle: value });
    }
  };

  const handleHome = useCallback(() => {
    setServo1(90);
    setServo2(90);
    sendCommand('CMD_SERVO', { servo: 0, angle: 90 });
    sendCommand('CMD_SERVO', { servo: 1, angle: 90 });
  }, [sendCommand]);

  const toggleBuzzer = () => {
    const newState = !buzzerOn;
    setBuzzerOn(newState);
    sendCommand('CMD_BUZZER', { state: newState ? 1 : 0 });
  };

  const toggleLeds = () => {
    const newState = !ledsOn;
    setLedsOn(newState);
    sendCommand('CMD_LED_MOD', { mode: newState ? 1 : 0 });
  };

  // Keyboard controls
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!controlConnected) return;
      
      switch(e.key.toLowerCase()) {
        case 'w': handleMove('forward'); break;
        case 's': handleMove('backward'); break;
        case 'a': handleMove('left'); break;
        case 'd': handleMove('right'); break;
        case ' ': handleStop(); e.preventDefault(); break;
        case 'h': handleHome(); break;
        default: addLog(`Unknown key: ${e.key}`, 'warning'); break;
      }
    };

    const handleKeyUp = (e) => {
      if (!controlConnected) return;
      
      if (['w', 's', 'a', 'd'].includes(e.key.toLowerCase())) {
        handleStop();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [controlConnected, addLog, handleHome, handleMove, handleStop]);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        Remote Drive Control
      </Typography>
      
      <Grid container spacing={3}>
        {/* Video Feed Section */}
        <Grid item xs={12} lg={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                <Typography variant="h6">Video Feed</Typography>
                <Box>
                  <Chip
                    icon={videoConnected ? <WifiTethering /> : <WifiTetheringOff />}
                    label={videoConnected ? 'Connected' : 'Disconnected'}
                    color={videoConnected ? 'success' : 'default'}
                    size="small"
                    sx={{ mr: 1 }}
                  />
                  {!videoConnected && (
                    <Button
                      variant="contained"
                      size="small"
                      onClick={connect}
                      disabled={isConnecting}
                      startIcon={isConnecting ? <CircularProgress size={16} /> : <Videocam />}
                    >
                      {isConnecting ? 'Connecting...' : 'Connect'}
                    </Button>
                  )}
                  {videoConnected && (
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={disconnect}
                      startIcon={<VideocamOff />}
                    >
                      Disconnect
                    </Button>
                  )}
                </Box>
              </Box>
              
              <Paper 
                sx={{ 
                  position: 'relative',
                  paddingTop: '56.25%' // 16:9 aspect ratio
                }}
              >
                {videoUrl ? (
                  <Box
                    component="img"
                    ref={videoRef}
                    src={videoUrl}
                    alt="Live video feed"
                    sx={{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: '100%',
                      objectFit: 'contain'
                    }}
                  />
                ) : (
                  <Box
                    sx={{
                      position: 'absolute',
                      top: '50%',
                      left: '50%',
                      transform: 'translate(-50%, -50%)',
                      textAlign: 'center'
                    }}
                  >
                    <VideocamOff sx={{ fontSize: 64, color: 'grey.500' }} />
                    <Typography color="grey.500" sx={{ mt: 2 }}>
                      No video feed
                    </Typography>
                  </Box>
                )}
              </Paper>
              
              {videoError && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {videoError}
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Control Panel */}
        <Grid item xs={12} lg={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Movement Controls
              </Typography>
              
              <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
                <Chip
                  icon={controlConnected ? <WifiTethering /> : <WifiTetheringOff />}
                  label={controlConnected ? 'Control Active' : 'Control Inactive'}
                  color={controlConnected ? 'success' : 'default'}
                />
              </Box>

              {/* Direction Pad */}
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 3 }}>
                <IconButton
                  size="large"
                  onMouseDown={() => handleMove('forward')}
                  onMouseUp={handleStop}
                  onMouseLeave={handleStop}
                  disabled={!controlConnected}
                >
                  <KeyboardArrowUp sx={{ fontSize: 40 }} />
                </IconButton>
                
                <Box sx={{ display: 'flex', gap: 4 }}>
                  <IconButton
                    size="large"
                    onMouseDown={() => handleMove('left')}
                    onMouseUp={handleStop}
                    onMouseLeave={handleStop}
                    disabled={!controlConnected}
                  >
                    <KeyboardArrowLeft sx={{ fontSize: 40 }} />
                  </IconButton>
                  
                  <IconButton
                    size="large"
                    onClick={handleStop}
                    disabled={!controlConnected}
                    color="error"
                  >
                    <Stop sx={{ fontSize: 40 }} />
                  </IconButton>
                  
                  <IconButton
                    size="large"
                    onMouseDown={() => handleMove('right')}
                    onMouseUp={handleStop}
                    onMouseLeave={handleStop}
                    disabled={!controlConnected}
                  >
                    <KeyboardArrowRight sx={{ fontSize: 40 }} />
                  </IconButton>
                </Box>
                
                <IconButton
                  size="large"
                  onMouseDown={() => handleMove('backward')}
                  onMouseUp={handleStop}
                  onMouseLeave={handleStop}
                  disabled={!controlConnected}
                >
                  <KeyboardArrowDown sx={{ fontSize: 40 }} />
                </IconButton>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Speed Control */}
              <Box sx={{ mb: 3 }}>
                <Typography gutterBottom>
                  Speed: {speed}%
                </Typography>
                <Slider
                  value={speed}
                  onChange={(e, v) => setSpeed(v)}
                  min={0}
                  max={100}
                  disabled={!controlConnected}
                  marks={[
                    { value: 0, label: '0' },
                    { value: 50, label: '50' },
                    { value: 100, label: '100' }
                  ]}
                />
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Servo Controls */}
              <Box sx={{ mb: 3 }}>
                <Typography gutterBottom>
                  Camera Controls
                </Typography>
                
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" gutterBottom>
                    Horizontal (Servo 1): {servo1}°
                  </Typography>
                  <Slider
                    value={servo1}
                    onChange={(e, v) => handleServoChange(1, v)}
                    min={0}
                    max={180}
                    disabled={!controlConnected}
                  />
                </Box>
                
                <Box sx={{ mb: 2 }}>
                  <Typography variant="body2" gutterBottom>
                    Vertical (Servo 2): {servo2}°
                  </Typography>
                  <Slider
                    value={servo2}
                    onChange={(e, v) => handleServoChange(2, v)}
                    min={80}
                    max={180}
                    disabled={!controlConnected}
                  />
                </Box>
                
                <Button
                  variant="outlined"
                  startIcon={<Home />}
                  onClick={handleHome}
                  disabled={!controlConnected}
                  fullWidth
                >
                  Reset Camera Position
                </Button>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Additional Controls */}
              <Box sx={{ mb: 2 }}>
                <Typography gutterBottom>
                  Accessories
                </Typography>
                
                <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                  <Button
                    variant={buzzerOn ? 'contained' : 'outlined'}
                    startIcon={buzzerOn ? <VolumeUp /> : <VolumeOff />}
                    onClick={toggleBuzzer}
                    disabled={!controlConnected}
                    fullWidth
                  >
                    Buzzer
                  </Button>
                  
                  <Button
                    variant={ledsOn ? 'contained' : 'outlined'}
                    startIcon={<RotateRight />}
                    onClick={toggleLeds}
                    disabled={!controlConnected}
                    fullWidth
                  >
                    LEDs
                  </Button>
                </Box>
              </Box>

              <Divider sx={{ my: 2 }} />

              {/* Telemetry Indicators */}
              <Box sx={{ mb: 2 }}>
                <Typography variant="h6" gutterBottom>Telemetry</Typography>
                <Box sx={{ display:'flex', flexWrap:'wrap', gap:1 }}>
                  <Chip
                    label={ultrasonic != null ? `Distance: ${ultrasonic}cm` : 'Distance: --'}
                    color={ultrasonic != null ? 'primary' : 'default'}
                    size="small"
                  />
                  <Chip
                    label={light ? `Light L:${light.left}V R:${light.right}V` : 'Light: --'}
                    size="small"
                  />
                  <Chip
                    label={power != null ? `Power: ${power}%` : 'Power: --'}
                    color={power != null ? (power > 30 ? 'success':'warning') : 'default'}
                    size="small"
                  />
                </Box>
                <Typography variant="caption" color="text.secondary">
                  Live telemetry only available when WS gateway passes raw server lines.
                </Typography>
              </Box>

              {/* Keyboard Shortcuts */}
              <Box>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Keyboard Controls:
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  W/S/A/D - Move | Space - Stop | H - Home
                </Typography>
              </Box>
            </CardContent>
          </Card>

          {/* Activity Log */}
          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Activity Log
              </Typography>
              <Paper variant="outlined" sx={{ maxHeight: 200, overflow: 'auto', p: 1 }}>
                {activityLog.map((log, index) => (
                  <Box key={index} sx={{ mb: 0.5 }}>
                    <Typography variant="caption" color={
                      log.type === 'error' ? 'error' : 
                      log.type === 'success' ? 'success.main' : 
                      log.type === 'warning' ? 'warning.main' : 
                      'text.secondary'
                    }>
                      [{log.timestamp}] {log.message}
                    </Typography>
                  </Box>
                ))}
                {activityLog.length === 0 && (
                  <Typography variant="caption" color="text.secondary">
                    No activity yet
                  </Typography>
                )}
              </Paper>
            </CardContent>
          </Card>
        </Grid>

        {/* Server Configuration */}
        <Grid item xs={12}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Server Configuration
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="Video Server URL"
                    value={videoServerUrl}
                    onChange={(e) => setVideoServerUrl(e.target.value)}
                    fullWidth
                    disabled={videoConnected}
                    helperText="WebSocket URL for video stream"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="Control Server URL"
                    value={controlServerUrl}
                    onChange={(e) => setControlServerUrl(e.target.value)}
                    fullWidth
                    disabled={controlConnected}
                    helperText="HTTP URL for remote control"
                  />
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default RemoteDrive;
