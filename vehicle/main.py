"""
Main application for the connected vehicle platform.
"""

from datetime import datetime
import sys
import os
import asyncio
import logging
from pathlib import Path
import uuid

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
from simulator.car_simulator import CarSimulator
from dotenv import load_dotenv
from plugin.mcp_server import start_weather_server
from utils.logging_config import logger, configure_logging

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d - %(message)s'
)

logger = logging.getLogger(__name__)

# Configure loguru with environment variable or default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO")
configure_logging(log_level)

load_dotenv(override=True)

# Now import Azure modules after configuring logging
from azure.cosmos_db import cosmos_client

# Initialize the car simulator
car_simulator = CarSimulator()

# Import agent routes with better error handling
try:
    # Import routes with local imports to avoid circular dependencies
    import importlib
    
    # Import modules individually to better isolate errors
    agent_routes_module = importlib.import_module('apis.agent_routes')
    feature_routes_module = importlib.import_module('apis.vehicle_feature_routes') 
    remote_routes_module = importlib.import_module('apis.remote_access_routes')
    emergency_routes_module = importlib.import_module('apis.emergency_routes')
    
    agent_router = agent_routes_module.router
    feature_router = feature_routes_module.router
    remote_router = remote_routes_module.router
    emergency_router = emergency_routes_module.router

    logger.info("Agent routes imported successfully")
except Exception as e:
    logger.error(f"Error importing agent routes: {str(e)}")
    # Create empty routers for fallback
    from fastapi import APIRouter

    agent_router = APIRouter()
    feature_router = APIRouter()
    remote_router = APIRouter()
    emergency_router = APIRouter()
    
    logger.warning("Using fallback empty routers due to import errors")


@asynccontextmanager
async def lifespan(app):
    # Startup: initialize resources
    logger.info("Starting up the application...")

    # Initialize Cosmos DB connection here, within the async context
    await cosmos_client.connect()

    # Yield control to the application
    yield

    # Shutdown: cleanup resources
    logger.info("Shutting down the application...")
    # Close Cosmos DB connection
    await cosmos_client.close()


