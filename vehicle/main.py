"""
Main application for the connected vehicle platform.
"""

from datetime import datetime, timezone
import sys
import os
import asyncio
import logging
from pathlib import Path
import uuid
import json
import uvicorn
import atexit
from typing import Optional
from fastapi import Body
import random

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
from dotenv import load_dotenv
from importlib import import_module

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s'
)

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(override=True)

# Configure loguru with better error handling
try:
    from utils.logging_config import configure_logging
    log_level = os.getenv("LOG_LEVEL", "INFO")
    configure_logging(log_level)
except ImportError as e:
    logger.warning(f"Could not import logging config: {e}")

# Enforce Cosmos DB client availability
cosmos_client = None
try:
    from azure.cosmos_db import cosmos_client
    logger.info("Cosmos DB client imported successfully")
except ImportError as e:
    logger.critical(f"Cosmos DB client is required for this showcase: {e}")
    raise

def _cosmos_status():
    """Small helper to report Cosmos status consistently."""
    enabled = bool(
        getattr(cosmos_client, "endpoint", None)
        and (getattr(cosmos_client, "key", None) or getattr(cosmos_client, "use_aad_auth", False))
    )
    connected = getattr(cosmos_client, "connected", False) if enabled else False
    return enabled, connected

# Track MCP processes for graceful shutdown
MCP_PROCESSES = []

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
                        logger.warning(f"MCP process PID {p.pid} did not terminate, killing...")
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
        if cosmos_client and hasattr(cosmos_client, "close"):
            try:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(cosmos_client.close())
                loop.close()
            except Exception:
                # Ignore errors during interpreter shutdown
                pass
    except Exception:
        pass

@asynccontextmanager
async def lifespan(app):
    logger.info("Starting up the application...")
    # Connect Cosmos
    try:
        if hasattr(cosmos_client, "connect"):
            await cosmos_client.connect()
            logger.info("Cosmos DB connected")
    except Exception as e:
        logger.error(f"Cosmos DB connection failed: {e}")

    # Best-effort router loading (keeps app running even if optional routers are missing)
    for name, modpath in [
        ("Agents", "apis.agent_routes"),
        ("Vehicle Features", "apis.vehicle_feature_routes"),
        ("Remote Access", "apis.remote_access_routes"),
        ("Emergency & Safety", "apis.emergency_routes"),
    ]:
        try:
            module = import_module(modpath)
            app.include_router(module.router, prefix="/api", tags=[name])
            logger.info(f"Loaded router: {name}")
        except Exception as e:
            logger.warning(f"Router not available ({name}): {e}")

    yield

    logger.info("Shutting down the application...")
    try:
        if hasattr(cosmos_client, "close"):
            await cosmos_client.close()
        # Defensive: close any exposed aiohttp session if present
        session = getattr(cosmos_client, "session", None)
        if session:
            closer = getattr(session, "close", None)
            if closer:
                res = closer()
                if asyncio.iscoroutine(res):
                    await res
    except Exception as e:
        logger.error(f"Shutdown error: {e}")
    finally:
        # Always attempt to stop MCP processes
        _stop_mcp_processes()

app = FastAPI(title="Connected Car Platform", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/")
def get_status():
    enabled, connected = _cosmos_status()
    return {
        "status": "Connected Car Platform running",
        "version": "2.0.0",
        "azure_cosmos_enabled": enabled,
        "azure_cosmos_connected": connected,
    }

@app.get("/api/health")
def health_check():
    enabled, connected = _cosmos_status()
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "api": "running",
            "cosmos_db": "connected" if connected else "disconnected"
        }
    }

@app.get("/api/vehicles/{vehicle_id}/command-history")
async def get_vehicle_command_history(vehicle_id: str):
    """Get command history for a specific vehicle"""
    try:
        # Try to ensure Cosmos DB is connected
        cosmos_connected = await cosmos_client.ensure_connected()
        if not cosmos_connected:
            logger.warning("Cosmos DB not available, returning empty command history")
            return []
        
        # Get commands for this specific vehicle
        commands = await cosmos_client.list_commands(vehicle_id)
        
        # Transform commands to the format expected by frontend
        history = []
        for cmd in commands:
            history.append({
                "timestamp": cmd.get("timestamp", ""),
                "command": cmd.get("commandType", "unknown"),
                "status": cmd.get("status", "unknown"),
                "response": cmd.get("response", ""),
                "error": cmd.get("error", "")
            })
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return history
    except Exception as e:
        logger.error(f"Error retrieving command history for vehicle {vehicle_id}: {str(e)}")
        return []


