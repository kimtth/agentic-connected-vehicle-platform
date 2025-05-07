"""
Main application for the connected vehicle platform.
"""
import os
import uuid
import datetime
import json
import logging
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from models.command import Command
from models.notification import Notification
from models.vehicle import VehicleProfile
from models.service import Service
from simulator.car_simulator import CarSimulator
from dotenv import load_dotenv

# Configure loguru first, before importing any Azure modules
from utils.logging_config import logger, configure_logging

# Configure loguru with environment variable or default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO")
configure_logging(log_level)

# Explicitly set Azure logging to lower verbosity
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.ERROR)

# Now import Azure modules after configuring logging
from azure.cosmos_db import cosmos_client

# Initialize the car simulator
car_simulator = CarSimulator()

# Import azure_vehicle_agent after environment setup
# Wrapped in try/except to handle initialization errors
try:
    from azure.azure_vehicle_agent import azure_vehicle_agent
    logger.info("Azure Vehicle Agent imported successfully")
except Exception as e:
    logger.error(f"Error importing Azure Vehicle Agent: {str(e)}")
    # Create a stub agent for fallback
    class StubAgent:
        async def ask(self, query, context_vars=None):
            return {
                "response": "The AI agent is currently unavailable due to configuration issues.",
                "plugins_used": []
            }
    azure_vehicle_agent = StubAgent()

# Import agent routes
try:
    from agents.agent_routes import router as agent_router
    logger.info("Agent routes imported successfully")
except Exception as e:
    logger.error(f"Error importing agent routes: {str(e)}")
    # Create an empty router for fallback
    from fastapi import APIRouter
    agent_router = APIRouter()

@asynccontextmanager
async def lifespan(app: FastAPI):
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
    """Get the status of the application"""
    agent_available = hasattr(azure_vehicle_agent, "is_available") and azure_vehicle_agent.is_available
    
    return {
        "status": "Connected Car Platform running", 
        "version": "2.0.0",
        "azure_cosmos_enabled": bool(cosmos_client.endpoint and cosmos_client.key),
        "azure_agent_enabled": agent_available
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
    command_data = command.dict()
    await cosmos_client.create_command(command_data)
    
    # Start background processing
    background_tasks.add_task(process_command_async, command_data)
    
    return {"commandId": command_id}

# Get command log
@app.get("/commands")
async def get_commands():
    """Get all commands"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()
    return await cosmos_client.list_commands()

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
        logger.warning(f"Failed to get status from Cosmos DB, falling back to simulator: {str(e)}")
    
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
            yield f"data: {json.dumps(status)}\n\n"
    
    return StreamingResponse(
        status_stream_generator(),
        media_type="text/event-stream"
    )

# Add a new endpoint to get all simulated vehicles
@app.get("/simulator/vehicles")
def get_simulated_vehicles():
    """Get all vehicle IDs currently in the simulator"""
    vehicle_ids = car_simulator.get_all_vehicle_ids()
    return {"vehicle_ids": vehicle_ids}

# Get notifications
@app.get("/notifications")
async def get_notifications():
    """Get all notifications"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()
    return await cosmos_client.list_notifications()

# Add a vehicle profile
@app.post("/vehicle")
async def add_vehicle(profile: VehicleProfile):
    """Add a new vehicle profile"""
    # Ensure Cosmos DB is connected
    await cosmos_client.ensure_connected()
    vehicle_id = profile.VehicleId
    # Also add to simulator for immediate testing
    car_simulator.add_vehicle(vehicle_id)
    return await cosmos_client.create_vehicle(profile.dict())

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

# Azure Agent API
@app.post("/api/agent/ask")
async def ask_agent(request: dict):
    """Ask the Azure Vehicle Agent a question"""
    if "query" not in request:
        raise HTTPException(status_code=400, detail="Missing 'query' field")
    
    query = request["query"]
    context_vars = request.get("context", {})
    
    # Call the Azure Vehicle Agent
    response = await azure_vehicle_agent.ask(query, context_vars)
    
    return response

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
            updated_data={"status": "processing"}
        )
        
        # Send command to car simulator
        ack = await car_simulator.receive_command(command)
        
        # Update command status to "completed"
        await cosmos_client.update_command(
            command_id=command_id,
            vehicle_id=vehicle_id,
            updated_data={
                "status": "completed",
                "completion_time": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        )
        
        # Create notification
        notification = {
            "id": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": "command_executed",
            "message": f"Command {command['commandType']} executed successfully",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "read": False
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
                    "completion_time": datetime.datetime.now(datetime.timezone.utc).isoformat()
                }
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
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "read": False,
                    "error": str(e)
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
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "read": False,
                    "error": str(e)
                }
                await cosmos_client.create_notification(notification)

# Entry point for running the application
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", 8000))
    logger.info(f"Starting server at http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)