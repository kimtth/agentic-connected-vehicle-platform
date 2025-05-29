"""
Main application for the connected vehicle platform.
"""

import os
import uuid
import datetime
import json
import asyncio
import uvicorn
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

# Configure loguru first, before importing any Azure modules
from utils.logging_config import logger, configure_logging
from agents.base.a2a_server_init import start_a2a_server

# Configure loguru with environment variable or default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO")
configure_logging(log_level)

# Now import Azure modules after configuring logging
from azure.cosmos_db import cosmos_client

# Initialize the car simulator
car_simulator = CarSimulator()

# Import agent routes
try:
    from apis.agent_routes import router as agent_router

    logger.info("Agent routes imported successfully")
except Exception as e:
    logger.error(f"Error importing agent routes: {str(e)}")
    # Create an empty router for fallback
    from fastapi import APIRouter

    agent_router = APIRouter()


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

# Include the agent router
app.include_router(agent_router, prefix="/api", tags=["Agents"])


@app.get("/api/")
def get_status():
    return {
        "status": "Connected Car Platform running",
        "version": "2.0.0",
        "azure_cosmos_enabled": bool(cosmos_client.endpoint and cosmos_client.key),
    }


# Submit a command (simulate external system)
@app.post("/api/command")
async def submit_command(command: Command, background_tasks: BackgroundTasks):
    """Submit a command to a vehicle"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()

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
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()
    commands = await cosmos_client.list_commands()

    # Filter by vehicleId if provided
    if vehicleId:
        commands = [cmd for cmd in commands if cmd.get("vehicleId") == vehicleId]

    return commands


# Get vehicle status (from simulator or Cosmos DB)
@app.get("/api/vehicle/{vehicleId}/status")
async def get_vehicle_status(vehicleId: str):
    """Get the status of a vehicle"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()

    # Try to fetch from Cosmos DB first, fall back to simulator
    try:
        cosmos_status = await cosmos_client.get_vehicle_status(vehicleId)
        if cosmos_status:
            return cosmos_status
    except Exception as e:
        logger.warning(
            f"Failed to get status from Cosmos DB, falling back to simulator: {str(e)}"
        )

    # Fallback to simulator
    return car_simulator.get_status(vehicleId)


# Stream vehicle status updates
@app.get("/api/vehicle/{vehicleId}/status/stream")
async def stream_vehicle_status(vehicleId: str):
    """Stream real-time status updates for a vehicle"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()

    async def status_stream_generator():
        async for status in cosmos_client.subscribe_to_vehicle_status(vehicleId):
            yield f"data: {json.dumps(status)}\n\n"

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
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()
    notifications = await cosmos_client.list_notifications()

    # Filter by vehicleId if provided
    if vehicleId:
        notifications = [
            notif for notif in notifications if notif.get("vehicleId") == vehicleId
        ]

    return notifications


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
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()
    return await cosmos_client.list_vehicles()


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
    await cosmos_client.ensure_connected()

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

        # Store in Cosmos DB first
        result = await cosmos_client.update_vehicle_status(vehicleId, status_data)
        cosmos_update_success = True
        logger.info(f"Successfully updated vehicle {vehicleId} status in Cosmos DB")

        # Update simulator state as well for consistency
        car_simulator.update_status(vehicleId, status_data)
        logger.info(f"Successfully updated vehicle {vehicleId} status in simulator")

        return result

    except Exception as e:
        logger.error(f"Error updating vehicle status for {vehicleId}: {str(e)}")
        
        # If Cosmos DB update succeeded but simulator update failed, try to rollback Cosmos DB
        if cosmos_update_success and original_simulator_state:
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
    await cosmos_client.ensure_connected()

    # Validate vehicleId
    if not vehicleId:
        raise HTTPException(status_code=400, detail="Vehicle ID is required")

    try:
        # First get current status
        current_status = await get_vehicle_status(vehicleId)

        # Update with new values
        current_status.update(status_update)
        
        # Add timestamp
        current_status["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Store updated status
        result = await cosmos_client.update_vehicle_status(vehicleId, current_status)
        
        # Update simulator as well
        car_simulator.update_status(vehicleId, current_status)
        
        return result
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
        await cosmos_client.ensure_connected()

        # Extract command details
        command_id = command["commandId"]
        vehicleId = command["vehicleId"]

        # Update command status to "processing"
        await cosmos_client.update_command(
            command_id=command_id,
            vehicleId=vehicleId,
            updated_data={"status": "processing"},
        )

        # Send command to car simulator
        ack = await car_simulator.receive_command(command)

        # Update command status to "completed"
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

        # Create notification
        notification = {
            "id": str(uuid.uuid4()),
            "vehicleId": vehicleId,
            "type": "command_executed",
            "message": f"Command {command['commandType']} executed successfully",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "read": False,
        }

        await cosmos_client.create_notification(notification)

    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")

        # Update command status to "failed"
        if "command_id" in locals() and "vehicleId" in locals():
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

            try:
                # Try to send the command to the simulator and use the acknowledgment
                ack = await car_simulator.receive_command(command)
                status = ack.get("status", "unknown")

                # Create notification with the simulator's response status
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

            except Exception as sim_error:
                # If the simulator call also fails, log it and create a simplified notification
                logger.error(f"Error communicating with simulator: {str(sim_error)}")
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


# Top-level entry points for multiprocessing
def run_weather_process():
    """Entry for MCP weather server."""
    asyncio.run(start_weather_server(host="0.0.0.0", port=8001))


def run_a2a_process():
    """Entry for A2A server."""
    asyncio.run(start_a2a_server(host="0.0.0.0", port=8002))


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

    try:
        logger.info("Starting A2A server process on port 8002")
        a2a_proc = Process(target=run_a2a_process, daemon=True)
        a2a_proc.start()
        logger.info(f"A2A server started with PID {a2a_proc.pid}")
    except Exception as e:
        logger.error(f"Failed to start A2A server: {str(e)}")

    # Always start the API server, even if other servers failed
    try:
        logger.info(f"Starting API server at http://{host}:{port}")
        uvicorn.run("main:app", host=host, port=port, reload=True)
    except Exception as e:
        logger.critical(f"Failed to start API server: {str(e)}")
        raise  # Re-raise to show the error
