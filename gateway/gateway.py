import os
import struct
import socket
import threading
import time
import asyncio
from typing import Set, Optional, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from contextlib import asynccontextmanager

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CAR_HOST = os.getenv("CAR_HOST", "127.0.0.1")
CAR_VIDEO_PORT = int(os.getenv("CAR_VIDEO_PORT", "8000"))
CAR_CONTROL_PORT = int(os.getenv("CAR_CONTROL_PORT", "5000"))

RECONNECT_BASE_DELAY = 1.0
RECONNECT_MAX_DELAY = 10.0

# ---------------------------------------------------------------------------
# Shared State
# ---------------------------------------------------------------------------
gateway_status = {
    "video_connected": False,
    "control_connected": False,
    "last_video_frame_ts": None,
    "last_telemetry_ts": None,
    "commands_sent": 0,
    "telemetry_lines": 0,
    "frames_sent": 0
}
status_lock = threading.Lock()  # <-- restored to avoid NameError

latest_frame_lock = threading.Lock()
latest_frame: Optional[bytes] = None

control_ws_connections: Set[WebSocket] = set()
control_ws_lock = asyncio.Lock()

telemetry_queue: asyncio.Queue[str] = asyncio.Queue()

app = FastAPI(title="Connected Car Gateway", version="1.0.0")

# Allow local dev origins – tighten in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Low-level TCP Clients (Threads)
# ---------------------------------------------------------------------------
class VideoClient(threading.Thread):
    daemon = True

    def __init__(self, host: str, port: int):
        super().__init__(name="VideoClient")
        self.host = host
        self.port = port
        self._stop = threading.Event()

    def run(self):
        backoff = RECONNECT_BASE_DELAY
        while not self._stop.is_set():
            try:
                with socket.create_connection((self.host, self.port), timeout=5) as sock:
                    sock_file = sock.makefile('rb')
                    self._set_status(video=True, connected=True)
                    backoff = RECONNECT_BASE_DELAY
                    while not self._stop.is_set():
                        header = sock_file.read(4)
                        if not header or len(header) < 4:
                            raise ConnectionError("Video socket closed")
                        (length,) = struct.unpack('<L', header)
                        if length <= 0 or length > 10_000_000:
                            raise ValueError(f"Invalid frame length {length}")
                        data = sock_file.read(length)
                        if not data or len(data) < length:
                            raise ConnectionError("Incomplete frame")
                        # Store latest frame
                        with latest_frame_lock:
                            global latest_frame
                            latest_frame = data
                        with status_lock:
                            gateway_status["last_video_frame_ts"] = time.time()
                self._set_status(video=True, connected=False)
            except Exception:
                self._set_status(video=True, connected=False)
                time.sleep(backoff)
                backoff = min(backoff * 2, RECONNECT_MAX_DELAY)

    def stop(self):
        self._stop.set()

    @staticmethod
    def _set_status(video: bool, connected: bool):
        with status_lock:
            gateway_status["video_connected"] = connected


class ControlClient(threading.Thread):
    daemon = True

    def __init__(self, host: str, port: int):
        super().__init__(name="ControlClient")
        self.host = host
        self.port = port
        self._stop = threading.Event()
        self.sock: Optional[socket.socket] = None
        self.sock_lock = threading.Lock()

    def send_command(self, line: str):
        # Ensure newline termination
        if not line.endswith('\n'):
            line = line + '\n'
        with self.sock_lock:
            if self.sock:
                try:
                    self.sock.sendall(line.encode('utf-8'))
                    with status_lock:
                        gateway_status["commands_sent"] += 1
                except Exception:
                    # Allow sender to fail silently; connection thread will reconnect
                    pass
            else:
                raise ConnectionError("Control socket not connected")

    def run(self):
        backoff = RECONNECT_BASE_DELAY
        while not self._stop.is_set():
            try:
                with socket.create_connection((self.host, self.port), timeout=5) as sock:
                    with self.sock_lock:
                        self.sock = sock
                    self._set_status(control=True, connected=True)
                    backoff = RECONNECT_BASE_DELAY
                    sock_file = sock.makefile('r', encoding='utf-8', errors='ignore')
                    while not self._stop.is_set():
                        line = sock_file.readline()
                        if not line:
                            raise ConnectionError("Control socket closed")
                        line = line.rstrip('\r\n')
                        if line:
                            with status_lock:
                                gateway_status["telemetry_lines"] += 1
                                gateway_status["last_telemetry_ts"] = time.time()
                            # Push to async queue for fan-out
                            try:
                                asyncio.run_coroutine_threadsafe(telemetry_queue.put(line), asyncio.get_event_loop())
                            except RuntimeError:
                                # Event loop not ready; drop
                                pass
                self._set_status(control=True, connected=False)
            except Exception:
                self._set_status(control=True, connected=False)
                with self.sock_lock:
                    self.sock = None
                time.sleep(backoff)
                backoff = min(backoff * 2, RECONNECT_MAX_DELAY)

    def stop(self):
        self._stop.set()
        with self.sock_lock:
            try:
                if self.sock:
                    self.sock.close()
            except Exception:
                pass

    @staticmethod
    def _set_status(control: bool, connected: bool):
        with status_lock:
            gateway_status["control_connected"] = connected

