"""
Main application for the connected vehicle platform.
"""

import sys
import os
import asyncio
import logging
import uuid
import json
import uvicorn
import atexit
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
import socket
import http.client  # added for health probing
import multiprocessing

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from models.command import Command
from models.vehicle_profile import VehicleProfile
from models.service import Service
from models.status import VehicleStatus
from models.api_responses import (
    InfoResponse,
    HealthResponse,
    HealthServices,
    CommandHistoryItem,
    CommandSubmitResponse,
    Notification,
    CreateNotificationResponse,
    MarkNotificationReadResponse,
    GenericDetailResponse,
)
from models.notification import Notification as NotificationModel
from dotenv import load_dotenv
from importlib import import_module
from azure.azure_auth import AzureADMiddleware
from fastapi import Request
from azure.cosmos_db import get_cosmos_client
from plugin.mcp_weather_server import start_weather_server
from plugin.mcp_traffic_server import start_traffic_server
from plugin.mcp_poi_server import start_poi_server
from plugin.mcp_navigation_server import start_navigation_server

# Load environment variables first
load_dotenv(override=True)

# Configure logging with single instance check
log_level = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
    force=True,  # Override any existing logging configuration
)

logger = logging.getLogger(__name__)

# Prevent duplicate logging from uvicorn
logging.getLogger("uvicorn.access").disabled = True
logging.getLogger("uvicorn").setLevel(logging.WARNING)

# Configure loguru with better error handling
from utils.logging_config import configure_logging

configure_logging(log_level)

# Track MCP processes for graceful shutdown
MCP_PROCESSES = []
_SERVER_INSTANCE_STARTED = False


def _stop_mcp_processes(timeout: float = 5.0):
    """Gracefully stop MCP subprocesses."""
    try:
        for p in MCP_PROCESSES:
            try:
                if p.is_alive():
                    logger.info(f"Stopping MCP process PID {p.pid}...")
                    p.terminate()
                    p.join(timeout)
                    if p.is_alive():
                        logger.warning(
                            f"MCP process PID {p.pid} did not terminate, killing..."
                        )
                        p.kill()
                        p.join(2.0)
            except Exception as e:
                logger.debug(f"Error stopping MCP process: {e}")
    except Exception:
        pass


# Ensure cleanup on unexpected interpreter exit (best-effort)
@atexit.register
def _cleanup_at_exit():
    try:
        # Stop MCP servers first
        _stop_mcp_processes()
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app):
    logger.info("Starting up the application...")
    # Lazy create only once
    if not hasattr(app.state, "cosmos_client"):
        app.state.cosmos_client = get_cosmos_client()  # unified singleton
        logger.info("Cosmos DB client instantiated (lifespan)")
    client = app.state.cosmos_client

    # Connect
    try:
        if hasattr(client, "connect"):
            await client.connect()
            logger.info("Cosmos DB connected")
    except Exception as e:
        logger.error(f"Cosmos DB connection failed: {e}")

    # Best-effort router loading (keeps app running even if optional routers are missing)
    for name, modpath in [
        ("Agents", "apis.agent_routes"),
        ("Vehicle Features", "apis.vehicle_feature_routes"),
        ("Remote Access", "apis.remote_access_routes"),
        ("Speech", "apis.speech_routes"),
        ("Emergency & Safety", "apis.emergency_routes"),
        ("Dev Seed", "apis.seed_routes"),  # Dev: Test data
    ]:
        try:
            module = import_module(modpath)
            app.include_router(module.router, prefix="/api", tags=[name])
            logger.info(f"Loaded router: {name}")
        except Exception as e:
            # Improved diagnostics: include full traceback at debug level
            logger.warning(f"Router not available ({name}): {e}")
            logger.debug("Full import traceback for router '%s'", name, exc_info=True)

    yield
    logger.info("Shutting down the application...")
    try:
        if hasattr(client, "close"):
            await client.close()
        # Defensive: close any exposed aiohttp session if present
        session = getattr(client, "session", None)
        if session:
            closer = getattr(session, "close", None)
            if closer:
                res = closer()
                if asyncio.iscoroutine(res):
                    await res
    except Exception as e:
        logger.error(f"Shutdown error: {e}")
    finally:
        if os.getenv("ENABLE_MCP", "true").lower() == "true":
            _stop_mcp_processes()