app = FastAPI(title="Connected Car Platform", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(agent_router, prefix="/api", tags=["Agents"])
app.include_router(feature_router, tags=["Vehicle Features"])
app.include_router(remote_router, tags=["Remote Access"])
app.include_router(emergency_router, tags=["Emergency & Safety"])


@app.get("/api/")
def get_status():
    # Check if cosmos client has valid configuration
    cosmos_enabled = bool(cosmos_client.endpoint and (cosmos_client.key or cosmos_client.use_aad_auth))
    cosmos_connected = cosmos_client.connected if cosmos_enabled else False
    
    return {
        "status": "Connected Car Platform running",
        "version": "2.0.0",
        "azure_cosmos_enabled": cosmos_enabled,
        "azure_cosmos_connected": cosmos_connected,
    }


@app.get("/api/health")
def health_check():
    """Health check endpoint for frontend API availability detection"""
    cosmos_enabled = bool(cosmos_client.endpoint and (cosmos_client.key or cosmos_client.use_aad_auth))
    cosmos_connected = cosmos_client.connected if cosmos_enabled else False
    
    return {
        "status": "healthy",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "services": {
            "api": "running",
            "cosmos_db": "connected" if cosmos_connected else "disconnected",
            "simulator": "running"
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
    command.timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

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


# Get vehicle status (from simulator or Cosmos DB)
@app.get("/api/vehicles/{vehicle_id}/status")
async def get_vehicle_status(vehicle_id: str):
    """Get the current status of a vehicle"""
    try:
        cosmos_connected = await cosmos_client.ensure_connected()
        if cosmos_connected:
            status = await cosmos_client.get_vehicle_status(vehicle_id)
            if status:
                return status
        
        # Fallback to simulator
        return car_simulator.get_status(vehicle_id)
    except Exception as e:
        logger.error(f"Error getting vehicle status: {str(e)}")
        return car_simulator.get_status(vehicle_id)


# Stream vehicle status updates
@app.get("/api/vehicle/{vehicleId}/status/stream")
async def stream_vehicle_status(vehicleId: str):
    """Stream real-time status updates for a vehicle"""
    # Try to ensure Cosmos DB is connected
    cosmos_connected = await cosmos_client.ensure_connected()
    
    async def status_stream_generator():
        if not cosmos_connected:
            # Fallback to simulator if Cosmos DB is not available
            logger.warning("Cosmos DB not available, using simulator for status streaming")
            try:
                # Get status from simulator periodically
                while True:
                    simulator_status = car_simulator.get_status(vehicleId)
                    if simulator_status:
                        yield f"data: {json.dumps(simulator_status)}\n\n"
                    await asyncio.sleep(2.0)  # Update every 2 seconds from simulator
            except Exception as e:
                logger.error(f"Error in simulator status streaming: {str(e)}")
                error_status = {"error": "Status streaming unavailable", "vehicleId": vehicleId}
                yield f"data: {json.dumps(error_status)}\n\n"
        else:
            # Use Cosmos DB for status streaming
            try:
                async for status in cosmos_client.subscribe_to_vehicle_status(vehicleId):
                    yield f"data: {json.dumps(status)}\n\n"
            except Exception as e:
                logger.error(f"Error in Cosmos DB status streaming: {str(e)}")
                # Fallback to simulator
                logger.info("Falling back to simulator for status streaming")
                try:
                    while True:
                        simulator_status = car_simulator.get_status(vehicleId)
                        if simulator_status:
                            yield f"data: {json.dumps(simulator_status)}\n\n"
                        await asyncio.sleep(2.0)
                except Exception as sim_error:
                    logger.error(f"Error in simulator fallback: {str(sim_error)}")
                    error_status = {"error": "Status streaming unavailable", "vehicleId": vehicleId}
                    yield f"data: {json.dumps(error_status)}\n\n"

    return StreamingResponse(status_stream_generator(), media_type="text/event-stream")


# Add a new endpoint to get all simulated vehicles
@app.get("/api/simulator/vehicles")
def get_simulated_vehicles():
    """Get all vehicle IDs currently in the simulator"""
    vehicle_ids = car_simulator.get_all_vehicle_ids()
    return {"vehicle_ids": vehicle_ids}


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
    await cosmos_client.ensure_connected()
    vehicle_id = profile.vehicleId  # Changed from VehicleId to vehicleId
    # Also add to simulator for immediate testing
    car_simulator.add_vehicle(vehicle_id)
    return await cosmos_client.create_vehicle(profile.model_dump())


# List all vehicles
@app.get("/api/vehicles")
async def list_vehicles():
    """List all vehicles"""
    # Try to ensure Cosmos DB is connected
    cosmos_connected = await cosmos_client.ensure_connected()
    if not cosmos_connected:
        logger.warning("Cosmos DB not available, returning simulated vehicle list")
        # Return simulated vehicles as fallback
        simulated_vehicles = [{"vehicleId": vid, "source": "simulator"} for vid in car_simulator.get_all_vehicle_ids()]
        return simulated_vehicles
    
    try:
        vehicles = await cosmos_client.list_vehicles()
        return vehicles
    except Exception as e:
        logger.error(f"Error retrieving vehicles from Cosmos DB: {str(e)}")
        # Fallback to simulator
        simulated_vehicles = [{"vehicleId": vid, "source": "simulator"} for vid in car_simulator.get_all_vehicle_ids()]
        return simulated_vehicles


# Add a service to a vehicle
@app.post("/api/vehicle/{vehicleId}/service")
async def add_service(vehicleId: str, service: Service):
    """Add a service record to a vehicle"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()
    service_data = service.model_dump()
    service_data["vehicleId"] = vehicleId
    service_data["id"] = str(uuid.uuid4())  # Generate unique ID for the service

    return await cosmos_client.create_service(service_data)


# List all services for a vehicle
@app.get("/api/vehicle/{vehicleId}/services")
async def list_services(vehicleId: str):
    """List all services for a vehicle"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()
    return await cosmos_client.list_services(vehicleId)


# Update vehicle status
@app.put("/api/vehicle/{vehicleId}/status")
async def update_vehicle_status(vehicleId: str, status: VehicleStatus):
    """Update the status of a vehicle"""
    # Ensure Cosmos DB is connected
    cosmos_connected = await cosmos_client.ensure_connected()

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
    status_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Store original simulator state for potential rollback
    original_simulator_state = None
    cosmos_update_success = False

    try:
        # Get current simulator state for rollback purposes
        try:
            original_simulator_state = car_simulator.get_status(vehicleId)
        except Exception as sim_error:
            logger.warning(f"Could not get original simulator state: {str(sim_error)}")

        # Store in Cosmos DB first if connected
        if cosmos_connected:
            try:
                result = await cosmos_client.update_vehicle_status(vehicleId, status_data)
                cosmos_update_success = True
                logger.info(f"Successfully updated vehicle {vehicleId} status in Cosmos DB")
            except Exception as cosmos_error:
                logger.error(f"Failed to update Cosmos DB: {str(cosmos_error)}")
                # Continue with simulator update even if Cosmos DB fails
        else:
            logger.warning("Cosmos DB not connected, updating simulator only")
            result = status_data

        # Update simulator state - use set_status instead of update_status
        try:
            # Check if the method exists before calling it
            if hasattr(car_simulator, 'set_status'):
                car_simulator.set_status(vehicleId, status_data)
            elif hasattr(car_simulator, 'update_vehicle_status'):
                car_simulator.update_vehicle_status(vehicleId, status_data)
            else:
                # Fallback: add vehicle if it doesn't exist, then try to update
                car_simulator.add_vehicle(vehicleId)
                logger.info(f"Added vehicle {vehicleId} to simulator")
            
            logger.info(f"Successfully updated vehicle {vehicleId} status in simulator")
        except Exception as sim_error:
            logger.error(f"Failed to update simulator: {str(sim_error)}")
            # If simulator update fails but Cosmos DB succeeded, continue
            if not cosmos_update_success:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Failed to update status in both Cosmos DB and simulator: {str(sim_error)}"
                )

        return result if cosmos_update_success else {"status": "updated", "vehicleId": vehicleId, "data": status_data}

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error updating vehicle status for {vehicleId}: {str(e)}")
        
        # If Cosmos DB update succeeded but simulator update failed, try to rollback Cosmos DB
        if cosmos_update_success and original_simulator_state and cosmos_connected:
            try:
                await cosmos_client.update_vehicle_status(vehicleId, original_simulator_state)
                logger.info(f"Rolled back Cosmos DB status for vehicle {vehicleId}")
            except Exception as rollback_error:
                logger.error(f"Failed to rollback Cosmos DB status: {str(rollback_error)}")

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
        current_status["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Store updated status in Cosmos DB if connected
        if cosmos_connected:
            try:
                result = await cosmos_client.update_vehicle_status(vehicleId, current_status)
            except Exception as cosmos_error:
                logger.error(f"Failed to update Cosmos DB: {str(cosmos_error)}")
                result = current_status
        else:
            result = current_status
        
        # Update simulator as well - use appropriate method
        try:
            if hasattr(car_simulator, 'set_status'):
                car_simulator.set_status(vehicleId, current_status)
            elif hasattr(car_simulator, 'update_vehicle_status'):
                car_simulator.update_vehicle_status(vehicleId, current_status)
            else:
                # Fallback: ensure vehicle exists in simulator
                car_simulator.add_vehicle(vehicleId)
                logger.info(f"Added vehicle {vehicleId} to simulator for status update")
        except Exception as sim_error:
            logger.warning(f"Failed to update simulator: {str(sim_error)}")
        
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
        cosmos_connected = await cosmos_client.ensure_connected()

        # Extract command details
        command_id = command["commandId"]
        vehicleId = command["vehicleId"]

        # Update command status to "processing" if Cosmos DB is available
        if cosmos_connected:
            try:
                await cosmos_client.update_command(
                    command_id=command_id,
                    vehicleId=vehicleId,
                    updated_data={"status": "processing"},
                )
            except Exception as cosmos_error:
                logger.warning(f"Failed to update command status in Cosmos DB: {str(cosmos_error)}")

        # Send command to car simulator
        ack = await car_simulator.receive_command(command)

        # Update command status to "completed" if Cosmos DB is available
        if cosmos_connected:
            try:
                await cosmos_client.update_command(
                    command_id=command_id,
                    vehicleId=vehicleId,
                    updated_data={
                        "status": "completed",
                        "completion_time": datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat(),
                    },
                )
            except Exception as cosmos_error:
                logger.warning(f"Failed to update command completion in Cosmos DB: {str(cosmos_error)}")

        # Create notification if Cosmos DB is available
        if cosmos_connected:
            try:
                notification = {
                    "id": str(uuid.uuid4()),
                    "vehicleId": vehicleId,
                    "type": "command_executed",
                    "message": f"Command {command['commandType']} executed successfully",
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "read": False,
                }
                await cosmos_client.create_notification(notification)
            except Exception as cosmos_error:
                logger.warning(f"Failed to create notification in Cosmos DB: {str(cosmos_error)}")

    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")

        # Update command status to "failed" if possible
        if "command_id" in locals() and "vehicleId" in locals() and cosmos_connected:
            try:
                await cosmos_client.update_command(
                    command_id=command_id,
                    vehicleId=vehicleId,
                    updated_data={
                        "status": "failed",
                        "error": str(e),
                        "completion_time": datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat(),
                    },
                )
            except Exception as cosmos_error:
                logger.warning(f"Failed to update command failure status: {str(cosmos_error)}")

        try:
            # Try to send the command to the simulator and use the acknowledgment
            ack = await car_simulator.receive_command(command)
            status = ack.get("status", "unknown")

            # Create notification with the simulator's response status if Cosmos DB is available
            if cosmos_connected and "vehicleId" in locals():
                try:
                    notification = {
                        "id": str(uuid.uuid4()),
                        "vehicleId": vehicleId,
                        "type": "command_executed",
                        "message": f"Command {command['commandType']} executed with status: {status}",
                        "timestamp": datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat(),
                        "read": False,
                        "error": str(e),
                    }
                    await cosmos_client.create_notification(notification)
                except Exception as cosmos_error:
                    logger.warning(f"Failed to create error notification: {str(cosmos_error)}")

        except Exception as sim_error:
            # If the simulator call also fails, log it and create a simplified notification
            logger.error(f"Error communicating with simulator: {str(sim_error)}")
            if cosmos_connected and "vehicleId" in locals():
                try:
                    notification = {
                        "id": str(uuid.uuid4()),
                        "vehicleId": vehicleId,
                        "type": "command_failed",
                        "message": f"Failed to process command {command['commandType']}",
                        "timestamp": datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat(),
                        "read": False,
                        "error": str(e),
                    }
                    await cosmos_client.create_notification(notification)
                except Exception as cosmos_error:
                    logger.warning(f"Failed to create failure notification: {str(cosmos_error)}")

# Top-level entry points for multiprocessing
def run_weather_process():
    """Entry for MCP weather server."""
    asyncio.run(start_weather_server(host="0.0.0.0", port=8001))


# Entry point for running the application
if __name__ == "__main__":
    # Initialize
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    logger.info(f"Starting server at http://{host}:{port}")

    from multiprocessing import Process, set_start_method

    # on Windows ensure 'spawn' start method
    set_start_method("spawn", force=True)

    # Try to start auxiliary servers, but continue with API even if they fail
    try:
        logger.info("Starting MCP (weather) server process on port 8001")
        mcp_proc = Process(target=run_weather_process, daemon=True)
        mcp_proc.start()
        logger.info(f"MCP server started with PID {mcp_proc.pid}")
    except Exception as e:
        logger.error(f"Failed to start MCP server: {str(e)}")

    # Always start the API server, even if other servers failed
    try:
        logger.info(f"Starting API server at http://{host}:{port}")
        uvicorn.run("main:app", host=host, port=port, reload=True)
    except Exception as e:
        logger.critical(f"Failed to start API server: {str(e)}")
        raise  # Re-raise to show the error
