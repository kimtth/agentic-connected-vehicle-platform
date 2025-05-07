"""
Vehicle Feature Control Agent for the Connected Car Platform.

This agent manages in-car features like climate settings, temperature control,
and service subscriptions.
"""

import logging
import datetime
import uuid
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent
from utils.agent_tools import validate_command, get_latest_status_from_cosmos
from semantic_kernel.functions import kernel_function
from azure.cosmos_db import cosmos_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VehicleFeatureControlAgent(BaseAgent):
    """
    Vehicle Feature Control Agent for managing in-car features.
    """
    
    def __init__(self):
        """Initialize the Vehicle Feature Control Agent."""
        instructions = (
            "You are a Vehicle Feature Control Agent that helps users manage in-car features like "
            "climate settings, temperature control, and service subscriptions. "
            "You can control the climate system, adjust vehicle features, and provide "
            "information about current subscriptions and settings. "
            "Be helpful, accurate, and focus on safely managing vehicle features."
        )
        
        super().__init__("Vehicle Feature Control Agent", instructions)
        
        # Register tools/plugins with the SK agent
        self.sk_agent.add_plugin(self)
    
    @kernel_function(
        description="Adjust climate control settings in the vehicle",
        name="adjust_climate_control"
    )
    async def adjust_climate_control(
        self, 
        vehicle_id: str, 
        temperature: float = 22.0, 
        fan_speed: str = "medium",
        ac_on: bool = None,
        heating_on: bool = None
    ) -> str:
        """Adjust the climate control settings in the vehicle."""
        try:
            # Validate input parameters
            if fan_speed.lower() not in ["low", "medium", "high"]:
                return f"Invalid fan speed: {fan_speed}. Must be one of: low, medium, high."
            
            if temperature < 16 or temperature > 30:
                return f"Temperature {temperature}°C is outside the acceptable range (16-30°C)."
            
            # Get current climate settings to determine which values to update
            current_status = await get_latest_status_from_cosmos(vehicle_id)
            if not current_status:
                logger.warning(f"No status found for vehicle {vehicle_id}")
            
            # Prepare command parameters
            parameters = {
                "temperature": temperature,
                "fan_speed": fan_speed.lower()
            }
            
            # Only include AC and heating settings if explicitly provided
            if ac_on is not None:
                parameters["isAirConditioningOn"] = ac_on
            
            if heating_on is not None:
                parameters["isHeatingOn"] = heating_on
            
            # Create command
            command = {
                "id": str(uuid.uuid4()),
                "commandId": f"climate-{str(uuid.uuid4())[:8]}",
                "vehicleId": vehicle_id,
                "commandType": "SET_CLIMATE",
                "parameters": parameters,
                "status": "pending",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "priority": "Normal"
            }
            
            # Store in Cosmos DB
            await cosmos_client.create_command(command)
            
            # Format response based on what was adjusted
            response_parts = [
                f"Temperature set to {temperature}°C",
                f"Fan speed set to {fan_speed}"
            ]
            
            if ac_on is not None:
                response_parts.append(f"Air conditioning {'turned on' if ac_on else 'turned off'}")
            
            if heating_on is not None:
                response_parts.append(f"Heating {'turned on' if heating_on else 'turned off'}")
            
            # Return success message
            return f"Climate control adjusted: {', '.join(response_parts)}."
        except Exception as e:
            logger.error(f"Failed to adjust climate control: {str(e)}")
            return "Failed to adjust the climate control due to a system error."
    
    @kernel_function(
        description="Get active subscriptions for the vehicle",
        name="get_subscriptions"
    )
    async def get_subscriptions(self, vehicle_id: str) -> str:
        """Get active subscriptions for the vehicle."""
        try:
            # Get subscriptions from Cosmos DB
            services = await cosmos_client.list_services(vehicle_id)
            
            active_services = [
                service for service in services 
                if not service.get("EndDate") or 
                datetime.datetime.fromisoformat(service.get("EndDate")) > datetime.datetime.now()
            ]
            
            if not active_services:
                return "You don't have any active subscriptions for this vehicle."
            
            # Format the response
            subscriptions_text = "\n".join([
                f"• {service.get('Description')}: Active since {service.get('StartDate').split('T')[0]}"
                f"{', expires on ' + service.get('EndDate').split('T')[0] if service.get('EndDate') else ''}"
                for service in active_services
            ])
            
            return f"Here are your current vehicle subscriptions:\n\n{subscriptions_text}"
        except Exception as e:
            logger.error(f"Failed to get subscriptions: {str(e)}")
            return "I couldn't retrieve your subscription information at this time."
    
    @kernel_function(
        description="Get settings for a specific vehicle feature",
        name="get_feature_settings"
    )
    async def get_feature_settings(self, vehicle_id: str, feature: str = "") -> str:
        """Get settings for a specific vehicle feature."""
        try:
            # Get vehicle status from Cosmos DB to extract settings
            status = await get_latest_status_from_cosmos(vehicle_id)
            
            if not status:
                return f"I couldn't find settings information for vehicle {vehicle_id}."
            
            # Extract feature settings from status
            if feature.lower() == "climate" or feature.lower() == "temperature":
                if "ClimateSettings" in status:
                    climate = status["ClimateSettings"]
                    settings_text = (
                        f"Temperature: {climate.get('temperature')}°C, "
                        f"Fan Speed: {climate.get('fanSpeed')}, "
                        f"AC: {'On' if climate.get('isAirConditioningOn') else 'Off'}, "
                        f"Heating: {'On' if climate.get('isHeatingOn') else 'Off'}"
                    )
                    return f"Current climate settings: {settings_text}"
                else:
                    return "Climate settings information is not available."
            elif feature.lower() == "doors" or feature.lower() == "locks":
                if "DoorStatus" in status:
                    doors = status["DoorStatus"]
                    settings_text = (
                        f"Driver: {doors.get('driver', 'unknown')}, "
                        f"Passenger: {doors.get('passenger', 'unknown')}, "
                        f"Rear Left: {doors.get('rearLeft', 'unknown')}, "
                        f"Rear Right: {doors.get('rearRight', 'unknown')}"
                    )
                    return f"Current door status: {settings_text}"
                else:
                    return "Door status information is not available."
            else:
                return f"Feature '{feature}' is not recognized or not supported."
        except Exception as e:
            logger.error(f"Failed to get feature settings: {str(e)}")
            return "I couldn't retrieve the feature settings due to a system error."