app = FastAPI(title="Connected Car Platform", lifespan=lifespan)

# Restore middlewares (Azure AD auth first, then CORS)
app.add_middleware(AzureADMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
)


def _cosmos_status():
    try:
        client = get_cosmos_client()
    except Exception:
        return False, False
    enabled = bool(
        getattr(client, "endpoint", None)
        and (getattr(client, "key", None) or getattr(client, "use_aad_auth", False))
    )
    connected = getattr(client, "connected", False) if enabled else False
    return enabled, connected


@app.middleware("http")
async def log_user_requests(request: Request, call_next):
    """Log API calls with authenticated user and correlation id."""
    corr_id = request.headers.get("X-Client-Request-Id") or str(uuid4())
    user_id = request.headers.get("X-User-Name", "anonymous")

    # Always set user_id on request state for consistency
    request.state.user_id = user_id

    # Log the request (even for anonymous users in development)
    if (
        user_id != "anonymous"
        or os.getenv("LOG_ANONYMOUS_REQUESTS", "false").lower() == "true"
    ):
        logger.info(
            f"[INFO] User request: {user_id}, Correlation ID: {corr_id}, API Endpoint: {request.url.path}, Request Method: {request.method}"
        )

    try:
        response = await call_next(request)
        response.headers.setdefault("X-Client-Request-Id", corr_id)
        return response
    except Exception as e:
        logger.error(f"Error in request middleware: {str(e)}")
        # Re-raise the exception to let FastAPI handle it properly
        raise


@app.get("/api/info", response_model=InfoResponse)
def get_status():
    enabled, connected = _cosmos_status()
    return InfoResponse(
        status="Connected Car Platform running",
        version="2.0.0",
        azure_cosmos_enabled=enabled,
        azure_cosmos_connected=connected,
    )


@app.get("/api/health", response_model=HealthResponse)
def health_check():
    enabled, connected = _cosmos_status()
    mcp_status = _collect_mcp_status()
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc),
        services=HealthServices(
            api="running",
            cosmos_db="connected" if connected else "disconnected",
            mcp_weather=mcp_status["weather"],
            mcp_traffic=mcp_status["traffic"],
            mcp_poi=mcp_status["poi"],
            mcp_navigation=mcp_status["navigation"],
        ),
    )


@app.get(
    "/api/vehicles/{vehicle_id}/command-history",
    response_model=list[CommandHistoryItem],
)
async def get_vehicle_command_history(vehicle_id: str):
    """Get command history for a specific vehicle"""
    client = get_cosmos_client()
    cosmos_connected = await client.ensure_connected()
    if not cosmos_connected:
        logger.warning("Cosmos DB not available, returning empty command history")
        return []
    commands = await client.list_commands(vehicle_id)
    history = [
        CommandHistoryItem(
            timestamp=cmd.get("timestamp", ""),
            command=cmd.get("command_type", "unknown"),
            status=cmd.get("status", "unknown"),
            response=cmd.get("response", ""),
            error=cmd.get("error", ""),
        )
        for cmd in commands
    ]
    history.sort(key=lambda x: x.timestamp, reverse=True)
    return history


# Submit a command (simulate external system)
@app.post("/api/command", response_model=CommandSubmitResponse)
async def submit_command(command: Command, background_tasks: BackgroundTasks):
    """Submit a command to a vehicle"""
    client = get_cosmos_client()
    cosmos_connected = await client.ensure_connected()
    if not cosmos_connected:
        logger.warning(
            "Cosmos DB not available, command will be processed without persistence"
        )
    command_id = str(uuid.uuid4())
    command.command_id = command_id
    command.status = "pending"
    command.timestamp = datetime.now(timezone.utc).isoformat()
    command_data = command.model_dump(by_alias=True)  # use camelCase per CamelModel
    await client.create_command(command_data)
    background_tasks.add_task(process_command_async, command_data)
    return CommandSubmitResponse(command_id=command_id)


