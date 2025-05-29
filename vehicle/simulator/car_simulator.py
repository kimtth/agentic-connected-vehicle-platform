# Car Simulator (PCU) - Simulates receiving and acknowledging commands for multiple vehicles
import asyncio
import random
from typing import Dict, List, Any
from utils.logging_config import get_logger
logger = get_logger(__name__)

class CarSimulator:
    def __init__(self):
        # Dictionary to store vehicle states by vehicle_id
        self.vehicle_states: Dict[str, Dict[str, Any]] = {}
        self.received_commands: List[Dict] = []
        self.acknowledgements: List[Dict] = []
    
    def _get_default_status(self):
        """Return a default status for a new vehicle"""
        return {
            "Battery": random.randint(70, 100),
            "Temperature": random.randint(20, 30),
            "Speed": 0,
            "OilUsage": random.randint(0, 20),
            "OilRemaining": random.randint(70, 100)
        }
    
    async def receive_command(self, command):
        vehicle_id = command.get("vehicleId")
        if not vehicle_id:
            logger.error(f"Command missing vehicleId: {command}")
            return {"commandId": command.get("commandId"), "status": "rejected", "reason": "Missing vehicleId"}
            
        self.received_commands.append(command)
        
        # Ensure vehicle exists in our simulator
        if vehicle_id not in self.vehicle_states:
            self.vehicle_states[vehicle_id] = self._get_default_status()
            logger.info(f"Created new simulated vehicle with ID: {vehicle_id}")
        
        # Process the command and update vehicle state
        await self._process_command(vehicle_id, command)
        
        # Simulate processing time
        await asyncio.sleep(1)
        
        ack = {"commandId": command["commandId"], "vehicleId": vehicle_id, "status": "acknowledged"}
        self.acknowledgements.append(ack)
        return ack
    
    async def _process_command(self, vehicle_id: str, command: Dict):
        """Process a command and update vehicle state"""
        command_type = command.get("commandType", "").upper()
        payload = command.get("payload", {})
        
        # Get current state
        state = self.vehicle_states[vehicle_id]
        
        # Update state based on command
        if command_type == "START_ENGINE":
            state["Speed"] = payload.get("initial_speed", 5)
            state["Temperature"] += 2
            state["OilUsage"] += 1
            state["OilRemaining"] -= 1
        elif command_type == "STOP_ENGINE":
            state["Speed"] = 0
            state["Temperature"] -= 1
        elif command_type == "LOCK_DOORS":
            # Just acknowledge, no state change
            pass
        elif command_type == "UNLOCK_DOORS":
            # Just acknowledge, no state change
            pass
        elif command_type == "ACTIVATE_CLIMATE":
            target_temp = payload.get("target_temperature", 22)
            # Move current temperature towards target
            if state["Temperature"] < target_temp:
                state["Temperature"] += 1
            elif state["Temperature"] > target_temp:
                state["Temperature"] -= 1
        
        # Save updated state
        self.vehicle_states[vehicle_id] = state
        
        logger.info(f"Processed command {command_type} for vehicle {vehicle_id}")
    
    def get_status(self, vehicle_id: str = None):
        """Get status of a specific vehicle or default if not specified"""
        if vehicle_id is None:
            # For backward compatibility, return first vehicle or default
            if not self.vehicle_states:
                return self._get_default_status()
            return next(iter(self.vehicle_states.values()))
        
        # Return specific vehicle status or create one if it doesn't exist
        if vehicle_id not in self.vehicle_states:
            self.vehicle_states[vehicle_id] = self._get_default_status()
            logger.info(f"Created new simulated vehicle with ID: {vehicle_id}")
        
        return self.vehicle_states[vehicle_id]
    
    def get_all_vehicle_ids(self):
        """Return list of all vehicle IDs in the simulator"""
        return list(self.vehicle_states.keys())
    
    def get_received_commands(self):
        return self.received_commands
    
    def get_acknowledgements(self):
        return self.acknowledgements
    
    def update_status(self, vehicle_id: str, status_data: Dict):
        """Update the status of a vehicle in the simulator"""
        # Create vehicle state if it doesn't exist
        if vehicle_id not in self.vehicle_states:
            self.vehicle_states[vehicle_id] = self._get_default_status()
            logger.info(f"Created new simulated vehicle with ID: {vehicle_id}")
        
        # Update state with new values
        state = self.vehicle_states[vehicle_id]
        
        # Map the incoming status fields to simulator fields
        if "Battery" in status_data:
            state["Battery"] = status_data["Battery"]
        if "Temperature" in status_data:
            state["Temperature"] = status_data["Temperature"]
        if "Speed" in status_data:
            state["Speed"] = status_data["Speed"]
        if "OilRemaining" in status_data:
            state["OilRemaining"] = status_data["OilRemaining"]
        if "engineStatus" in status_data:
            state["engineStatus"] = status_data["engineStatus"]
        if "doorStatus" in status_data:
            # Just store the whole object
            state["doorStatus"] = status_data["doorStatus"]
        if "climateSettings" in status_data:
            state["climateSettings"] = status_data["climateSettings"]
        
        # Save updated state
        self.vehicle_states[vehicle_id] = state
        
        logger.info(f"Updated simulator status for vehicle {vehicle_id}")
        return state
    
    def add_vehicle(self, vehicle_id: str):
        """Add a new vehicle to the simulator"""
        if vehicle_id not in self.vehicle_states:
            self.vehicle_states[vehicle_id] = self._get_default_status()
            logger.info(f"Added new vehicle to simulator: {vehicle_id}")
        else:
            logger.info(f"Vehicle {vehicle_id} already exists in simulator")
    
car_simulator = CarSimulator()