# Singletons
video_client = VideoClient(CAR_HOST, CAR_VIDEO_PORT)
control_client = ControlClient(CAR_HOST, CAR_CONTROL_PORT)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if not video_client.is_alive():
        video_client.start()
    if not control_client.is_alive():
        control_client.start()
    yield
    # Shutdown
    video_client.stop()
    control_client.stop()
    # Optional joins (non-blocking safety)
    video_client.join(timeout=2)
    control_client.join(timeout=2)

app = FastAPI(title="Connected Car Gateway", version="1.0.0", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def _status_snapshot():
    with status_lock:
        return dict(gateway_status)

# ---------------------------------------------------------------------------
# HTTP Endpoints
# ---------------------------------------------------------------------------
@app.get("/status")
async def status():
    s = _status_snapshot()
    s["active_control_ws_clients"] = len(control_ws_connections)
    return JSONResponse(s)

@app.post("/command")
async def post_command(payload: dict):
    cmd = payload.get("command")
    if not cmd or not isinstance(cmd, str):
        raise HTTPException(400, "Missing command")
    try:
        control_client.send_command(cmd)
    except Exception as e:
        raise HTTPException(503, f"Send failed: {e}")
    return {"ok": True}

@app.get("/video.jpg")
async def video_jpg():
    with latest_frame_lock:
        frame = latest_frame
    if not frame:
        raise HTTPException(404, "No frame")
    return Response(content=frame, media_type="image/jpeg")

@app.get("/video_feed")
async def video_feed():
    boundary = "frameboundary"

    async def gen():
        while True:
            with latest_frame_lock:
                frame = latest_frame
            if frame:
                yield (
                    f"--{boundary}\r\n"
                    "Content-Type: image/jpeg\r\n"
                    f"Content-Length: {len(frame)}\r\n\r\n"
                ).encode('utf-8') + frame + b"\r\n"
                with status_lock:
                    gateway_status["frames_sent"] += 1
            await asyncio.sleep(0.05)  # ~20 fps cap

    return StreamingResponse(gen(), media_type=f"multipart/x-mixed-replace; boundary={boundary}")

# ---------------------------------------------------------------------------
# WebSocket: Control (commands + telemetry)
# ---------------------------------------------------------------------------
@app.websocket("/ws/control")
async def ws_control(ws: WebSocket):
    await ws.accept()
    async with control_ws_lock:
        control_ws_connections.add(ws)
    try:
        await ws.send_text("WELCOME")
        # Task to forward telemetry to this client
        forward_task = asyncio.create_task(_telemetry_forwarder(ws))

        while True:
            msg = await ws.receive_text()
            # Expect raw command line sans newline
            try:
                control_client.send_command(msg)
            except Exception as e:
                await ws.send_text(f"ERROR#SEND#{e}")
    except WebSocketDisconnect:
        pass
    finally:
        forward_task.cancel()
        async with control_ws_lock:
            control_ws_connections.discard(ws)

async def _telemetry_forwarder(ws: WebSocket):
    # Simple fan-out: each client independently reads from a shared queue via a broadcast buffer
    # Implement a lightweight subscriber model: local buffer per connection
    local_queue: asyncio.Queue[str] = asyncio.Queue()

    # Register listener task
    async def distributor():
        while True:
            line = await telemetry_queue.get()
            # Broadcast to all current subscribers (shallow copy for safety)
            async with control_ws_lock:
                targets: List[WebSocket] = list(control_ws_connections)
            for target in targets:
                # Each target gets its own send; errors ignored
                try:
                    await target.send_text(line)
                except Exception:
                    # Drop silently; disconnect handler cleans up
                    pass

    # We only want one global distributor; create if not existing
    if not hasattr(_telemetry_forwarder, "_distributor_started"):
        _telemetry_forwarder._distributor_started = True  # type: ignore
        asyncio.create_task(distributor())

    # Keep connection open; distributor sends directly
    try:
        while True:
            await asyncio.sleep(60)  # Passive; real data pushed by distributor
    except asyncio.CancelledError:
        return

# ---------------------------------------------------------------------------
# WebSocket: Video (binary JPEG frames)
# ---------------------------------------------------------------------------
@app.websocket("/ws/video")
async def ws_video(ws: WebSocket):
    await ws.accept()
    try:
        last_sent_ts = 0
        while True:
            await asyncio.sleep(0.05)  # 20 fps max
            with latest_frame_lock:
                frame = latest_frame
            if frame:
                # Optional: throttle if unchanged; basic version sends always
                await ws.send_bytes(frame)
    except WebSocketDisconnect:
        pass

# ---------------------------------------------------------------------------
# Entry
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run(
        "gateway.gateway:app",
        host="0.0.0.0",
        port=int(os.getenv("GATEWAY_PORT", "9000")),
        reload=False
    )