# Get command log
@app.get("/api/commands", response_model=list[Command])
async def get_commands(vehicle_id: str = None):  # renamed query param
    """Get all commands with optional filtering by vehicle ID"""
    client = get_cosmos_client()
    cosmos_connected = await client.ensure_connected()
    if not cosmos_connected:
        logger.warning("Cosmos DB not available, returning empty command list")
        return []
    try:
        return await client.list_commands(vehicle_id)
    except Exception as e:
        logger.error(f"Error retrieving commands: {str(e)}")
        return []


# Get vehicle status (from Cosmos DB only)
@app.get("/api/vehicles/{vehicle_id}/status", response_model=VehicleStatus)
async def get_vehicle_status(vehicle_id: str):
    """Get the current status of a vehicle"""
    client = get_cosmos_client()
    try:
        cosmos_connected = await client.ensure_connected()
        if not cosmos_connected:
            raise HTTPException(status_code=503, detail="Database service unavailable")

        status = await client.get_vehicle_status(vehicle_id)
        if not status:
            raise HTTPException(
                status_code=404, detail=f"Vehicle {vehicle_id} not found"
            )

        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting vehicle status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Stream vehicle status updates
@app.get("/api/vehicle/{vehicle_id}/status/stream")  # path param renamed
async def stream_vehicle_status(vehicle_id: str):
    """Stream real-time status updates for a vehicle"""

    async def status_stream_generator():
        agen = None
        client = get_cosmos_client()
        cosmos_connected = await client.ensure_connected()
        if not cosmos_connected:
            error_status = {
                "error": "Database service unavailable",
                "vehicle_id": vehicle_id,
            }
            yield f"data: {json.dumps(error_status)}\n\n"
            return
        try:
            agen = client.subscribe_to_vehicle_status(vehicle_id)
            async for status in agen:
                yield f"data: {json.dumps(status)}\n\n"
        except Exception as e:
            logger.error(f"Error in Cosmos DB status streaming: {str(e)}")
            error_status = {
                "error": "Status streaming unavailable",
                "vehicle_id": vehicle_id,
            }
            yield f"data: {json.dumps(error_status)}\n\n"
        finally:
            # Ensure the async generator is properly closed to release underlying resources
            if agen and hasattr(agen, "aclose"):
                try:
                    await agen.aclose()
                except Exception as close_err:
                    logger.debug(f"Ignored stream close error: {close_err}")

    response = StreamingResponse(
        status_stream_generator(), media_type="text/event-stream"
    )
    # Add CORS headers specifically for EventSource
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET"
    response.headers["Access-Control-Allow-Headers"] = "Cache-Control"
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"

    return response


# Get notifications
@app.get("/api/notifications", response_model=list[Notification])
async def get_notifications(vehicle_id: str = None):  # renamed query param
    """Get all notifications with optional filtering by vehicle ID"""
    client = get_cosmos_client()
    cosmos_connected = await client.ensure_connected()
    if not cosmos_connected:
        logger.warning("Cosmos DB not available, returning empty notification list")
        return []
    try:
        return await client.list_notifications(vehicle_id)
    except Exception as e:
        logger.error(f"Error retrieving notifications: {str(e)}")
        return []


# Add a vehicle profile
@app.post("/api/vehicle", response_model=VehicleProfile)
async def add_vehicle(profile: VehicleProfile):
    """Add a new vehicle profile"""
    client = get_cosmos_client()
    cosmos_connected = await client.ensure_connected()
    if not cosmos_connected:
        raise HTTPException(status_code=503, detail="Database service unavailable")

    return await client.create_vehicle(profile.model_dump())


