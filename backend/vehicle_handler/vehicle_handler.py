"""
Vehicle Handler for the Connected Car Platform.

This module provides a comprehensive interface to all vehicle-related features
and integrates with the agent system to provide both direct API access and
agent-mediated natural language interactions.
"""

from typing import Dict, Any, Optional, List
import uuid
import datetime
import asyncio

# Replace standard logging with loguru
from utils.logging_config import get_logger

# Import existing handlers
from vehicle_handler.vehicle_profile_manager import VehicleProfileManager
from vehicle_handler.vehicle_service_manager import VehicleServiceManager
from vehicle_handler.vehicle_api_executor import VehicleAPIExecutor
from vehicle_handler.vehicle_data_manager import VehicleDataManager
from vehicle_handler.vehicle_notification_handler import VehicleNotificationHandler

# Get logger for this module
logger = get_logger(__name__)

class VehicleHandler:
    """
    Comprehensive handler for all vehicle-related features.
    Integrates with the agent system and provides direct API access.
    """
    
    def __init__(self, simulator=None):
        """
        Initialize the Vehicle Handler with all component handlers.
        
        Args:
            simulator: Optional reference to the CarSimulator for testing
        """
        self.profile_manager = VehicleProfileManager()
        self.service_manager = VehicleServiceManager()
        self.api_executor = VehicleAPIExecutor()
        self.data_manager = VehicleDataManager()
        self.notification_handler = VehicleNotificationHandler()
        self.simulator = simulator
        logger.info("VehicleHandler initialized with all component handlers")
    
    # Remote Access Features
    
    async def lock_vehicle(self, vehicle_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Lock a vehicle remotely.
        
        Args:
            vehicle_id: ID of the vehicle to lock
            parameters: Optional parameters (e.g., specific doors)
            
        Returns:
            Command execution status
        """
        command = {
            "commandId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "commandType": "LOCK_DOORS",
            "parameters": parameters or {"doors": "all"},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "pending"
        }
        
        await self.api_executor.send_command(command)
        
        # Create notification for the action
        notification = {
            "id": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": "command_sent",
            "message": f"Lock command sent to vehicle {vehicle_id}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "read": False
        }
        
        self.notification_handler.send_notification(notification)
        
        return {
            "commandId": command["commandId"],
            "status": "sent",
            "message": f"Lock command sent to vehicle {vehicle_id}"
        }
    
    async def unlock_vehicle(self, vehicle_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Unlock a vehicle remotely.
        
        Args:
            vehicle_id: ID of the vehicle to unlock
            parameters: Optional parameters (e.g., specific doors)
            
        Returns:
            Command execution status
        """
        command = {
            "commandId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "commandType": "UNLOCK_DOORS",
            "parameters": parameters or {"doors": "all"},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "pending"
        }
        
        await self.api_executor.send_command(command)
        
        # Create notification for the action
        notification = {
            "id": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": "command_sent",
            "message": f"Unlock command sent to vehicle {vehicle_id}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "read": False
        }
        
        self.notification_handler.send_notification(notification)
        
        return {
            "commandId": command["commandId"],
            "status": "sent",
            "message": f"Unlock command sent to vehicle {vehicle_id}"
        }
    
    async def start_engine(self, vehicle_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Start a vehicle's engine remotely.
        
        Args:
            vehicle_id: ID of the vehicle to start
            parameters: Optional parameters (e.g., runtime duration)
            
        Returns:
            Command execution status
        """
        command = {
            "commandId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "commandType": "START_ENGINE",
            "parameters": parameters or {"duration": 10},  # Default 10-minute runtime
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "pending"
        }
        
        await self.api_executor.send_command(command)
        
        # Create notification for the action
        notification = {
            "id": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": "command_sent",
            "message": f"Engine start command sent to vehicle {vehicle_id}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "read": False
        }
        
        self.notification_handler.send_notification(notification)
        
        return {
            "commandId": command["commandId"],
            "status": "sent",
            "message": f"Engine start command sent to vehicle {vehicle_id}"
        }
    
    # Safety & Emergency Features
    
    async def trigger_emergency_call(self, vehicle_id: str, emergency_type: str) -> Dict[str, Any]:
        """
        Trigger an emergency call from the vehicle.
        
        Args:
            vehicle_id: ID of the vehicle
            emergency_type: Type of emergency (collision, medical, etc.)
            
        Returns:
            Emergency call status
        """
        command = {
            "commandId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "commandType": "EMERGENCY_CALL",
            "parameters": {"type": emergency_type},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "pending",
            "priority": "high"
        }
        
        await self.api_executor.send_command(command)
        
        # Create critical notification for the action
        notification = {
            "id": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": "emergency",
            "message": f"Emergency call ({emergency_type}) initiated for vehicle {vehicle_id}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "read": False,
            "severity": "critical"
        }
        
        self.notification_handler.send_notification(notification)
        
        return {
            "commandId": command["commandId"],
            "status": "emergency_initiated",
            "message": f"Emergency call ({emergency_type}) initiated for vehicle {vehicle_id}"
        }
    
    async def report_theft(self, vehicle_id: str, location: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Report a vehicle as stolen.
        
        Args:
            vehicle_id: ID of the stolen vehicle
            location: Optional last known location (latitude, longitude)
            
        Returns:
            Theft report status
        """
        command = {
            "commandId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "commandType": "REPORT_THEFT",
            "parameters": {"location": location, "reportTime": datetime.datetime.now(datetime.timezone.utc).isoformat()},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "pending",
            "priority": "high"
        }
        
        await self.api_executor.send_command(command)
        
        # Log the theft report
        self.data_manager.log_vehicle_data(vehicle_id, {
            "logType": "security",
            "event": "theft_report",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "location": location
        })
        
        # Create critical notification
        notification = {
            "id": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": "security",
            "message": f"Theft reported for vehicle {vehicle_id}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "read": False,
            "severity": "critical"
        }
        
        self.notification_handler.send_notification(notification)
        
        return {
            "commandId": command["commandId"],
            "status": "theft_reported",
            "message": f"Theft reported for vehicle {vehicle_id}"
        }
    
    # Charging & Energy Features
    
    async def start_charging(self, vehicle_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Start charging an electric vehicle.
        
        Args:
            vehicle_id: ID of the vehicle to charge
            parameters: Optional parameters (target level, schedule, etc.)
            
        Returns:
            Charging status
        """
        command = {
            "commandId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "commandType": "START_CHARGING",
            "parameters": parameters or {"target_level": 80},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "pending"
        }
        
        await self.api_executor.send_command(command)
        
        # Create notification
        notification = {
            "id": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": "charging",
            "message": f"Charging started for vehicle {vehicle_id}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "read": False
        }
        
        self.notification_handler.send_notification(notification)
        
        return {
            "commandId": command["commandId"],
            "status": "charging_started",
            "message": f"Charging started for vehicle {vehicle_id}"
        }
    
    async def stop_charging(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Stop charging an electric vehicle.
        
        Args:
            vehicle_id: ID of the vehicle
            
        Returns:
            Charging status
        """
        command = {
            "commandId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "commandType": "STOP_CHARGING",
            "parameters": {},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "pending"
        }
        
        await self.api_executor.send_command(command)
        
        # Create notification
        notification = {
            "id": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": "charging",
            "message": f"Charging stopped for vehicle {vehicle_id}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "read": False
        }
        
        self.notification_handler.send_notification(notification)
        
        return {
            "commandId": command["commandId"],
            "status": "charging_stopped",
            "message": f"Charging stopped for vehicle {vehicle_id}"
        }
    
    async def get_charging_stations(self, vehicle_id: str, radius: float, location: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Find charging stations near a location.
        
        Args:
            vehicle_id: ID of the vehicle
            radius: Search radius in kilometers
            location: Optional location (defaults to vehicle's current location)
            
        Returns:
            List of nearby charging stations
        """
        # This would typically call an external API
        # For demonstration purposes, return mock data
        
        # Log the search request
        self.data_manager.log_vehicle_data(vehicle_id, {
            "logType": "information",
            "event": "charging_station_search",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "parameters": {"radius": radius, "location": location}
        })
        
        return {
            "status": "success",
            "message": f"Found 3 charging stations within {radius} km",
            "stations": [
                {
                    "id": "cs001",
                    "name": "Central EV Station",
                    "location": {"latitude": 37.7749, "longitude": -122.4194},
                    "distance": 2.3,
                    "available_ports": 4,
                    "charging_types": ["Level 2", "DC Fast"]
                },
                {
                    "id": "cs002",
                    "name": "City Power Hub",
                    "location": {"latitude": 37.7831, "longitude": -122.4181},
                    "distance": 3.1,
                    "available_ports": 2,
                    "charging_types": ["Level 2"]
                },
                {
                    "id": "cs003",
                    "name": "Express Charge Station",
                    "location": {"latitude": 37.7691, "longitude": -122.4251},
                    "distance": 3.7,
                    "available_ports": 6,
                    "charging_types": ["Level 2", "DC Fast", "Tesla"]
                }
            ]
        }
    
    # Information Services Features
    
    async def get_weather(self, vehicle_id: str, location: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Get weather information for a location.
        
        Args:
            vehicle_id: ID of the vehicle
            location: Optional location (defaults to vehicle's current location)
            
        Returns:
            Weather information
        """
        # This would typically call an external weather API
        # For demonstration purposes, return mock data
        
        # Log the request
        self.data_manager.log_vehicle_data(vehicle_id, {
            "logType": "information",
            "event": "weather_request",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "location": location
        })
        
        return {
            "status": "success",
            "message": "Current weather information",
            "location": location or {"latitude": 37.7749, "longitude": -122.4194, "city": "San Francisco"},
            "weather": {
                "temperature": 18,
                "condition": "Partly Cloudy",
                "humidity": 65,
                "wind_speed": 10,
                "forecast": [
                    {"day": "Today", "high": 19, "low": 12, "condition": "Partly Cloudy"},
                    {"day": "Tomorrow", "high": 21, "low": 13, "condition": "Sunny"}
                ]
            }
        }
    
    async def get_traffic(self, vehicle_id: str, route: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get traffic information for a route.
        
        Args:
            vehicle_id: ID of the vehicle
            route: Optional route information (start/end points)
            
        Returns:
            Traffic information
        """
        # This would typically call an external traffic API
        # For demonstration purposes, return mock data
        
        # Log the request
        self.data_manager.log_vehicle_data(vehicle_id, {
            "logType": "information",
            "event": "traffic_request",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "route": route
        })
        
        return {
            "status": "success",
            "message": "Current traffic information",
            "route": route or {"start": "Home", "end": "Work"},
            "traffic": {
                "current_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "estimated_travel_time": 35,  # minutes
                "distance": 12.5,  # km
                "congestion_level": "moderate",
                "incidents": [
                    {"type": "construction", "location": "Highway 101, mile marker 432", "delay": 10}
                ]
            }
        }
    
    # Vehicle Feature Control
    
    async def set_climate(self, vehicle_id: str, temperature: float, settings: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Set the climate control in a vehicle.
        
        Args:
            vehicle_id: ID of the vehicle
            temperature: Target temperature in Celsius
            settings: Optional additional settings (fan speed, zones, etc.)
            
        Returns:
            Climate control status
        """
        command = {
            "commandId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "commandType": "SET_CLIMATE",
            "parameters": {"temperature": temperature, **(settings or {})},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "pending"
        }
        
        await self.api_executor.send_command(command)
        
        # Create notification
        notification = {
            "id": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": "climate_control",
            "message": f"Climate set to {temperature}°C for vehicle {vehicle_id}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "read": False
        }
        
        self.notification_handler.send_notification(notification)
        
        return {
            "commandId": command["commandId"],
            "status": "climate_set",
            "message": f"Climate set to {temperature}°C for vehicle {vehicle_id}"
        }
    
    async def manage_subscriptions(self, vehicle_id: str, action: str, service_code: str) -> Dict[str, Any]:
        """
        Manage vehicle service subscriptions.
        
        Args:
            vehicle_id: ID of the vehicle
            action: Action to perform (add, remove, update)
            service_code: Code of the service to manage
            
        Returns:
            Subscription management status
        """
        # For demonstration, create a service record based on action
        if action.lower() == "add":
            service = {
                "id": str(uuid.uuid4()),
                "serviceCode": service_code,
                "description": f"Service {service_code}",
                "startDate": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "endDate": None  # Open-ended subscription
            }
            
            self.service_manager.add_service(vehicle_id, service)
            
            return {
                "status": "success",
                "message": f"Service {service_code} added to vehicle {vehicle_id}",
                "service": service
            }
        
        elif action.lower() == "remove":
            # This is simplified - in reality, would need to find and remove specific service
            return {
                "status": "success",
                "message": f"Service {service_code} removed from vehicle {vehicle_id}"
            }
        
        else:
            return {
                "status": "error",
                "message": f"Unknown action: {action}"
            }
    
    # Diagnostics & Battery Features
    
    async def run_diagnostics(self, vehicle_id: str, systems: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run vehicle diagnostics.
        
        Args:
            vehicle_id: ID of the vehicle
            systems: Optional list of systems to diagnose (None = all systems)
            
        Returns:
            Diagnostic results
        """
        command = {
            "commandId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "commandType": "RUN_DIAGNOSTICS",
            "parameters": {"systems": systems or ["all"]},
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "pending"
        }
        
        await self.api_executor.send_command(command)
        
        # Log the diagnostics request
        self.data_manager.log_vehicle_data(vehicle_id, {
            "logType": "diagnostics",
            "event": "diagnostics_request",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "parameters": {"systems": systems or ["all"]}
        })
        
        # This would typically wait for results, but for demonstration:
        # Create mock diagnostic results
        diagnostics_results = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "systems": {
                "engine": {"status": "ok", "codes": []},
                "battery": {"status": "ok", "health": 92, "codes": []},
                "brakes": {"status": "ok", "wear": 15, "codes": []},
                "transmission": {"status": "warning", "codes": ["P0715"]},
                "electrical": {"status": "ok", "codes": []}
            },
            "overall_status": "warning",
            "recommendations": [
                "Transmission sensor may need service. Code P0715: Input/Turbine Speed Sensor Circuit."
            ]
        }
        
        # Create notification
        notification = {
            "id": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": "diagnostics",
            "message": f"Diagnostics completed for vehicle {vehicle_id}. Status: {diagnostics_results['overall_status']}",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "read": False,
            "severity": "warning" if diagnostics_results['overall_status'] == "warning" else "info"
        }
        
        self.notification_handler.send_notification(notification)
        
        return {
            "commandId": command["commandId"],
            "status": "diagnostics_completed",
            "message": f"Diagnostics completed for vehicle {vehicle_id}",
            "results": diagnostics_results
        }
    
    async def get_battery_status(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get battery status for an electric vehicle.
        
        Args:
            vehicle_id: ID of the vehicle
            
        Returns:
            Battery status information
        """
        # For demonstration, return mock data
        return {
            "status": "success",
            "message": f"Battery status for vehicle {vehicle_id}",
            "battery": {
                "level": 65,  # percent
                "range": 185,  # km
                "charging_status": "not_charging",
                "time_to_full": None,
                "health": 92,  # percent
                "temperature": 23  # Celsius
            }
        }
    
    # Alerts & Notifications Features
    
    async def get_alerts(self, vehicle_id: str, alert_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get active alerts for a vehicle.
        
        Args:
            vehicle_id: ID of the vehicle
            alert_type: Optional alert type filter
            
        Returns:
            List of active alerts
        """
        # In a real implementation, would fetch from storage
        # For demonstration, return mock data
        alerts = [
            {
                "id": "a001",
                "type": "speed_violation",
                "message": "Speed limit exceeded (120 km/h in 100 km/h zone)",
                "timestamp": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2)).isoformat(),
                "severity": "warning",
                "location": {"latitude": 37.7749, "longitude": -122.4194},
                "read": False
            },
            {
                "id": "a002",
                "type": "maintenance",
                "message": "Oil change due in 500 km",
                "timestamp": (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)).isoformat(),
                "severity": "info",
                "read": True
            }
        ]
        
        if alert_type:
            alerts = [alert for alert in alerts if alert["type"] == alert_type]
        
        return {
            "status": "success",
            "message": f"Alerts for vehicle {vehicle_id}",
            "alerts": alerts
        }
    
    async def update_notification_preferences(self, vehicle_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update notification preferences for a vehicle.
        
        Args:
            vehicle_id: ID of the vehicle
            preferences: Notification preferences settings
            
        Returns:
            Updated preferences status
        """
        # This would typically update a user profile or settings in database
        # For demonstration, just return confirmation
        
        # Log the update
        self.data_manager.log_vehicle_data(vehicle_id, {
            "logType": "settings",
            "event": "notification_preferences_update",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "preferences": preferences
        })
        
        return {
            "status": "success",
            "message": f"Notification preferences updated for vehicle {vehicle_id}",
            "preferences": preferences
        }
    
    # Integration with the agent system
    
    async def handle_agent_request(self, agent_type: str, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle a request from the agent system.
        
        Args:
            agent_type: Type of agent making the request
            query: User query
            context: Additional context for the query
            
        Returns:
            Response to the agent request
        """
        vehicle_id = context.get("vehicle_id") if context else None
        
        # Handle request based on agent type
        if agent_type == "remote_access":
            # Simple keyword matching for demonstration
            if "lock" in query.lower():
                return await self.lock_vehicle(vehicle_id)
            elif "unlock" in query.lower():
                return await self.unlock_vehicle(vehicle_id)
            elif "start" in query.lower() and "engine" in query.lower():
                return await self.start_engine(vehicle_id)
        
        elif agent_type == "safety_emergency":
            if "emergency" in query.lower() or "ecall" in query.lower():
                emergency_type = "general" 
                if "collision" in query.lower() or "crash" in query.lower():
                    emergency_type = "collision"
                elif "medical" in query.lower():
                    emergency_type = "medical"
                return await self.trigger_emergency_call(vehicle_id, emergency_type)
            elif "theft" in query.lower() or "stolen" in query.lower():
                return await self.report_theft(vehicle_id)
        
        elif agent_type == "charging_energy":
            if "start" in query.lower() and "charg" in query.lower():
                return await self.start_charging(vehicle_id)
            elif "stop" in query.lower() and "charg" in query.lower():
                return await self.stop_charging(vehicle_id)
            elif "station" in query.lower() or "find" in query.lower() and "charg" in query.lower():
                return await self.get_charging_stations(vehicle_id, 5.0)  # Default 5km radius
        
        elif agent_type == "information_services":
            if "weather" in query.lower():
                return await self.get_weather(vehicle_id)
            elif "traffic" in query.lower():
                return await self.get_traffic(vehicle_id)
        
        elif agent_type == "vehicle_feature_control":
            if "climate" in query.lower() or "temperature" in query.lower():
                # Extract temperature from query or use default
                temp = 22.0  # Default temperature
                return await self.set_climate(vehicle_id, temp)
            elif "subscription" in query.lower() or "service" in query.lower():
                action = "add" if "add" in query.lower() or "enable" in query.lower() else "remove"
                # This is simplistic - in a real system we'd extract the actual service code
                service_code = "PREMIUM_CONNECT"
                return await self.manage_subscriptions(vehicle_id, action, service_code)
        
        elif agent_type == "diagnostics_battery":
            if "diagnos" in query.lower() or "check" in query.lower():
                return await self.run_diagnostics(vehicle_id)
            elif "battery" in query.lower():
                return await self.get_battery_status(vehicle_id)
        
        elif agent_type == "alerts_notifications":
            if "alert" in query.lower():
                return await self.get_alerts(vehicle_id)
            elif "prefer" in query.lower() or "notif" in query.lower() and "setting" in query.lower():
                # This is simplistic - in a real system we'd extract actual preferences
                sample_preferences = {"speed_alerts": True, "geofence_alerts": True, "maintenance_reminders": True}
                return await self.update_notification_preferences(vehicle_id, sample_preferences)
        
        # Default response if no specific handling
        return {
            "status": "error",
            "message": f"Could not process request for agent type {agent_type}",
            "query": query
        }
