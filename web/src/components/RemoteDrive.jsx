import { useState, useEffect, useCallback } from 'react';
import {
  ChevronUp, ChevronDown, ChevronLeft, ChevronRight,
  Square, Home, Video, VideoOff, Wifi, WifiOff,
  RotateCw, Volume2, VolumeX, Construction
} from 'lucide-react';
import demoVideo from '../assets/video.mp4'; // Path expects: web/src/assets/video.mp4. Adjust if asset lives elsewhere.

const RemoteDrive = () => {
  // Connection/demo states (now local only)
  const [videoConnected, setVideoConnected] = useState(true);      // start connected for demo
  const [controlConnected, setControlConnected] = useState(true);  // start connected for demo
  
  // Video states (placeholder demo image)
  const videoFallback = demoVideo || '/video.mp4'; // fallback to public root if import fails
  const [videoUrl, setVideoUrl] = useState(videoFallback);
  const [videoError, setVideoError] = useState('');
  
  // Control states
  const [speed, setSpeed] = useState(50);
  const [servo1, setServo1] = useState(90);
  const [servo2, setServo2] = useState(90);
  const [buzzerOn, setBuzzerOn] = useState(false);
  const [ledsOn, setLedsOn] = useState(false);
  const [demoLoop, setDemoLoop] = useState(false); // placeholder loop flag
  
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
    setDemoLoop(false);
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
    setVideoUrl(videoFallback);
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

  const toggleDemoLoop = () => {
    setDemoLoop(v => {
      const nv = !v;
      addLog(`Demo loop ${nv ? 'started' : 'stopped'}`);
      return nv;
    });
  };

  // Placeholder servo sweep loop (demo)
  useEffect(() => {
    if (!demoLoop) return;
    let direction = 1;
    const id = setInterval(() => {
      setServo1(prev => {
        let next = prev + direction * 5;
        if (next >= 180) { next = 180; direction = -1; }
        if (next <= 0) { next = 0; direction = 1; }
        return next;
      });
    }, 300);
    return () => clearInterval(id);
  }, [demoLoop]);

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
    <div className="p-5">
      <div className="flex items-center gap-1.5 bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded-md p-2.5 mb-3">
        <Construction className="h-4 w-4 text-blue-600 dark:text-blue-400" />
        <span className="text-xs text-blue-900 dark:text-blue-100">Under construction demo mode – all controls are simulated.</span>
      </div>
      <h1 className="text-xl font-semibold mb-3">Remote Drive Control</h1>
      
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3">
        {/* Video Feed Section */}
        <div className="lg:col-span-6">
          <div className="bg-card rounded-lg border border-border p-4">
            <div className="flex justify-between items-center mb-3">
              <h2 className="text-base font-semibold">Video Feed</h2>
              <div className="flex items-center gap-1.5">
                <span className={`flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs ${
                  videoConnected ? 'bg-green-100 dark:bg-green-950 text-green-800 dark:text-green-200' : 'bg-gray-100 dark:bg-gray-800'
                }`}>
                  {videoConnected ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
                  {videoConnected ? 'Connected' : 'Disconnected'}
                </span>
                <button
                  onClick={connect}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-xs"
                >
                  <Video className="h-3.5 w-3.5" />
                  Connect
                </button>
                <button
                  onClick={disconnect}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 border border-input rounded-md hover:bg-accent text-xs"
                >
                  <VideoOff className="h-3.5 w-3.5" />
                  Disconnect
                </button>
              </div>
            </div>
            
            <div className="relative pt-[56.25%] bg-black rounded-md overflow-hidden">
              {videoConnected ? (
                <video
                  src={videoUrl}
                  autoPlay
                  muted
                  loop
                  playsInline
                  onError={() => setVideoError('Failed to load demo video')}
                  className="absolute top-0 left-0 w-full h-full object-cover"
                  style={{ filter: buzzerOn ? 'hue-rotate(45deg)' : 'none' }}
                />
              ) : (
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center">
                  <VideoOff className="h-16 w-16 text-gray-500 mx-auto" />
                  <p className="text-gray-500 mt-4">No video feed</p>
                </div>
              )}
            </div>
            
            {videoError && (
              <div className="mt-4 p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-md text-red-900 dark:text-red-100">
                {videoError}
              </div>
            )}
          </div>

          <div className="mt-3 bg-card rounded-lg border border-border p-4">
            <h2 className="text-base font-semibold mb-3">Activity Log</h2>
            
            <div className="mb-3">
              <h3 className="text-xs font-medium text-muted-foreground mb-1.5">Telemetry</h3>
              <div className="flex flex-wrap gap-2">
                <span className={`px-2 py-1 text-xs rounded ${
                  ultrasonic != null ? 'bg-primary text-primary-foreground' : 'bg-muted'
                }`}>
                  Distance: {ultrasonic != null ? `${ultrasonic}cm` : '--'}
                </span>
                <span className="px-2 py-1 text-xs rounded bg-muted">
                  Light {light ? `L:${light.left}V R:${light.right}V` : '--'}
                </span>
                <span className={`px-2 py-1 text-xs rounded ${
                  power != null ? (power > 30 ? 'bg-green-100 dark:bg-green-950 text-green-800 dark:text-green-200' : 'bg-yellow-100 dark:bg-yellow-950 text-yellow-800 dark:text-yellow-200') : 'bg-muted'
                }`}>
                  Power: {power != null ? `${Math.round(power)}%` : '--'}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Live telemetry only available when WS gateway passes raw server lines.
              </p>
            </div>
            
            <div className="border border-border rounded-md max-h-[200px] overflow-auto p-2">
              {activityLog.map((log, index) => (
                <div key={index} className="mb-1">
                  <span className={`text-xs ${
                    log.type === 'error' ? 'text-red-600 dark:text-red-400' :
                    log.type === 'success' ? 'text-green-600 dark:text-green-400' :
                    log.type === 'warning' ? 'text-yellow-600 dark:text-yellow-400' :
                    'text-muted-foreground'
                  }`}>
                    [{log.timestamp}] {log.message}
                  </span>
                </div>
              ))}
              {activityLog.length === 0 && (
                <span className="text-xs text-muted-foreground">No activity yet</span>
              )}
            </div>

            <div className="border-t border-border my-4" />
            <h2 className="text-xl font-semibold mb-4">Server Configuration</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Video Server URL</label>
                <input
                  type="text"
                  value={videoServerUrl}
                  onChange={(e) => setVideoServerUrl(e.target.value)}
                  className="w-full px-3 py-2 border border-input rounded-md"
                />
                <p className="text-xs text-muted-foreground mt-1">WebSocket URL for video stream</p>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Control Server URL</label>
                <input
                  type="text"
                  value={controlServerUrl}
                  onChange={(e) => setControlServerUrl(e.target.value)}
                  className="w-full px-3 py-2 border border-input rounded-md"
                />
                <p className="text-xs text-muted-foreground mt-1">HTTP URL for remote control</p>
              </div>
            </div>
          </div>
        </div>

        {/* Control Panel */}
        <div className="lg:col-span-6">
          <div className="bg-card rounded-lg border border-border p-6">
            <h2 className="text-xl font-semibold mb-4">Movement Controls</h2>
            
            <div className="flex justify-center mb-6">
              <span className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm ${
                controlConnected ? 'bg-green-100 dark:bg-green-950 text-green-800 dark:text-green-200' : 'bg-muted'
              }`}>
                {controlConnected ? <Wifi className="h-4 w-4" /> : <WifiOff className="h-4 w-4" />}
                {controlConnected ? 'Control Active' : 'Control Inactive'}
              </span>
            </div>

            {/* Direction Pad */}
            <div className="flex flex-col items-center mb-6">
              <button
                onMouseDown={() => handleMove('forward')}
                onMouseUp={handleStop}
                onMouseLeave={handleStop}
                className="p-2 hover:bg-accent rounded-lg transition-colors"
              >
                <ChevronUp className="h-10 w-10" />
              </button>
              
              <div className="flex gap-8">
                <button
                  onMouseDown={() => handleMove('left')}
                  onMouseUp={handleStop}
                  onMouseLeave={handleStop}
                  className="p-2 hover:bg-accent rounded-lg transition-colors"
                >
                  <ChevronLeft className="h-10 w-10" />
                </button>
                
                <button onClick={handleStop} className="p-2 hover:bg-red-100 dark:hover:bg-red-950 rounded-lg transition-colors text-red-600">
                  <Square className="h-10 w-10" />
                </button>
                
                <button
                  onMouseDown={() => handleMove('right')}
                  onMouseUp={handleStop}
                  onMouseLeave={handleStop}
                  className="p-2 hover:bg-accent rounded-lg transition-colors"
                >
                  <ChevronRight className="h-10 w-10" />
                </button>
              </div>
              
              <button
                onMouseDown={() => handleMove('backward')}
                onMouseUp={handleStop}
                onMouseLeave={handleStop}
                className="p-2 hover:bg-accent rounded-lg transition-colors"
              >
                <ChevronDown className="h-10 w-10" />
              </button>
            </div>

            <div className="border-t border-border my-4" />

              {/* Speed Control */}
              <div className="mb-6">
                <div className="flex justify-between mb-2">
                  <span className="text-sm font-medium">Speed: {speed}%</span>
                  <div className="flex gap-2 text-xs text-muted-foreground">
                    <span>0</span>
                    <span>50</span>
                    <span>100</span>
                  </div>
                </div>
                <input
                  type="range"
                  value={speed}
                  onChange={(e) => setSpeed(Number(e.target.value))}
                  min={0}
                  max={100}
                  className="w-full"
                />
              </div>

              <div className="border-t border-border my-4" />

              {/* Servo Controls */}
              <div className="mb-6">
                <h3 className="text-sm font-medium mb-3">Camera Controls</h3>
                
                <div className="mb-4">
                  <label className="text-sm mb-2 block">Horizontal (Servo 1): {servo1}°</label>
                  <input
                    type="range"
                    value={servo1}
                    onChange={(e) => handleServoChange(1, Number(e.target.value))}
                    min={0}
                    max={180}
                    className="w-full"
                  />
                </div>
                
                <div className="mb-4">
                  <label className="text-sm mb-2 block">Vertical (Servo 2): {servo2}°</label>
                  <input
                    type="range"
                    value={servo2}
                    onChange={(e) => handleServoChange(2, Number(e.target.value))}
                    min={80}
                    max={180}
                    className="w-full"
                  />
                </div>
                
                <button
                  onClick={handleHome}
                  className="flex items-center justify-center gap-2 w-full px-4 py-2 border border-input rounded-md hover:bg-accent"
                >
                  <Home className="h-4 w-4" />
                  Reset Camera Position
                </button>
                <button
                  onClick={toggleDemoLoop}
                  className={`flex items-center justify-center gap-2 w-full px-4 py-2 rounded-md mt-2 ${
                    demoLoop ? 'bg-green-600 text-white hover:bg-green-700' : 'border border-input hover:bg-accent'
                  }`}
                >
                  {demoLoop ? 'Stop Demo Loop' : 'Start Demo Loop'}
                </button>
              </div>

              <div className="border-t border-border my-4" />

              {/* Additional Controls */}
              <div className="mb-4">
                <h3 className="text-sm font-medium mb-3">Accessories</h3>
                
                <div className="flex gap-2">
                  <button
                    onClick={toggleBuzzer}
                    className={`flex items-center justify-center gap-2 flex-1 px-4 py-2 rounded-md ${
                      buzzerOn ? 'bg-primary text-primary-foreground' : 'border border-input hover:bg-accent'
                    }`}
                  >
                    {buzzerOn ? <Volume2 className="h-4 w-4" /> : <VolumeX className="h-4 w-4" />}
                    Buzzer
                  </button>
                  
                  <button
                    onClick={toggleLeds}
                    className={`flex items-center justify-center gap-2 flex-1 px-4 py-2 rounded-md ${
                      ledsOn ? 'bg-primary text-primary-foreground' : 'border border-input hover:bg-accent'
                    }`}
                  >
                    <RotateCw className="h-4 w-4" />
                    LEDs
                  </button>
                </div>
              </div>

              <div className="border-t border-border my-4" />

            {/* Keyboard Shortcuts */}
            <div>
              <p className="text-sm text-muted-foreground mb-1">Keyboard Controls:</p>
              <p className="text-xs text-muted-foreground">
                W/S/A/D - Move | Space - Stop | H - Home
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RemoteDrive;