# List all vehicles
@app.get("/api/vehicles", response_model=list[VehicleProfile])
async def list_vehicles():
    """List all vehicles"""
    client = get_cosmos_client()
    cosmos_connected = await client.ensure_connected()
    if not cosmos_connected:
        raise HTTPException(status_code=503, detail="Database service unavailable")

    try:
        vehicles = await client.list_vehicles()
        return vehicles
    except Exception as e:
        logger.error(f"Error retrieving vehicles from Cosmos DB: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve vehicles")


# GET a single vehicle by ID (for fetchVehicleById)
@app.get("/api/vehicles/{vehicle_id}", response_model=VehicleProfile)
async def get_vehicle(vehicle_id: str):
    client = get_cosmos_client()
    cosmos_connected = await client.ensure_connected() if client else False
    if not cosmos_connected:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    try:
        vehicle = await client.get_vehicle(vehicle_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")
    return vehicle


# Add a service to a vehicle
@app.post("/api/vehicles/{vehicle_id}/services", response_model=Service)
async def add_service(vehicle_id: str, service: Service):
    """Add a service record to a vehicle"""
    client = get_cosmos_client()
    # Ensure Cosmos DB is connected
    await client.ensure_connected()
    service_data = service.model_dump()
    service_data["vehicle_id"] = vehicle_id
    service_data["id"] = str(uuid.uuid4())  # Generate unique ID for the service

    return await client.create_service(service_data)


# List all services for a vehicle
@app.get("/api/vehicles/{vehicle_id}/services", response_model=list[Service])
async def list_services(vehicle_id: str):
    """List all services for a vehicle"""
    client = get_cosmos_client()
    # Ensure Cosmos DB is connected
    await client.ensure_connected()
    return await client.list_services(vehicle_id)


# Update a service
@app.put("/api/vehicles/{vehicle_id}/services/{serviceId}", response_model=Service)
async def update_service(vehicle_id: str, serviceId: str, service: Service):
    client = get_cosmos_client()
    await client.ensure_connected()
    data = service.model_dump()
    return await client.update_service(vehicle_id, serviceId, data)


# Delete a service
@app.delete(
    "/api/vehicles/{vehicle_id}/services/{serviceId}",
    response_model=GenericDetailResponse,
)
async def delete_service(vehicle_id: str, serviceId: str):
    client = get_cosmos_client()
    await client.ensure_connected()
    await client.delete_service(vehicle_id, serviceId)
    return GenericDetailResponse(detail=f"Service {serviceId} deleted successfully")


# Update vehicle status
@app.put("/api/vehicle/{vehicle_id}/status", response_model=VehicleStatus)
async def update_vehicle_status(vehicle_id: str, status: VehicleStatus):
    """Update the status of a vehicle"""
    client = get_cosmos_client()
    cosmos_connected = await client.ensure_connected()
    if not cosmos_connected:
        raise HTTPException(status_code=503, detail="Database service unavailable")

    # Validate vehicleId
    if not vehicle_id or not vehicle_id.strip():
        raise HTTPException(status_code=400, detail="Vehicle ID cannot be empty")

    # Ensure vehicleId in path matches the one in the status object
    if status.vehicle_id != vehicle_id:
        raise HTTPException(
            status_code=400, detail="Vehicle ID in path does not match status object"
        )

    # Convert status to dict for storage
    status_data = status.model_dump(by_alias=True)

    # Add timestamp
    status_data["timestamp"] = datetime.now(timezone.utc).isoformat()

    try:
        result = await client.update_vehicle_status(vehicle_id, status_data)
        logger.info(f"Successfully updated vehicle {vehicle_id} status in Cosmos DB")
        return result

    except Exception as e:
        logger.error(f"Error updating vehicle status for {vehicle_id}: {str(e)}")

        # Determine appropriate HTTP status code based on error type
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=404, detail=f"Vehicle {vehicle_id} not found"
            )
        elif "validation" in str(e).lower():
            raise HTTPException(
                status_code=400, detail=f"Invalid status data: {str(e)}"
            )
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to update status: {str(e)}"
            )


