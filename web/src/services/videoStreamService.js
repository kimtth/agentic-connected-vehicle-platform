class VideoStreamService {
  constructor() {
    this.ws = null;
    this.videoUrl = null;
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 5;
    this.reconnectTimeout = null;
    this.heartbeatInterval = null;
    this.pollInterval = null;
    this.snapshotUrl = null;
    this.frameListeners = new Set();
  }

  onFrame(cb) {
    this.frameListeners.add(cb);
    return () => this.frameListeners.delete(cb);
  }

  _notifyFrame() {
    if (!this.videoUrl) return;
    this.frameListeners.forEach(cb => {
      try { cb(this.videoUrl); } catch {}
    });
  }

  async connect(serverUrl) {
    return new Promise((resolve, reject) => {
      try {
        // Preserve listeners during reconnect
        this.disconnect(false);
        // Browser cannot open raw TCP (Python server uses plain sockets 8000).
        // Expect a gateway exposing either:
        // 1) WebSocket forwarding binary JPEG frames, or
        // 2) MJPEG/HTTP endpoint /video_feed, or
        // 3) Snapshot JPEG endpoint (we poll).

        if (serverUrl.startsWith('http')) {
          // If user points directly to a JPEG (e.g. http://host:8000/video.jpg) enable polling
          if (serverUrl.endsWith('.jpg') || serverUrl.endsWith('.jpeg')) {
            this.snapshotUrl = serverUrl;
            this._startSnapshotPolling();
            this.videoUrl = this._cacheBustedSnapshot();
            this._notifyFrame();
            resolve(this.videoUrl);
            return;
          }

          // Direct MJPEG stream URL
          const streamUrl = `${serverUrl}/video_feed`;
          this.videoUrl = streamUrl;
          
          // Test the connection
          fetch(streamUrl, { method: 'HEAD' })
            .then(() => {
              this._notifyFrame();
              resolve(streamUrl);
            })
            .catch(error => {
              reject(new Error(`Failed to connect to video stream: ${error.message}`));
            });
          return;
        }

        // For WebSocket-based streaming
        this.ws = new WebSocket(serverUrl);
        
        this.ws.onopen = () => {
          console.log('Video WebSocket connected');
          this.reconnectAttempts = 0;
          this.startHeartbeat();
          resolve(this.videoUrl);
        };

        this.ws.onmessage = (event) => {
          // Handle different message types
          if (event.data instanceof Blob) {
            // Binary image data
            const url = URL.createObjectURL(event.data);
            if (this.videoUrl) {
              URL.revokeObjectURL(this.videoUrl);
            }
            this.videoUrl = url;
          } else {
            // Text message (could be base64 image or control message)
            try {
              const data = JSON.parse(event.data);
              if (data.type === 'frame' && data.image) {
                // Base64 encoded image
                this.videoUrl = `data:image/jpeg;base64,${data.image}`;
              }
            } catch (e) {
              // If not JSON, might be raw base64
              if (event.data.startsWith('data:image')) {
                this.videoUrl = event.data;
              }
            }
          }
          // Inject notification after determining final this.videoUrl
          this._notifyFrame();
        };

        this.ws.onerror = (error) => {
          console.error('Video WebSocket error:', error);
          reject(new Error('WebSocket connection failed'));
        };

        this.ws.onclose = () => {
          console.log('Video WebSocket closed');
          this.stopHeartbeat();
          this.attemptReconnect(serverUrl);
        };

        // Set a connection timeout
        setTimeout(() => {
          if (this.ws.readyState !== WebSocket.OPEN) {
            this.ws.close();
            reject(new Error('Connection timeout'));
          }
        }, 5000);

      } catch (error) {
        reject(error);
      }
    });
  }

  _cacheBustedSnapshot() {
    return `${this.snapshotUrl}?t=${Date.now()}`;
  }

  _startSnapshotPolling() {
    this._stopSnapshotPolling();
    this.pollInterval = setInterval(() => {
      if (this.snapshotUrl) {
        this.videoUrl = this._cacheBustedSnapshot();
        this._notifyFrame();
      }
    }, 500); // 2 fps; adjust if needed
  }

  _stopSnapshotPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
  }

  disconnect(clearListeners = true) {
    this.stopHeartbeat();
    this._stopSnapshotPolling();
    
    if (this.reconnectTimeout) {
      clearTimeout(this.reconnectTimeout);
      this.reconnectTimeout = null;
    }

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }

    if (this.videoUrl && this.videoUrl.startsWith('blob:')) {
      URL.revokeObjectURL(this.videoUrl);
    }
    this.videoUrl = null;
    this.snapshotUrl = null;
    if (clearListeners) this.frameListeners.clear();
  }

  attemptReconnect(serverUrl) {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 10000);
    
    console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.connect(serverUrl).catch(error => {
        console.error('Reconnection failed:', error);
      });
    }, delay);
  }

  startHeartbeat() {
    this.heartbeatInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Send heartbeat every 30 seconds
  }

  stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  getVideoUrl() {
    return this.videoUrl;
  }

  isConnected() {
    return this.ws && this.ws.readyState === WebSocket.OPEN;
  }
}

export default VideoStreamService;
