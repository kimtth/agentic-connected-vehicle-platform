import { useState, useEffect, useCallback } from 'react';
import {
  Box, Paper, Grid, Typography, Button, IconButton,
  Card, CardContent, Chip, Alert, Slider, TextField,
  Divider
} from '@mui/material';
import {
  KeyboardArrowUp, KeyboardArrowDown, KeyboardArrowLeft, KeyboardArrowRight,
  Stop, Home, Videocam, VideocamOff, WifiTethering, WifiTetheringOff,
  RotateRight, VolumeUp, VolumeOff
} from '@mui/icons-material';
import ConstructionIcon from '@mui/icons-material/Construction';

const RemoteDrive = () => {
  // Connection/demo states (now local only)
  const [videoConnected, setVideoConnected] = useState(true);      // start connected for demo
  const [controlConnected, setControlConnected] = useState(true);  // start connected for demo
  
  // Video states (placeholder demo image)
  const [videoUrl, setVideoUrl] = useState('https://via.placeholder.com/800x450?text=Demo+Video');
  const [videoError, setVideoError] = useState('');
  
  // Control states
  const [speed, setSpeed] = useState(50);
  const [servo1, setServo1] = useState(90);
  const [servo2, setServo2] = useState(90);
  const [buzzerOn, setBuzzerOn] = useState(false);
  const [ledsOn, setLedsOn] = useState(false);
  
  // Telemetry states
  const [ultrasonic,setUltrasonic] = useState(null);
  const [light,setLight] = useState(null);
  const [power,setPower] = useState(null); // percent
  
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
    setVideoConnected(false);
    setControlConnected(false);
    setVideoUrl('');
    setUltrasonic(null);
    setLight(null);
    setPower(null);
    // accessories off
    setBuzzerOn(false);
    setLedsOn(false);
    addLog('Demo: Disconnected');
  }, [addLog]);

  // Random telemetry generator while connected
  useEffect(() => {
    if (!controlConnected) return;
    const id = setInterval(() => {
      setUltrasonic(Math.floor(10 + Math.random() * 90));
      setLight({ left: (2 + Math.random()).toFixed(2), right: (2 + Math.random()).toFixed(2) });
      setPower(p => (p == null || p < 5) ? 100 : p - Math.random() * 0.5); // slow drain
    }, 1500);
    return () => clearInterval(id);
  }, [controlConnected]);

  // Simplified connect (instant)
  const connect = async () => {
    setVideoError('');
    setVideoConnected(true);
    setControlConnected(true);
    setVideoUrl('https://via.placeholder.com/800x450?text=Demo+Video');
    addLog('Demo: Connected');
  };

  // Movement handlers (no backend)
  const handleMove = useCallback((direction) => {
    const speedValue = Math.round(speed * 15);
    addLog(`Move ${direction} @ internalSpeed=${speedValue}`);
  }, [speed, addLog]);

  const handleStop = useCallback(() => {
    addLog('Stop');
  }, [addLog]);

  const handleServoChange = (servo, value) => {
    if (servo === 1) {
      setServo1(value);
      addLog(`Servo1 -> ${value}`);
    } else {
      setServo2(value);
      addLog(`Servo2 -> ${value}`);
    }
  };

  const handleHome = useCallback(() => {
    setServo1(90);
    setServo2(90);
    addLog('Camera reset to home');
  }, [addLog]);

  const toggleBuzzer = () => {
    setBuzzerOn(b => {
      const v = !b;
      addLog(`Buzzer ${v ? 'ON' : 'OFF'}`);
      return v;
    });
  };

  const toggleLeds = () => {
    setLedsOn(l => {
      const v = !l;
      addLog(`LEDs ${v ? 'ON' : 'OFF'}`);
      return v;
    });
  };

  // Keyboard controls (always active now)
  useEffect(() => {
    const handleKeyDown = (e) => {
      switch(e.key.toLowerCase()) {
        case 'w': handleMove('forward'); break;
        case 's': handleMove('backward'); break;
        case 'a': handleMove('left'); break;
        case 'd': handleMove('right'); break;
        case ' ': handleStop(); e.preventDefault(); break;
        case 'h': handleHome(); break;
        default: break;
      }
    };
    const handleKeyUp = (e) => {
      if (['w','s','a','d'].includes(e.key.toLowerCase())) handleStop();
    };
    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [handleMove, handleStop, handleHome]);

  return (
    <Box sx={{ p: 3 }}>
      <Alert
        icon={<ConstructionIcon fontSize="inherit" />}
        severity="info"
        sx={{ mb: 2 }}
      >
        Under construction demo mode – all controls are simulated.
      </Alert>
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
                  <Button
                    variant="contained"
                    size="small"
                    onClick={connect}
                    startIcon={<Videocam />}
                  >
                    Connect
                  </Button>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={disconnect}
                    startIcon={<VideocamOff />}
                    sx={{ ml: 1 }}
                  >
                    Disconnect
                  </Button>
                </Box>
              </Box>
              
              <Paper sx={{ position: 'relative', paddingTop: '56.25%' }}>
                {videoConnected ? (
                  <Box
                    component="img"
                    src={videoUrl}
                    alt="Demo video feed"
                    sx={{
                      position: 'absolute', top: 0, left: 0,
                      width: '100%', height: '100%',
                      objectFit: 'cover',
                      filter: buzzerOn ? 'hue-rotate(45deg)' : 'none'
                    }}
                  />
                ) : (
                  <Box
                    sx={{
                      position: 'absolute',
                      top: '50%', left: '50%',
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

          <Card sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Activity Log
              </Typography>
              <Paper variant="outlined" sx={{ maxHeight: 200, overflow: 'auto', p: 1 }}>
                {activityLog.map((log, index) => (
                  <Box key={index} sx={{ mb: 0.5 }}>
                    <Typography
                      variant="caption"
                      color={
                        log.type === 'error' ? 'error' :
                        log.type === 'success' ? 'success.main' :
                        log.type === 'warning' ? 'warning.main' :
                        'text.secondary'
                      }
                    >
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

              <Divider sx={{ my: 2 }} />
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
                    helperText="WebSocket URL for video stream"
                  />
                </Grid>
                <Grid item xs={12} md={6}>
                  <TextField
                    label="Control Server URL"
                    value={controlServerUrl}
                    onChange={(e) => setControlServerUrl(e.target.value)}
                    fullWidth
                    helperText="HTTP URL for remote control"
                  />
                </Grid>
              </Grid>
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
                <IconButton size="large"
                  onMouseDown={() => handleMove('forward')}
                  onMouseUp={handleStop}
                  onMouseLeave={handleStop}
                >
                  <KeyboardArrowUp sx={{ fontSize: 40 }} />
                </IconButton>
                
                <Box sx={{ display: 'flex', gap: 4 }}>
                  <IconButton size="large"
                    onMouseDown={() => handleMove('left')}
                    onMouseUp={handleStop}
                    onMouseLeave={handleStop}
                  >
                    <KeyboardArrowLeft sx={{ fontSize: 40 }} />
                  </IconButton>
                  
                  <IconButton size="large" onClick={handleStop} color="error">
                    <Stop sx={{ fontSize: 40 }} />
                  </IconButton>
                  
                  <IconButton size="large"
                    onMouseDown={() => handleMove('right')}
                    onMouseUp={handleStop}
                    onMouseLeave={handleStop}
                  >
                    <KeyboardArrowRight sx={{ fontSize: 40 }} />
                  </IconButton>
                </Box>
                
                <IconButton size="large"
                  onMouseDown={() => handleMove('backward')}
                  onMouseUp={handleStop}
                  onMouseLeave={handleStop}
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
                  />
                </Box>
                
                <Button
                  variant="outlined"
                  startIcon={<Home />}
                  onClick={handleHome}
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
                    fullWidth
                  >
                    Buzzer
                  </Button>
                  
                  <Button
                    variant={ledsOn ? 'contained' : 'outlined'}
                    startIcon={<RotateRight />}
                    onClick={toggleLeds}
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
        </Grid>
      </Grid>
    </Box>
  );
};

export default RemoteDrive;