# Partial status update
@app.patch("/api/vehicle/{vehicle_id}/status", response_model=VehicleStatus)
async def patch_vehicle_status(vehicle_id: str, status_update: dict):
    """Update specific fields of a vehicle's status"""
    client = get_cosmos_client()
    # Ensure Cosmos DB is connected
    cosmos_connected = await client.ensure_connected()
    if not cosmos_connected:
        raise HTTPException(status_code=503, detail="Database service unavailable")

    # Validate vehicleId
    if not vehicle_id:
        raise HTTPException(status_code=400, detail="Vehicle ID is required")

    try:
        # First get current status
        current_status = await get_vehicle_status(vehicle_id)

        # If no current status exists, create a default one
        if not current_status:
            current_status = {"vehicle_id": vehicle_id}
        current_status.update(status_update)
        current_status["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Store updated status in Cosmos DB
        result = await client.update_vehicle_status(vehicle_id, current_status)
        return result

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error updating vehicle status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update status: {str(e)}"
        )


# Async background task to process commands
async def process_command_async(command):
    """Process a command asynchronously"""
    try:
        client = get_cosmos_client()
    except Exception:
        logger.error("Cannot process command: Cosmos client not initialized")
        return

    # Ensure Cosmos DB is connected
    cosmos_connected = await client.ensure_connected()
    if not cosmos_connected:
        logger.error("Cannot process command: Database service unavailable")
        return

    # Extract command details
    command_id = command["command_id"]
    vehicle_id = command["vehicle_id"]
    try:
        await client.update_command(
            command_id=command_id,
            updated_data={"status": "processing"},
        )
    except Exception as cosmos_error:
        logger.warning(
            f"Failed to update command status in Cosmos DB: {str(cosmos_error)}"
        )
    try:
        await client.update_command(
            command_id=command_id,
            updated_data={
                "status": "completed",
                "completion_time": datetime.now(timezone.utc).isoformat(),
            },
        )
    except Exception as cosmos_error:
        logger.warning(
            f"Failed to update command completion in Cosmos DB: {str(cosmos_error)}"
        )
    try:
        notif = NotificationModel(
            id=str(uuid.uuid4()),
            vehicle_id=vehicle_id,
            type="command_executed",
            message=f"Command {command.get('command_type','unknown')} executed successfully",
            timestamp=datetime.now(timezone.utc).isoformat(),
            read=False,
            severity="low",
            source="System",
            action_required=False,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        # Persist using the model's serialization (aligns with other uses in the codebase)
        await client.create_notification(notif.model_dump())

    except Exception as cosmos_error:
        logger.warning(
            f"Failed to create notification in Cosmos DB: {str(cosmos_error)}"
        )
    logger.info(f"Successfully processed command {command_id} for vehicle {vehicle_id}")


# Create a notification (for createNotification)
@app.post("/api/notifications", response_model=CreateNotificationResponse)
async def create_notification(notification: dict):
    client = get_cosmos_client()
    await client.ensure_connected()
    result = await client.create_notification(notification)
    nid = notification.get("id")
    return CreateNotificationResponse(id=nid, status="created", data=result)


# Mark a notification as read (for markNotificationRead)
@app.put(
    "/api/notifications/{NotificationId}/read",
    response_model=MarkNotificationReadResponse,
)
async def mark_notification_read(NotificationId: str):
    client = get_cosmos_client()
    await client.ensure_connected()
    updated = await client.mark_notification_read(NotificationId)
    if not updated:
        raise HTTPException(
            status_code=404, detail=f"Notification {NotificationId} not found"
        )
    return MarkNotificationReadResponse(
        id=NotificationId, status="marked_as_read", data=updated
    )


# Delete a notification (for deleteNotification)
@app.delete("/api/notifications/{NotificationId}", response_model=GenericDetailResponse)
async def delete_notification(NotificationId: str):
    client = get_cosmos_client()
    await client.ensure_connected()
    await client.delete_notification(NotificationId)
    return GenericDetailResponse(
        detail=f"Notification {NotificationId} deleted successfully"
    )


def _is_port_open(host: str, port: int, timeout: float = 0.25) -> bool:
    """Check if a TCP port is accepting connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _collect_mcp_status() -> dict:
    """
    Probe MCP sidecar health endpoints.
    Returns dict with keys: weather, traffic, poi, navigation.
    Status values: 'running', 'down', or 'disabled'.
    """
    if os.getenv("ENABLE_MCP", "true").lower() != "true":
        return {k: "disabled" for k in ("weather", "traffic", "poi", "navigation")}

    host = "127.0.0.1"
    services = {
        "weather": 8001,
        "traffic": 8002,
        "poi": 8003,
        "navigation": 8004,
    }
    results: dict[str, str] = {}
    for name, port in services.items():
        status = "down"
        if _is_port_open(host, port):
            try:
                conn = http.client.HTTPConnection(host, port, timeout=0.4)
                conn.request("GET", "/health")
                resp = conn.getresponse()
                body = resp.read(256)  # small read
                conn.close()
                if resp.status == 200:
                    # Accept plain OK or small JSON with status ok/OK
                    try:
                        txt = body.decode("utf-8", errors="ignore").strip()
                        if not txt:
                            pass
                        elif txt.lower() == "ok":
                            status = "running"
                        else:
                            # Try JSON
                            try:
                                parsed = json.loads(txt)
                                s = str(parsed.get("status", "")).lower()
                                if s == "ok":
                                    status = "running"
                            except Exception:
                                # Non-JSON but contains OK token
                                if "ok" in txt.lower():
                                    status = "running"
                    except Exception:
                        pass
            except Exception:
                pass
        results[name] = status
    return results


def _check_port_availability(host: str, port: int) -> None:
    """Check if the specified port is available for binding.

    Args:
        host: Host address to bind to
        port: Port number to check

    Raises:
        SystemExit: If port is already in use
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
    except OSError:
        logger.error(
            f"Port {port} is already in use. Another server instance may be running."
        )
        sys.exit(1)


def _start_mcp_process(func, name: str):
    """Start an MCP sidecar server in its own process and track it."""
    try:
        p = multiprocessing.Process(target=func, name=name, daemon=True)
        p.start()
        MCP_PROCESSES.append(p)
        logger.info(f"Started {name} (PID {p.pid})")
    except Exception as e:
        logger.warning(f"Failed to start {name}: {e}")


if __name__ == "__main__":
    # Prevent multiple server instances
    if _SERVER_INSTANCE_STARTED:
        logger.warning("Server instance already started, skipping...")
        sys.exit(0)

    _SERVER_INSTANCE_STARTED = True

    # Initialize
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))

    # Check if port is already in use
    _check_port_availability(host, port)

    logger.info(f"Starting Connected Car Platform server at http://{host}:{port}")
    ENABLE_MCP = os.getenv("ENABLE_MCP", "true").lower() == "true"
    if ENABLE_MCP:
        logger.info("MCP integration enabled")
        _start_mcp_process(start_weather_server, "mcp_weather")
        _start_mcp_process(start_navigation_server, "mcp_navigation")
        _start_mcp_process(start_traffic_server, "mcp_traffic")
        _start_mcp_process(start_poi_server, "mcp_poi")

    # Start the FastAPI app with explicit configuration
    logger.info("Initializing FastAPI application...")
    try:
        # Explicitly disable reload and set worker count to 1
        uvicorn.run(
            app,
            host=host,
            port=port,
            # reload=False,  # Explicitly disable auto-reload
            workers=1,  # Single worker process
            log_level=log_level.lower(),
        )
    except Exception as e:
        logger.critical(f"API server failed to start: {e}")
        raise
    finally:
        _SERVER_INSTANCE_STARTED = False