# Submit a command (simulate external system)
@app.post("/api/command")
async def submit_command(command: Command, background_tasks: BackgroundTasks):
    """Submit a command to a vehicle"""
    # Try to ensure Cosmos DB is connected, but continue if it fails
    cosmos_connected = await cosmos_client.ensure_connected()
    if not cosmos_connected:
        logger.warning("Cosmos DB not available, command will be processed without persistence")

    command_id = str(uuid.uuid4())
    command.commandId = command_id
    command.status = "pending"
    # Use the non-deprecated method for getting current UTC time
    command.timestamp = datetime.now(timezone.utc).isoformat()

    # Store command in Cosmos DB
    command_data = command.model_dump()
    await cosmos_client.create_command(command_data)

    # Start background processing
    background_tasks.add_task(process_command_async, command_data)

    return {"commandId": command_id}


# Get command log
@app.get("/api/commands")
async def get_commands(vehicleId: str = None):
    """Get all commands with optional filtering by vehicle ID"""
    # Try to ensure Cosmos DB is connected
    cosmos_connected = await cosmos_client.ensure_connected()
    if not cosmos_connected:
        logger.warning("Cosmos DB not available, returning empty command list")
        return []
    
    try:
        commands = await cosmos_client.list_commands(vehicleId)
        return commands
    except Exception as e:
        logger.error(f"Error retrieving commands: {str(e)}")
        return []


# Get vehicle status (from Cosmos DB only)
@app.get("/api/vehicles/{vehicle_id}/status")
async def get_vehicle_status(vehicle_id: str):
    """Get the current status of a vehicle"""
    try:
        cosmos_connected = await cosmos_client.ensure_connected()
        if not cosmos_connected:
            raise HTTPException(status_code=503, detail="Database service unavailable")
        
        status = await cosmos_client.get_vehicle_status(vehicle_id)
        if not status:
            raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")
        
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting vehicle status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Stream vehicle status updates
@app.get("/api/vehicle/{vehicleId}/status/stream")
async def stream_vehicle_status(vehicleId: str):
    """Stream real-time status updates for a vehicle"""
    async def status_stream_generator():
        agen = None
        cosmos_connected = await cosmos_client.ensure_connected()
        if not cosmos_connected:
            error_status = {"error": "Database service unavailable", "vehicleId": vehicleId}
            yield f"data: {json.dumps(error_status)}\n\n"
            return
        try:
            agen = cosmos_client.subscribe_to_vehicle_status(vehicleId)
            async for status in agen:
                yield f"data: {json.dumps(status)}\n\n"
        except Exception as e:
            logger.error(f"Error in Cosmos DB status streaming: {str(e)}")
            error_status = {"error": "Status streaming unavailable", "vehicleId": vehicleId}
            yield f"data: {json.dumps(error_status)}\n\n"
        finally:
            # Ensure the async generator is properly closed to release underlying resources
            if agen and hasattr(agen, "aclose"):
                try:
                    await agen.aclose()
                except Exception as close_err:
                    logger.debug(f"Ignored stream close error: {close_err}")

    return StreamingResponse(status_stream_generator(), media_type="text/event-stream")


# Removed: get_simulated_vehicles endpoint


# Get notifications
@app.get("/api/notifications")
async def get_notifications(vehicleId: str = None):
    """Get all notifications with optional filtering by vehicle ID"""
    # Try to ensure Cosmos DB is connected
    cosmos_connected = await cosmos_client.ensure_connected()
    if not cosmos_connected:
        logger.warning("Cosmos DB not available, returning empty notification list")
        return []
    
    try:
        notifications = await cosmos_client.list_notifications(vehicleId)
        return notifications
    except Exception as e:
        logger.error(f"Error retrieving notifications: {str(e)}")
        return []


# Add a vehicle profile
@app.post("/api/vehicle")
async def add_vehicle(profile: VehicleProfile):
    """Add a new vehicle profile"""
    # Ensure Cosmos DB is connected
    cosmos_connected = await cosmos_client.ensure_connected()
    if not cosmos_connected:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    return await cosmos_client.create_vehicle(profile.model_dump())


# List all vehicles
@app.get("/api/vehicles")
async def list_vehicles():
    """List all vehicles"""
    cosmos_connected = await cosmos_client.ensure_connected()
    if not cosmos_connected:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    
    try:
        vehicles = await cosmos_client.list_vehicles()
        return vehicles
    except Exception as e:
        logger.error(f"Error retrieving vehicles from Cosmos DB: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve vehicles")


