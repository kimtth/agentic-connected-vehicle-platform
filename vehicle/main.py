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

# Import Azure modules with error handling
cosmos_client = None
try:
    from azure.cosmos_db import cosmos_client
    logger.info("Cosmos DB client imported successfully")
except ImportError as e:
    logger.error(f"Could not import cosmos_client: {e}")
    # Create a mock client to prevent crashes
    class MockCosmosClient:
        connected = False
        endpoint = None
        key = None
        use_aad_auth = False
        
        async def connect(self): pass
        async def close(self): pass
        async def ensure_connected(self): return False
        
    cosmos_client = MockCosmosClient()

# Import agent routes with better error handling and timeout
agent_router = None
feature_router = None
remote_router = None
emergency_router = None

async def import_routes_with_timeout():
    """Import routes with timeout to prevent hanging"""
    try:
        import asyncio
        from fastapi import APIRouter
        
        # Create default empty routers first
        global agent_router, feature_router, remote_router, emergency_router
        agent_router = APIRouter()
        feature_router = APIRouter()
        remote_router = APIRouter()
        emergency_router = APIRouter()
        
        # Try to import actual routes with timeout
        try:
            async with asyncio.timeout(10):  # 10 second timeout
                import importlib
                
                agent_routes_module = importlib.import_module('apis.agent_routes')
                feature_routes_module = importlib.import_module('apis.vehicle_feature_routes') 
                remote_routes_module = importlib.import_module('apis.remote_access_routes')
                emergency_routes_module = importlib.import_module('apis.emergency_routes')
                
                agent_router = agent_routes_module.router
                feature_router = feature_routes_module.router
                remote_router = remote_routes_module.router
                emergency_router = emergency_routes_module.router
                
                logger.info("All route modules imported successfully")
        except asyncio.TimeoutError:
            logger.error("Route import timed out after 10 seconds - using empty routers")
        except Exception as e:
            logger.error(f"Error importing routes: {str(e)} - using empty routers")
            
    except Exception as e:
        logger.error(f"Critical error in route import: {str(e)}")

@asynccontextmanager
async def lifespan(app):
    # Startup: import routes, connect DB, then include routers
    logger.info("Starting up the application...")

    try:
        # Import routes first
        await import_routes_with_timeout()
        
        # Initialize Cosmos DB connection with timeout
        if cosmos_client and hasattr(cosmos_client, 'connect'):
            try:
                await asyncio.wait_for(cosmos_client.connect(), timeout=5.0)
                logger.info("Cosmos DB connected successfully")
            except asyncio.TimeoutError:
                logger.error("Cosmos DB connection timed out")
            except Exception as e:
                logger.error(f"Cosmos DB connection failed: {e}")
    except Exception as e:
        logger.error(f"Startup error: {e}")

    # include routers under /api
    if agent_router:
        app.include_router(agent_router, prefix="/api", tags=["Agents"])
    if feature_router:
        app.include_router(feature_router, prefix="/api", tags=["Vehicle Features"])
    if remote_router:
        app.include_router(remote_router, prefix="/api", tags=["Remote Access"])
    if emergency_router:
        app.include_router(emergency_router, prefix="/api", tags=["Emergency & Safety"])
    
    yield  # app is now running

    # Shutdown: cleanup resources
    logger.info("Shutting down the application...")
    try:
        if cosmos_client and hasattr(cosmos_client, 'close'):
            await cosmos_client.close()
    except Exception as e:
        logger.error(f"Shutdown error: {e}")

app = FastAPI(title="Connected Car Platform", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/")
def get_status():
    # Check if cosmos client has valid configuration
    cosmos_enabled = bool(cosmos_client and hasattr(cosmos_client, 'endpoint') and cosmos_client.endpoint and (cosmos_client.key or cosmos_client.use_aad_auth))
    cosmos_connected = getattr(cosmos_client, 'connected', False) if cosmos_enabled else False
    
    return {
        "status": "Connected Car Platform running",
        "version": "2.0.0",
        "azure_cosmos_enabled": cosmos_enabled,
        "azure_cosmos_connected": cosmos_connected,
    }

@app.get("/api/health")
def health_check():
    """Health check endpoint for frontend API availability detection"""
    cosmos_enabled = bool(cosmos_client and hasattr(cosmos_client, 'endpoint') and cosmos_client.endpoint and (cosmos_client.key or cosmos_client.use_aad_auth))
    cosmos_connected = getattr(cosmos_client, 'connected', False) if cosmos_enabled else False
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "services": {
            "api": "running",
            "cosmos_db": "connected" if cosmos_connected else "disconnected"
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
    cosmos_connected = await cosmos_client.ensure_connected()
    
    async def status_stream_generator():
        if not cosmos_connected:
            error_status = {"error": "Database service unavailable", "vehicleId": vehicleId}
            yield f"data: {json.dumps(error_status)}\n\n"
            return
        
        try:
            async for status in cosmos_client.subscribe_to_vehicle_status(vehicleId):
                yield f"data: {json.dumps(status)}\n\n"
        except Exception as e:
            logger.error(f"Error in Cosmos DB status streaming: {str(e)}")
            error_status = {"error": "Status streaming unavailable", "vehicleId": vehicleId}
            yield f"data: {json.dumps(error_status)}\n\n"

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


# Top-level entry points for multiprocessing
def run_weather_process():
    """Entry for MCP weather server."""
    try:
        from vehicle.plugin.mcp_weather_server import start_weather_server
        asyncio.run(start_weather_server(host="0.0.0.0", port=8001))
    except Exception as e:
        logger.error(f"Weather server failed to start: {e}")

def run_traffic_process():
    """Entry for MCP traffic server."""
    try:
        from plugin.mcp_traffic_server import start_traffic_server
        asyncio.run(start_traffic_server(host="0.0.0.0", port=8002))
    except Exception as e:
        logger.error(f"Traffic server failed to start: {e}")

def run_poi_process():
    """Entry for MCP POI server."""
    try:
        from plugin.mcp_poi_server import start_poi_server
        asyncio.run(start_poi_server(host="0.0.0.0", port=8003))
    except Exception as e:
        logger.error(f"POI server failed to start: {e}")

def run_navigation_process():
    """Entry for MCP navigation server."""
    try:
        from plugin.mcp_navigation_server import start_navigation_server
        asyncio.run(start_navigation_server(host="0.0.0.0", port=8004))
    except Exception as e:
        logger.error(f"Navigation server failed to start: {e}")

if __name__ == "__main__":
    # Initialize
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    logger.info(f"Starting server at http://{host}:{port}")

    # Launch MCP servers in separate processes
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
                logger.info(f"{name.title()} MCP server PID: {p.pid}")
            except Exception as e:
                logger.error(f"Failed to start {name} MCP server: {e}")
    except Exception as e:
        logger.error(f"Failed to start MCP servers: {e}")

    # Finally, start the FastAPI app
    logger.info(f"Starting API server at http://{host}:{port}")
    try:
        uvicorn.run("main:app", host=host, port=port, reload=False)
    except Exception as e:
        logger.critical(f"API server failed to start: {e}")
        raise
