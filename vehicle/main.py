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
async def lifespan():
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


@app.get("/")
def get_status():
    return {
        "status": "Connected Car Platform running",
        "version": "2.0.0",
        "azure_cosmos_enabled": bool(cosmos_client.endpoint and cosmos_client.key),
    }


# Submit a command (simulate external system)
@app.post("/command")
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
@app.get("/commands")
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
@app.get("/vehicle/{vehicle_id}/status")
async def get_vehicle_status(vehicle_id: str):
    """Get the status of a vehicle"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()

    # Try to fetch from Cosmos DB first, fall back to simulator
    try:
        cosmos_status = await cosmos_client.get_vehicle_status(vehicle_id)
        if cosmos_status:
            return cosmos_status
    except Exception as e:
        logger.warning(
            f"Failed to get status from Cosmos DB, falling back to simulator: {str(e)}"
        )

    # Fallback to simulator
    return car_simulator.get_status(vehicle_id)


# Stream vehicle status updates
@app.get("/vehicle/{vehicle_id}/status/stream")
async def stream_vehicle_status(vehicle_id: str):
    """Stream real-time status updates for a vehicle"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()

    async def status_stream_generator():
        async for status in cosmos_client.subscribe_to_vehicle_status(vehicle_id):
            yield f"data: {json.dumps(status)}{os.linesep * 2}"

    return StreamingResponse(status_stream_generator(), media_type="text/event-stream")


# Add a new endpoint to get all simulated vehicles
@app.get("/simulator/vehicles")
def get_simulated_vehicles():
    """Get all vehicle IDs currently in the simulator"""
    vehicle_ids = car_simulator.get_all_vehicle_ids()
    return {"vehicle_ids": vehicle_ids}


# Get notifications
@app.get("/notifications")
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
@app.post("/vehicle")
async def add_vehicle(profile: VehicleProfile):
    """Add a new vehicle profile"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()
    vehicle_id = profile.VehicleId
    # Also add to simulator for immediate testing
    car_simulator.add_vehicle(vehicle_id)
    return await cosmos_client.create_vehicle(profile.model_dump())


# List all vehicles
@app.get("/vehicles")
async def list_vehicles():
    """List all vehicles"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()
    return await cosmos_client.list_vehicles()


# Add a service to a vehicle
@app.post("/vehicle/{vehicle_id}/service")
async def add_service(vehicle_id: str, service: Service):
    """Add a service record to a vehicle"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()
    service_data = service.model_dump()
    service_data["vehicleId"] = vehicle_id
    service_data["id"] = str(uuid.uuid4())  # Generate unique ID for the service

    return await cosmos_client.create_service(service_data)


# List all services for a vehicle
@app.get("/vehicle/{vehicle_id}/services")
async def list_services(vehicle_id: str):
    """List all services for a vehicle"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()
    return await cosmos_client.list_services(vehicle_id)


# Update vehicle status
@app.put("/vehicle/{vehicle_id}/status")
async def update_vehicle_status(vehicle_id: str, status: VehicleStatus):
    """Update the status of a vehicle"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()

    # Ensure vehicleId in path matches the one in the status object
    if status.vehicleId != vehicle_id:
        raise HTTPException(
            status_code=400, detail="Vehicle ID in path does not match status object"
        )

    # Convert status to dict for storage
    status_data = status.model_dump()

    # Add timestamp
    status_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

    try:
        # Store in Cosmos DB
        result = await cosmos_client.update_vehicle_status(vehicle_id, status_data)

        # Update simulator state as well for consistency
        car_simulator.update_status(vehicle_id, status_data)

        return result
    except Exception as e:
        logger.error(f"Error updating vehicle status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to update status: {str(e)}"
        )


# Partial status update (only specific fields)
@app.patch("/vehicle/{vehicle_id}/status")
async def patch_vehicle_status(vehicle_id: str, status_update: dict):
    """Update specific fields of a vehicle's status"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()

    # Validate vehicle_id
    if not vehicle_id:
        raise HTTPException(status_code=400, detail="Vehicle ID is required")

    try:
        # First get current status
        current_status = await get_vehicle_status(vehicle_id)

        # Update with new values
        for key, value in status_update.items():
            # Skip vehicleId to avoid conflicts
            if key != "vehicleId":
                current_status[key] = value

        # Add timestamp for the update
        current_status["timestamp"] = datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat()
        current_status["vehicleId"] = vehicle_id

        # Store updated status
        result = await cosmos_client.update_vehicle_status(vehicle_id, current_status)

        # Update simulator as well
        car_simulator.update_status(vehicle_id, current_status)

        return result
    except Exception as e:
        logger.error(f"Error updating vehicle status fields: {str(e)}")
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
        vehicle_id = command["vehicleId"]

        # Update command status to "processing"
        await cosmos_client.update_command(
            command_id=command_id,
            vehicle_id=vehicle_id,
            updated_data={"status": "processing"},
        )

        # Send command to car simulator
        ack = await car_simulator.receive_command(command)

        # Update command status to "completed"
        await cosmos_client.update_command(
            command_id=command_id,
            vehicle_id=vehicle_id,
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
            "vehicleId": vehicle_id,
            "type": "command_executed",
            "message": f"Command {command['commandType']} executed successfully",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "read": False,
        }

        await cosmos_client.create_notification(notification)

    except Exception as e:
        logger.error(f"Error processing command: {str(e)}")

        # Update command status to "failed"
        if "command_id" in locals() and "vehicle_id" in locals():
            await cosmos_client.update_command(
                command_id=command_id,
                vehicle_id=vehicle_id,
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
                    "vehicleId": vehicle_id,
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
                    "vehicleId": vehicle_id,
                    "type": "command_failed",
                    "message": f"Failed to process command {command['commandType']}",
                    "timestamp": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "read": False,
                    "error": str(e),
                }
                await cosmos_client.create_notification(notification)


# Entry point for running the application
if __name__ == "__main__":
    # Initialize
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    logger.info(f"Starting server at http://{host}:{port}")

    # Run the bootstrap process
    # 1. Start the weather server (MCP) in the background
    asyncio.run(start_weather_server(host="0.0.0.0", port=8001))
    # 2. Start a2a server
    asyncio.run(start_a2a_server(host="0.0.0.0", port=8002))
    # 3. Start the FastAPI server
    # Use uvicorn to run the FastAPI app
    uvicorn.run("main:app", host=host, port=port, reload=True)
