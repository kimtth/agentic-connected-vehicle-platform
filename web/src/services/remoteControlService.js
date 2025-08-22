class RemoteControlService {
  constructor() {
    this.baseUrl = null;
    this.socket = null;
    this.connected = false;
    this.commandQueue = [];
    this.processing = false;
    this.telemetryHandler = null;
    this._recvBuffer = '';
  }

  setTelemetryHandler(fn) {
    this.telemetryHandler = fn;
  }

  async connect(serverUrl) {
    this.baseUrl = serverUrl;
    
    // Try to establish connection
    try {
      // For HTTP-based control
      if (serverUrl.startsWith('http')) {
        const response = await fetch(`${serverUrl}/status`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        if (response.ok) {
          this.connected = true;
          console.log('Remote control connected via HTTP');
          return true;
        }
      }
      
      // For WebSocket-based control
      if (serverUrl.startsWith('ws')) {
        return new Promise((resolve, reject) => {
          this.socket = new WebSocket(serverUrl);
          
          this.socket.onopen = () => {
            this.connected = true;
            console.log('Remote control connected via WebSocket');
            this.processCommandQueue();
            resolve(true);
          };
          
          this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            reject(new Error('Failed to connect to control server'));
          };
          
          this.socket.onclose = () => {
            this.connected = false;
            console.log('Remote control WebSocket closed');
          };

          this.socket.onmessage = (evt) => {
            const data = typeof evt.data === 'string' ? evt.data : '';
            if (!data) return;
            this._recvBuffer += data;
            // Split by newline (Python server sends '\n')
            const lines = this._recvBuffer.split('\n');
            this._recvBuffer = lines.pop(); // residual
            lines.forEach(line => this._parseTelemetryLine(line.trim()));
          };
          
          setTimeout(() => {
            if (!this.connected) {
              reject(new Error('Connection timeout'));
            }
          }, 5000);
        });
      }
      
      // For TCP-based control (would need a proxy/bridge)
      throw new Error('Unsupported protocol');
      
    } catch (error) {
      console.error('Failed to connect to remote control:', error);
      throw error;
    }
  }

  disconnect() {
    this.connected = false;
    
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    
    this.commandQueue = [];
    this.baseUrl = null;
  }

  async sendCommand(command, params = {}) {
    if (!this.connected) {
      throw new Error('Not connected to control server');
    }

    const commandData = this.formatCommand(command, params);
    
    // HTTP-based sending
    if (this.baseUrl && this.baseUrl.startsWith('http')) {
      try {
        const response = await fetch(`${this.baseUrl}/command`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            command: command,
            params: params,
            timestamp: Date.now()
          }),
        });
        
        if (!response.ok) {
          throw new Error(`Command failed: ${response.statusText}`);
        }
        
        return await response.json();
      } catch (error) {
        console.error('Failed to send command:', error);
        throw error;
      }
    }
    
    // WebSocket-based sending
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(commandData);
      return { success: true };
    }
    
    // Queue command if not ready
    this.commandQueue.push({ command, params });
    this.processCommandQueue();
  }

  formatCommand(command, params) {
    // Format command based on the protocol expected by the RC server
    // This matches the Python client format: CMD#param1#param2#...
    const intervalChar = '#';
    const endChar = '\n';
    
    let formattedCommand = command;
    
    switch(command) {
      case 'CMD_MOTOR':
        // Motor control: CMD_MOTOR#speed1#speed2#speed3#speed4
        if (params.values) {
          formattedCommand = `${command}${intervalChar}${params.values.join(intervalChar)}${endChar}`;
        }
        break;
        
      case 'CMD_SERVO':
        // Servo control: CMD_SERVO#servo_num#angle
        if (params.servo !== undefined && params.angle !== undefined) {
          formattedCommand = `${command}${intervalChar}${params.servo}${intervalChar}${params.angle}${endChar}`;
        }
        break;
        
      case 'CMD_LED':
        // Support RGB: CMD_LED#maskIndex#R#G#B
        if (params.ledIndex !== undefined && Array.isArray(params.rgb) && params.rgb.length === 3) {
          const [r,g,b] = params.rgb;
            formattedCommand = `${command}${intervalChar}${params.ledIndex}${intervalChar}${r}${intervalChar}${g}${intervalChar}${b}${endChar}`;
        } else if (params.mode !== undefined) {
          // fallback (rare)
          formattedCommand = `${command}${intervalChar}${params.mode}${endChar}`;
        }
        break;
        
      case 'CMD_LED_MOD':
        // LED control: CMD_LED_MOD#mode
        if (params.mode !== undefined) {
          formattedCommand = `${command}${intervalChar}${params.mode}${endChar}`;
        }
        break;
        
      case 'CMD_BUZZER':
        // Buzzer control: CMD_BUZZER#state
        if (params.state !== undefined) {
          formattedCommand = `${command}${intervalChar}${params.state}${endChar}`;
        }
        break;
        
      default:
        // Generic command format
        if (params.values) {
          formattedCommand = `${command}${intervalChar}${params.values.join(intervalChar)}${endChar}`;
        } else {
          formattedCommand = `${command}${endChar}`;
        }
    }
    
    return formattedCommand;
  }

  _emitTelemetry(obj) {
    if (this.telemetryHandler) this.telemetryHandler(obj);
  }

  _parseTelemetryLine(line) {
    if (!line) return;
    const parts = line.split('#');
    // parts example: CMD_SONIC#<distance>
    try {
      if (parts[0] === 'CMD_SONIC' && parts.length >= 2) {
        this._emitTelemetry({ type:'CMD_SONIC', distance: parts[1], raw: line });
      } else if (parts[0] === 'CMD_LIGHT' && parts.length >= 3) {
        this._emitTelemetry({ type:'CMD_LIGHT', left: parts[1], right: parts[2], raw: line });
      } else if (parts[0] === 'CMD_POWER' && parts.length >= 2) {
        const raw = parts[1];
        let val = parseFloat(raw);
        let percent = 0;
        if (isFinite(val)) {
          // If looks like voltage (> 20 unlikely), treat ≤ 20 as voltage else already percent? 
          // Original desktop computed: (voltage -7)/1.40*100
          if (val > 20) {
            percent = Math.round(val); // already percent
          } else {
            percent = Math.round(((val - 7) / 1.40) * 100);
          }
          percent = Math.min(100, Math.max(0, percent));
        }
        this._emitTelemetry({ type:'CMD_POWER', percent, raw: line });
      } else {
        this._emitTelemetry({ type:'OTHER', raw: line });
      }
    } catch {
      this._emitTelemetry({ type:'PARSE_ERROR', raw: line });
    }
  }

  async processCommandQueue() {
    if (this.processing || this.commandQueue.length === 0) {
      return;
    }
    
    this.processing = true;
    
    while (this.commandQueue.length > 0 && this.connected) {
      const { command, params } = this.commandQueue.shift();
      try {
        await this.sendCommand(command, params);
        await this.delay(50); // Small delay between commands
      } catch (error) {
        console.error('Failed to process queued command:', error);
      }
    }
    
    this.processing = false;
  }

  delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  isConnected() {
    return this.connected;
  }

  // Command shortcuts for common operations
  async moveForward(speed = 1500) {
    return this.sendCommand('CMD_MOTOR', { values: [speed, speed, speed, speed] });
  }

  async moveBackward(speed = 1500) {
    return this.sendCommand('CMD_MOTOR', { values: [-speed, -speed, -speed, -speed] });
  }

  async turnLeft(speed = 1500) {
    return this.sendCommand('CMD_MOTOR', { values: [-speed, -speed, speed, speed] });
  }

  async turnRight(speed = 1500) {
    return this.sendCommand('CMD_MOTOR', { values: [speed, speed, -speed, -speed] });
  }

  async stop() {
    return this.sendCommand('CMD_MOTOR', { values: [0, 0, 0, 0] });
  }

  async setServo(servoNum, angle) {
    return this.sendCommand('CMD_SERVO', { servo: servoNum, angle: angle });
  }

  async setBuzzer(state) {
    return this.sendCommand('CMD_BUZZER', { state: state ? 1 : 0 });
  }

  async setLedMode(mode) {
    return this.sendCommand('CMD_LED_MOD', { mode: mode });
  }
}

export default RemoteControlService;