# GET a single vehicle by ID (for fetchVehicleById)
@app.get("/api/vehicles/{vehicle_id}")
async def get_vehicle(vehicle_id: str):
    cosmos_connected = await cosmos_client.ensure_connected() if cosmos_client else False
    if not cosmos_connected:
        raise HTTPException(status_code=503, detail="Database service unavailable")
    try:
        vehicle = await cosmos_client.get_vehicle(vehicle_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle {vehicle_id} not found")
    return vehicle


# Add a service to a vehicle
@app.post("/api/vehicles/{vehicleId}/services")
async def add_service(vehicleId: str, service: Service):
    """Add a service record to a vehicle"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()
    service_data = service.model_dump()
    service_data["vehicleId"] = vehicleId
    service_data["id"] = str(uuid.uuid4())  # Generate unique ID for the service

    return await cosmos_client.create_service(service_data)


# List all services for a vehicle
@app.get("/api/vehicles/{vehicleId}/services")
async def list_services(vehicleId: str):
    """List all services for a vehicle"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()
    return await cosmos_client.list_services(vehicleId)


# Update a service (for updateService)
@app.put("/api/vehicles/{vehicleId}/services/{serviceId}")
async def update_service(vehicleId: str, serviceId: str, service: Service):
    await cosmos_client.ensure_connected()
    data = service.model_dump()
    return await cosmos_client.update_service(vehicleId, serviceId, data)


# Delete a service (for deleteService)
@app.delete("/api/vehicles/{vehicleId}/services/{serviceId}")
async def delete_service(vehicleId: str, serviceId: str):
    await cosmos_client.ensure_connected()
    await cosmos_client.delete_service(vehicleId, serviceId)
    return {"detail": f"Service {serviceId} deleted"}


# Update vehicle status
@app.put("/api/vehicle/{vehicleId}/status")
async def update_vehicle_status(vehicleId: str, status: VehicleStatus):
    """Update the status of a vehicle"""
    # Ensure Cosmos DB is connected
    cosmos_connected = await cosmos_client.ensure_connected()
    if not cosmos_connected:
        raise HTTPException(status_code=503, detail="Database service unavailable")

    # Validate vehicleId
    if not vehicleId or not vehicleId.strip():
        raise HTTPException(status_code=400, detail="Vehicle ID cannot be empty")

    # Ensure vehicleId in path matches the one in the status object
    if status.vehicleId != vehicleId:
        raise HTTPException(
            status_code=400, detail="Vehicle ID in path does not match status object"
        )

    # Convert status to dict for storage
    status_data = status.model_dump()

    # Add timestamp
    status_data["timestamp"] = datetime.now(timezone.utc).isoformat()

    try:
        result = await cosmos_client.update_vehicle_status(vehicleId, status_data)
        logger.info(f"Successfully updated vehicle {vehicleId} status in Cosmos DB")
        return result

    except Exception as e:
        logger.error(f"Error updating vehicle status for {vehicleId}: {str(e)}")
        
        # Determine appropriate HTTP status code based on error type
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=f"Vehicle {vehicleId} not found")
        elif "validation" in str(e).lower():
            raise HTTPException(status_code=400, detail=f"Invalid status data: {str(e)}")
        else:
            raise HTTPException(
                status_code=500, detail=f"Failed to update status: {str(e)}"
            )


