# Car Simulator (PCU) - Enhanced simulator with Azure integration and validation
import asyncio
import random
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from utils.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class VehicleStatus:
    """Data class for vehicle status with validation"""
    Battery: int = 85
    Temperature: int = 22
    Speed: int = 0
    OilUsage: int = 0
    OilRemaining: int = 80
    engineStatus: str = "off"
    doorStatus: Dict[str, bool] = None
    climateSettings: Dict[str, Any] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.doorStatus is None:
            self.doorStatus = {
                "frontLeft": False,
                "frontRight": False,
                "rearLeft": False,
                "rearRight": False
            }
        if self.climateSettings is None:
            self.climateSettings = {
                "temperature": 22,
                "fanSpeed": 0,
                "mode": "off"
            }
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def validate(self) -> bool:
        """Validate status values are within reasonable ranges"""
        try:
            # Validate ranges
            if not (0 <= self.Battery <= 100):
                return False
            if not (-40 <= self.Temperature <= 80):
                return False
            if not (0 <= self.Speed <= 300):
                return False
            if not (0 <= self.OilUsage <= 100):
                return False
            if not (0 <= self.OilRemaining <= 100):
                return False
            if self.engineStatus not in ["on", "off", "starting", "stopping"]:
                return False
            return True
        except (TypeError, ValueError):
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        result = asdict(self)
        if isinstance(result['timestamp'], datetime):
            result['timestamp'] = result['timestamp'].isoformat()
        return result

