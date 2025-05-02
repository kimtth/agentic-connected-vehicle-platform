"""
Main application for the connected vehicle platform.
"""
import uuid
import datetime
import logging

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from models.command import Command
from models.notification import Notification
from models.vehicle import VehicleProfile
from models.service import Service
from simulator.car_simulator import CarSimulator
from dotenv import load_dotenv
from azure.cosmos_db import cosmos_client
from azure.azure_vehicle_agent import azure_vehicle_agent
from agents.agent_routes import router as agent_router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables - prioritize .env.azure
load_dotenv()
load_dotenv(".env.azure", override=True)
logger.info("Loaded environment configuration")

# Initialize the car simulator
car_simulator = CarSimulator()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize resources
    logger.info("Starting up the application...")
    
    # Yield control to the application
    yield
    
    # Shutdown: cleanup resources
    logger.info("Shutting down the application...")

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
    return {
        "status": "Connected Car Platform running", 
        "version": "2.0.0"
    }

# Submit a command (simulate external system)
@app.post("/command")
async def submit_command(command: Command, background_tasks: BackgroundTasks):
    """Submit a command to a vehicle"""
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
    return await cosmos_client.list_commands()

# Get vehicle status (from simulator)
@app.get("/vehicle/{vehicle_id}/status")
def get_vehicle_status(vehicle_id: str):
    """Get the status of a vehicle"""
    return car_simulator.get_status(vehicle_id)

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
    return await cosmos_client.list_notifications()

# Add a vehicle profile
@app.post("/vehicle")
async def add_vehicle(profile: VehicleProfile):
    """Add a new vehicle profile"""
    vehicle_id = profile.VehicleId
    await cosmos_client.create_vehicle(profile.dict())
    return {"vehicleId": vehicle_id}

# List all vehicles
@app.get("/vehicles")
async def list_vehicles():
    """List all vehicles"""
    return await cosmos_client.list_vehicles()

# Add a service to a vehicle
@app.post("/vehicle/{vehicle_id}/service")
async def add_service(vehicle_id: str, service: Service):
    """Add a service record to a vehicle"""
    service_data = service.dict()
    service_data["vehicleId"] = vehicle_id
    service_data["id"] = str(uuid.uuid4())  # Generate unique ID for the service
    
    return await cosmos_client.create_service(service_data)

# List all services for a vehicle
@app.get("/vehicle/{vehicle_id}/services")
async def list_services(vehicle_id: str):
    """List all services for a vehicle"""
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