# Partial status update (only specific fields)
@app.patch("/api/vehicle/{vehicleId}/status")
async def patch_vehicle_status(vehicleId: str, status_update: dict):
    """Update specific fields of a vehicle's status"""
    # Ensure Cosmos DB is connected
    cosmos_connected = await cosmos_client.ensure_connected()
    if not cosmos_connected:
        raise HTTPException(status_code=503, detail="Database service unavailable")

    # Validate vehicleId
    if not vehicleId:
        raise HTTPException(status_code=400, detail="Vehicle ID is required")

    try:
        # First get current status
        current_status = await get_vehicle_status(vehicleId)
        
        # If no current status exists, create a default one
        if not current_status:
            current_status = {
                "vehicleId": vehicleId,
                "Battery": 0,
                "Temperature": 0,
                "Speed": 0,
                "OilRemaining": 0
            }

        # Update with new values
        current_status.update(status_update)
        
        # Add timestamp
        current_status["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Store updated status in Cosmos DB
        result = await cosmos_client.update_vehicle_status(vehicleId, current_status)
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
        # Ensure Cosmos DB is connected
        if not cosmos_client or not hasattr(cosmos_client, 'ensure_connected'):
            logger.error("Cannot process command: Cosmos client not available")
            return
            
        cosmos_connected = await cosmos_client.ensure_connected()
        if not cosmos_connected:
            logger.error("Cannot process command: Database service unavailable")
            return

        # Extract command details
        command_id = command["commandId"]
        vehicleId = command["vehicleId"]

        # Update command status to "processing"
        try:
            await cosmos_client.update_command(
                command_id=command_id,
                vehicleId=vehicleId,
                updated_data={"status": "processing"},
            )
        except Exception as cosmos_error:
            logger.warning(f"Failed to update command status in Cosmos DB: {str(cosmos_error)}")

        # Process the command (you can add custom logic here for different command types)
        # For now, we'll mark it as completed
        try:
            await cosmos_client.update_command(
                command_id=command_id,
                vehicleId=vehicleId,
                updated_data={
                    "status": "completed",
                    "completion_time": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as cosmos_error:
            logger.warning(f"Failed to update command completion in Cosmos DB: {str(cosmos_error)}")

        # Create notification
        try:
            notification = {
                "id": str(uuid.uuid4()),
                "vehicleId": vehicleId,
                "type": "command_executed",
                "message": f"Command {command['commandType']} executed successfully",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "read": False,
            }
            await cosmos_client.create_notification(notification)
        except Exception as cosmos_error:
            logger.warning(f"Failed to create notification in Cosmos DB: {str(cosmos_error)}")

    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")

        # Update command status to "failed" if possible
        if "command_id" in locals() and "vehicleId" in locals() and cosmos_client:
            try:
                await cosmos_client.update_command(
                    command_id=command_id,
                    vehicleId=vehicleId,
                    updated_data={
                        "status": "failed",
                        "error": str(e),
                        "completion_time": datetime.now(timezone.utc).isoformat(),
                    },
                )
            except Exception as cosmos_error:
                logger.warning(f"Failed to update command failure status: {str(cosmos_error)}")

            # Create failure notification
            try:
                notification = {
                    "id": str(uuid.uuid4()),
                    "vehicleId": vehicleId,
                    "type": "command_failed",
                    "message": f"Failed to process command {command['commandType']}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "read": False,
                    "error": str(e),
                }
                await cosmos_client.create_notification(notification)
            except Exception as cosmos_error:
                logger.warning(f"Failed to create failure notification: {str(cosmos_error)}")

# Create a notification (for createNotification)
@app.post("/api/notifications")
async def create_notification(notification: dict):
    await cosmos_client.ensure_connected()
    await cosmos_client.create_notification(notification)
    return notification

# Mark a notification as read (for markNotificationRead)
@app.put("/api/notifications/{notificationId}/read")
async def mark_notification_read(notificationId: str):
    await cosmos_client.ensure_connected()
    updated = await cosmos_client.mark_notification_read(notificationId)
    return updated

# Delete a notification (for deleteNotification)
@app.delete("/api/notifications/{notificationId}")
async def delete_notification(notificationId: str):
    await cosmos_client.ensure_connected()
    await cosmos_client.delete_notification(notificationId)
    return {"detail": f"Notification {notificationId} deleted"}


# Dev: seed a test vehicle and status
@app.post("/api/dev/seed")
async def seed_dev_data(vehicleId: Optional[str] = None):
    """Create a test vehicle profile and initial status for development."""
    # Ensure DB is available
    cosmos_connected = await cosmos_client.ensure_connected()
    if not cosmos_connected:
        raise HTTPException(status_code=503, detail="Database service unavailable")

    # Use provided or default test vehicle ID
    vehicle_id = (vehicleId or "a640f210-dca4-4db7-931a-9f119bbe54e0").strip()

    created_vehicle = False
    try:
        # Check if vehicle exists
        vehicle = await cosmos_client.get_vehicle(vehicle_id)
        if not vehicle:
            # Create a minimal profile (fields commonly used by UI)
            profile = {
                "VehicleId": vehicle_id,
                "vehicleId": vehicle_id,
                "Make": "Demo",
                "Model": "Car",
                "Year": 2024,
                "Status": "Active",
                "LastLocation": { "Latitude": 43.6532, "Longitude": -79.3832 }
            }
            await cosmos_client.create_vehicle(profile)
            created_vehicle = True

        # Seed/Upsert vehicle status
        status_data = {
            "vehicleId": vehicle_id,
            "Battery": 82,
            "Temperature": 36,
            "Speed": 0,
            "OilRemaining": 75,
            "Odometer": 12456,
            "location": { "latitude": 43.6532, "longitude": -79.3832 },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        await cosmos_client.update_vehicle_status(vehicle_id, status_data)

        return {
            "vehicleId": vehicle_id,
            "createdVehicle": created_vehicle,
            "statusSeeded": True
        }
    except Exception as e:
        logger.error(f"Seed failed for {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Seeding failed: {str(e)}")


# Track last seed summary (dev utility)
LAST_SEED_SUMMARY = {}

@app.post("/api/dev/seed/bulk")
async def seed_dev_data_bulk(config: dict = Body(default=None)):
    """
    Bulk-generate test data and insert into Cosmos DB.
    Body (optional):
    {
      "vehicles": 10,
      "commandsPerVehicle": 2,
      "notificationsPerVehicle": 2,
      "servicesPerVehicle": 1,
      "statusesPerVehicle": 1
    }
    """
    # Ensure DB is available
    cosmos_connected = await cosmos_client.ensure_connected()
    if not cosmos_connected:
        raise HTTPException(status_code=503, detail="Database service unavailable")

    # Defaults
    cfg = {
        "vehicles": 10,
        "commandsPerVehicle": 2,
        "notificationsPerVehicle": 2,
        "servicesPerVehicle": 1,
        "statusesPerVehicle": 1,
    }
    if isinstance(config, dict):
        cfg.update({k: v for k, v in config.items() if k in cfg and isinstance(v, int) and v >= 0})

    created = {
        "vehicles": 0,
        "statuses": 0,
        "services": 0,
        "commands": 0,
        "notifications": 0,
        "vehicleIds": []
    }

    # Simple test data pools
    makes = ["Demo", "Tesla", "Toyota", "Ford", "BMW"]
    models = ["Car", "Model 3", "RAV4", "F-150", "X3"]

    try:
        for _ in range(cfg["vehicles"]):
            vehicle_id = str(uuid.uuid4())

            # Minimal vehicle profile used by UI and DB (ensure partition key)
            profile = {
                "id": str(uuid.uuid4()),
                "VehicleId": vehicle_id,
                "vehicleId": vehicle_id,  # partition key
                "Make": random.choice(makes),
                "Model": random.choice(models),
                "Year": random.choice([2021, 2022, 2023, 2024]),
                "Status": random.choice(["Active", "Inactive", "Maintenance"]),
                "LastLocation": {"Latitude": 43.6532, "Longitude": -79.3832}
            }
            await cosmos_client.create_vehicle(profile)
            created["vehicles"] += 1
            created["vehicleIds"].append(vehicle_id)

            # Status history
            for _n in range(cfg["statusesPerVehicle"]):
                status_data = {
                    "vehicleId": vehicle_id,  # partition key
                    "Battery": random.randint(50, 100),
                    "Temperature": random.randint(15, 40),
                    "Speed": random.choice([0, random.randint(10, 120)]),
                    "OilRemaining": random.randint(40, 100),
                    "Odometer": random.randint(1000, 150000),
                    "location": {"latitude": 43.6532, "longitude": -79.3832},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await cosmos_client.update_vehicle_status(vehicle_id, status_data)
                created["statuses"] += 1

            # Services
            for _n in range(cfg["servicesPerVehicle"]):
                service = {
                    "id": str(uuid.uuid4()),
                    "vehicleId": vehicle_id,  # partition key
                    "ServiceCode": random.choice(["OIL_CHANGE", "TIRE_ROTATION", "BRAKE_SERVICE"]),
                    "Description": "Auto-generated test service",
                    "StartDate": datetime.now(timezone.utc).isoformat(),
                    "EndDate": datetime.now(timezone.utc).isoformat(),
                    "NextServiceDate": datetime.now(timezone.utc).isoformat(),
                    "mileage": random.randint(1000, 150000),
                    "nextServiceMileage": random.randint(1000, 150000) + 5000,
                    "cost": round(random.uniform(50.0, 500.0), 2),
                    "location": "Service Center 1",
                    "technician": "Tech A",
                    "invoiceNumber": f"INV-{random.randint(10000, 99999)}",
                    "serviceStatus": "Completed",
                    "serviceType": random.choice(["Scheduled", "Repair"]),
                }
                await cosmos_client.create_service(service)
                created["services"] += 1

            # Commands
            for _n in range(cfg["commandsPerVehicle"]):
                command = {
                    "id": str(uuid.uuid4()),
                    "commandId": str(uuid.uuid4()),
                    "vehicleId": vehicle_id,  # partition key
                    "commandType": random.choice(["LOCK_DOORS", "UNLOCK_DOORS", "START_ENGINE", "STOP_ENGINE"]),
                    "parameters": {},
                    "status": random.choice(["Sent", "Processing", "Completed"]),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await cosmos_client.create_command(command)
                created["commands"] += 1

            # Notifications
            for _n in range(cfg["notificationsPerVehicle"]):
                notification = {
                    "id": str(uuid.uuid4()),
                    "vehicleId": vehicle_id,  # partition key
                    "type": random.choice(["service_reminder", "low_battery_alert", "speed_alert"]),
                    "message": "Auto-generated test notification",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "read": False,
                    "severity": random.choice(["low", "medium", "high"]),
                    "source": random.choice(["Vehicle", "System"]),
                    "actionRequired": False,
                }
                await cosmos_client.create_notification(notification)
                created["notifications"] += 1

        summary = {
            "ok": True,
            "config": cfg,
            "created": created,
            "azure_cosmos_connected": True
        }
        # Save last seed summary for status endpoint
        global LAST_SEED_SUMMARY
        LAST_SEED_SUMMARY = summary
        return summary

    except Exception as e:
        logger.error(f"Bulk seed failed: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk seeding failed: {str(e)}")


@app.get("/api/dev/seed/status")
async def seed_status():
    """Return the last bulk seed summary (if any) and current Cosmos connectivity."""
    enabled, connected = _cosmos_status()
    return {
        "azure_cosmos_enabled": enabled,
        "azure_cosmos_connected": connected,
        "last_seed": LAST_SEED_SUMMARY or {}
    }


# Top-level entry points for multiprocessing
def run_weather_process():
    """Entry for MCP weather server."""
    import sys
    from pathlib import Path
    # Add the project root to Python path for the subprocess
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    try:
        from plugin.mcp_weather_server import start_weather_server
        import asyncio
        asyncio.run(start_weather_server(host="0.0.0.0", port=8001))
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Weather server failed to start: {e}")

def run_traffic_process():
    """Entry for MCP traffic server."""
    import sys
    from pathlib import Path
    # Add the project root to Python path for the subprocess
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    try:
        from plugin.mcp_traffic_server import start_traffic_server
        import asyncio
        asyncio.run(start_traffic_server(host="0.0.0.0", port=8002))
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Traffic server failed to start: {e}")

def run_poi_process():
    """Entry for MCP POI server."""
    import sys
    from pathlib import Path
    # Add the project root to Python path for the subprocess
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    try:
        from plugin.mcp_poi_server import start_poi_server
        import asyncio
        asyncio.run(start_poi_server(host="0.0.0.0", port=8003))
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"POI server failed to start: {e}")

def run_navigation_process():
    """Entry for MCP navigation server."""
    import sys
    from pathlib import Path
    # Add the project root to Python path for the subprocess
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))
    
    try:
        from plugin.mcp_navigation_server import start_navigation_server
        import asyncio
        asyncio.run(start_navigation_server(host="0.0.0.0", port=8004))
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Navigation server failed to start: {e}")

if __name__ == "__main__":
    # Initialize
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    logger.info(f"Starting server at http://{host}:{port}")
    ENABLE_MCP = True

    # Launch MCP servers
    if ENABLE_MCP == True:
        try:
            from multiprocessing import Process, set_start_method
            set_start_method("spawn", force=True)
            for name, target, mcp_port in [
                ("weather", run_weather_process, 8001),
                ("traffic", run_traffic_process, 8002),
                ("poi", run_poi_process, 8003),
                ("navigation", run_navigation_process, 8004),
            ]:
                try:
                    logger.info(f"Starting MCP ({name}) server on port {mcp_port}")
                    p = Process(target=target, daemon=True)
                    p.start()
                    MCP_PROCESSES.append(p)  # track for shutdown
                    logger.info(f"{name.title()} MCP server PID: {p.pid}")
                except Exception as e:
                    logger.error(f"Failed to start {name} MCP server: {e}")
        except Exception as e:
            logger.error(f"Failed to start MCP servers: {e}")
    else:
        logger.info("MCP servers disabled")

    # Start the FastAPI app
    logger.info(f"Starting API server at http://{host}:{port}")
    try:
        uvicorn.run("main:app", host=host, port=port, reload=False)
    except Exception as e:
        logger.critical(f"API server failed to start: {e}")
        raise