class CarSimulator:
    """Enhanced car simulator with Azure integration and validation"""
    
    def __init__(self):
        # Dictionary to store vehicle states by vehicle_id
        self.vehicle_states: Dict[str, VehicleStatus] = {}
        self.received_commands: List[Dict] = []
        self.acknowledgements: List[Dict] = []
        
        # Command processing configuration
        self.command_processing_delay = 1.0  # seconds
        self.max_vehicles = 1000  # reasonable limit
        
        # Status simulation configuration
        self.simulation_enabled = True
        self.simulation_interval = 5.0  # seconds
        
        # Performance metrics
        self.metrics = {
            "commands_processed": 0,
            "commands_failed": 0,
            "vehicles_created": 0,
            "status_updates": 0
        }
        
        logger.info("Enhanced Car Simulator initialized - no mock data generation")
    
    def _get_default_status(self) -> VehicleStatus:
        """Return empty status - no mock data, must be provided externally"""
        # Return completely empty status that must be populated by real data
        return VehicleStatus(
            Battery=0,           # No default - must be set by real data
            Temperature=0,       # No default - must be set by real data  
            Speed=0,             # Only reasonable default is 0 speed
            OilUsage=0,          # No default - must be set by real data
            OilRemaining=0,      # No default - must be set by real data
            engineStatus="unknown"  # Unknown state until real data provided
        )
    
    def _validate_vehicle_id(self, vehicle_id: str) -> bool:
        """Validate vehicle ID format"""
        if not isinstance(vehicle_id, str):
            return False
        if not vehicle_id or len(vehicle_id) > 50:
            return False
        # Basic format validation (alphanumeric, hyphens, underscores)
        return vehicle_id.replace("-", "").replace("_", "").isalnum()
    
    def _validate_command(self, command: Dict) -> tuple[bool, str]:
        """Validate command structure and content"""
        try:
            # Required fields
            required_fields = ["commandId", "vehicleId", "commandType"]
            for field in required_fields:
                if field not in command:
                    return False, f"Missing required field: {field}"
            
            # Validate field types
            if not isinstance(command["commandId"], str):
                return False, "commandId must be a string"
            if not isinstance(command["vehicleId"], str):
                return False, "vehicleId must be a string"
            if not isinstance(command["commandType"], str):
                return False, "commandType must be a string"
            
            # Validate vehicle ID
            if not self._validate_vehicle_id(command["vehicleId"]):
                return False, "Invalid vehicleId format"
            
            # Validate command type
            valid_commands = [
                "START_ENGINE", "STOP_ENGINE", "LOCK_DOORS", "UNLOCK_DOORS",
                "ACTIVATE_CLIMATE", "DEACTIVATE_CLIMATE", "SET_TEMPERATURE",
                "HONK_HORN", "FLASH_LIGHTS", "UPDATE_STATUS"
            ]
            if command["commandType"].upper() not in valid_commands:
                return False, f"Invalid command type: {command['commandType']}"
            
            return True, ""
        except Exception as e:
            return False, f"Command validation error: {str(e)}"
    
    async def receive_command(self, command: Dict) -> Dict[str, Any]:
        """Enhanced command processing with validation and error handling"""
        try:
            # Validate command structure
            is_valid, error_msg = self._validate_command(command)
            if not is_valid:
                self.metrics["commands_failed"] += 1
                logger.error(f"Invalid command: {error_msg}")
                return {
                    "commandId": command.get("commandId", "unknown"),
                    "status": "rejected",
                    "reason": error_msg,
                    "timestamp": datetime.now().isoformat()
                }
            
            vehicle_id = command["vehicleId"]
            command_id = command["commandId"]
            
            self.received_commands.append({
                **command,
                "receivedAt": datetime.now().isoformat()
            })
            
            # Check vehicle limit
            if (vehicle_id not in self.vehicle_states and 
                len(self.vehicle_states) >= self.max_vehicles):
                self.metrics["commands_failed"] += 1
                logger.warning(f"Vehicle limit reached ({self.max_vehicles})")
                return {
                    "commandId": command_id,
                    "vehicleId": vehicle_id,
                    "status": "rejected",
                    "reason": "Vehicle limit reached",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Only create vehicle if it doesn't exist AND we have an UPDATE_STATUS command with real data
            if vehicle_id not in self.vehicle_states:
                if command.get("commandType", "").upper() == "UPDATE_STATUS" and command.get("payload"):
                    # Create vehicle with real status data from the command
                    self.vehicle_states[vehicle_id] = self._get_default_status()
                    self.metrics["vehicles_created"] += 1
                    logger.info(f"Created new simulated vehicle with real data: {vehicle_id}")
                else:
                    # Reject commands for non-existent vehicles unless it's an update with real data
                    self.metrics["commands_failed"] += 1
                    logger.warning(f"Vehicle {vehicle_id} not found and command is not UPDATE_STATUS with payload")
                    return {
                        "commandId": command_id,
                        "vehicleId": vehicle_id,
                        "status": "rejected",
                        "reason": "Vehicle not found - please provide status data first",
                        "timestamp": datetime.now().isoformat()
                    }
            
            # Process the command
            success, result_msg = await self._process_command(vehicle_id, command)
            
            # Simulate realistic processing time
            await asyncio.sleep(self.command_processing_delay)
            
            # Create acknowledgment
            ack = {
                "commandId": command_id,
                "vehicleId": vehicle_id,
                "status": "acknowledged" if success else "failed",
                "message": result_msg,
                "timestamp": datetime.now().isoformat(),
                "processedAt": datetime.now().isoformat()
            }
            
            self.acknowledgements.append(ack)
            
            if success:
                self.metrics["commands_processed"] += 1
                logger.info(f"Successfully processed command {command['commandType']} for vehicle {vehicle_id}")
            else:
                self.metrics["commands_failed"] += 1
                logger.warning(f"Failed to process command {command['commandType']} for vehicle {vehicle_id}: {result_msg}")
            
            return ack
            
        except Exception as e:
            self.metrics["commands_failed"] += 1
            logger.error(f"Error processing command: {str(e)}")
            return {
                "commandId": command.get("commandId", "unknown"),
                "vehicleId": command.get("vehicleId", "unknown"),
                "status": "error",
                "reason": f"Processing error: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }
    
    async def _process_command(self, vehicle_id: str, command: Dict) -> tuple[bool, str]:
        """Enhanced command processing with validation and realistic simulation"""
        try:
            command_type = command.get("commandType", "").upper()
            payload = command.get("payload", {})
            
            # Get current state
            status = self.vehicle_states[vehicle_id]
            
            # Process command based on type
            if command_type == "START_ENGINE":
                if status.engineStatus == "on":
                    return False, "Engine already running"
                status.engineStatus = "starting"
                await asyncio.sleep(0.5)  # Simulate engine start time
                status.engineStatus = "on"
                status.Speed = payload.get("initial_speed", 0)
                status.Temperature += 2
                status.OilUsage += 1
                status.OilRemaining = max(0, status.OilRemaining - 1)
                
            elif command_type == "STOP_ENGINE":
                if status.engineStatus == "off":
                    return False, "Engine already off"
                status.engineStatus = "stopping"
                await asyncio.sleep(0.3)  # Simulate engine stop time
                status.engineStatus = "off"
                status.Speed = 0
                status.Temperature = max(status.Temperature - 2, 18)
                
            elif command_type == "LOCK_DOORS":
                if all(status.doorStatus.values()):
                    return False, "All doors already locked"
                for door in status.doorStatus:
                    status.doorStatus[door] = True
                    
            elif command_type == "UNLOCK_DOORS":
                if not any(status.doorStatus.values()):
                    return False, "All doors already unlocked"
                for door in status.doorStatus:
                    status.doorStatus[door] = False
                    
            elif command_type == "ACTIVATE_CLIMATE":
                if status.climateSettings["mode"] != "off":
                    return False, "Climate control already active"
                target_temp = payload.get("target_temperature", 22)
                fan_speed = payload.get("fan_speed", 3)
                
                if not (16 <= target_temp <= 30):
                    return False, "Invalid target temperature (16-30°C)"
                if not (1 <= fan_speed <= 5):
                    return False, "Invalid fan speed (1-5)"
                
                status.climateSettings.update({
                    "temperature": target_temp,
                    "fanSpeed": fan_speed,
                    "mode": "auto"
                })
                
            elif command_type == "DEACTIVATE_CLIMATE":
                if status.climateSettings["mode"] == "off":
                    return False, "Climate control already off"
                status.climateSettings.update({
                    "temperature": 22,
                    "fanSpeed": 0,
                    "mode": "off"
                })
                
            elif command_type == "SET_TEMPERATURE":
                target_temp = payload.get("temperature", 22)
                if not (16 <= target_temp <= 30):
                    return False, "Invalid temperature (16-30°C)"
                status.climateSettings["temperature"] = target_temp
                
            elif command_type == "UPDATE_STATUS":
                # Allow external status updates
                for key, value in payload.items():
                    if hasattr(status, key):
                        setattr(status, key, value)
                        
            else:
                return False, f"Unknown command type: {command_type}"
            
            # Update timestamp
            status.timestamp = datetime.now()
            
            # Validate updated status
            if not status.validate():
                return False, "Status validation failed after command processing"
            
            # Update metrics
            self.metrics["status_updates"] += 1
            
            return True, f"Command {command_type} executed successfully"
            
        except Exception as e:
            logger.error(f"Error processing command {command_type}: {str(e)}")
            return False, f"Processing error: {str(e)}"
    
    def get_status(self, vehicle_id: str = None) -> Dict[str, Any]:
        """Get status with enhanced validation and error handling"""
        try:
            if vehicle_id is None:
                # For backward compatibility, return first vehicle or empty dict
                if not self.vehicle_states:
                    logger.warning("No vehicles in simulator and no vehicle_id provided")
                    return {}
                return next(iter(self.vehicle_states.values())).to_dict()
            
            # Validate vehicle ID
            if not self._validate_vehicle_id(vehicle_id):
                logger.error(f"Invalid vehicle ID format: {vehicle_id}")
                return {}
            
            # Return specific vehicle status only if it exists
            if vehicle_id not in self.vehicle_states:
                logger.warning(f"Vehicle {vehicle_id} not found in simulator - no mock data will be created")
                return {}
            
            return self.vehicle_states[vehicle_id].to_dict()
            
        except Exception as e:
            logger.error(f"Error getting status for vehicle {vehicle_id}: {str(e)}")
            return {}
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get simulator performance metrics"""
        return {
            **self.metrics,
            "active_vehicles": len(self.vehicle_states),
            "commands_in_queue": len(self.received_commands),
            "acknowledgements_sent": len(self.acknowledgements),
            "success_rate": (
                self.metrics["commands_processed"] / 
                (self.metrics["commands_processed"] + self.metrics["commands_failed"])
                if (self.metrics["commands_processed"] + self.metrics["commands_failed"]) > 0 
                else 0
            )
        }

# Create enhanced singleton instance
car_simulator = CarSimulator()
