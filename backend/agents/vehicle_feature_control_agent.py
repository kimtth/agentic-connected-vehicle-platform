"""
Vehicle Feature Control Agent for the Connected Car Platform.

This agent manages in-car features like climate settings, temperature control,
and service subscriptions.
"""

import logging
import random
from typing import Dict
from agents.base_agent import BaseAgent
from utils.agent_tools import validate_command
from semantic_kernel.functions import kernel_function

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
        
        # Mock data for demonstration
        self.mock_subscriptions = [
            {"id": "sub001", "name": "Premium Navigation", "status": "active", "expiry": "2026-01-15"},
            {"id": "sub002", "name": "Remote Access", "status": "active", "expiry": "2025-12-31"},
            {"id": "sub003", "name": "In-Car WiFi", "status": "inactive", "expiry": None},
            {"id": "sub004", "name": "Advanced Driver Assistance", "status": "active", "expiry": "2025-09-30"},
            {"id": "sub005", "name": "Entertainment Package", "status": "trial", "expiry": "2025-06-01"},
        ]
    
    @kernel_function(
        description="Adjust climate control settings in the vehicle",
        name="adjust_climate_control"
    )
    def adjust_climate_control(
        self, 
        vehicle_id: str, 
        temperature: float = 22.0, 
        fan_speed: str = "medium"
    ) -> str:
        """Adjust the climate control settings in the vehicle."""
        # Validate the command
        command_type = "ACTIVATE_CLIMATE"
        validation = validate_command(
            command_id="feature_control_climate",
            command_type=command_type,
            parameters={"temperature": temperature, "fan_speed": fan_speed}
        )
        
        if not validation["valid"]:
            return f"Failed to adjust the climate control: {validation.get('error', 'Unknown error')}"
        
        # In a real implementation, this would send a command to the vehicle
        return (
            f"Climate control settings adjusted. Temperature is now set to {temperature}°C "
            f"with {fan_speed} fan speed."
        )
    
    @kernel_function(
        description="Get active subscriptions for the vehicle",
        name="get_subscriptions"
    )
    def get_subscriptions(self, vehicle_id: str) -> str:
        """Get active subscriptions for the vehicle."""
        # In a real implementation, this would query the vehicle's subscription database
        active_subscriptions = [sub for sub in self.mock_subscriptions if sub["status"] in ["active", "trial"]]
        
        if not active_subscriptions:
            return "You don't have any active subscriptions for this vehicle."
        
        # Format the response
        subscriptions_text = "\n".join([
            f"• {sub['name']}: {sub['status'].title()}{f', expires on {sub['expiry']}' if sub['expiry'] else ''}"
            for sub in active_subscriptions
        ])
        
        return f"Here are your current vehicle subscriptions:\n\n{subscriptions_text}"
    
    @kernel_function(
        description="Get settings for a specific vehicle feature",
        name="get_feature_settings"
    )
    def get_feature_settings(self, vehicle_id: str, feature: str = "") -> str:
        """Get settings for a specific vehicle feature."""
        # Mock data for demonstration
        feature_settings = {
            "climate": {"temperature": 22.0, "fan_speed": "medium", "mode": "auto"},
            "lighting": {"interior_brightness": 70, "exterior_mode": "auto"},
            "seats": {"driver_position": "preset1", "heating_level": "off"},
            "display": {"brightness": 80, "theme": "default"},
            "audio": {"volume": 12, "equalizer": "balanced"}
        }
        
        if not feature:
            # Return all settings
            settings_text = "\n".join([
                f"• {feat.title()}: {', '.join([f'{k}={v}' for k, v in settings.items()])}"
                for feat, settings in feature_settings.items()
            ])
            
            return f"Here are all your vehicle feature settings:\n\n{settings_text}"
        
        feature = feature.lower()
        if feature not in feature_settings:
            return f"I don't have information about {feature} settings."
        
        # Format the response
        settings_text = ", ".join([f"{k}: {v}" for k, v in feature_settings[feature].items()])
        
        return f"Here are your {feature} settings: {settings_text}"
    
    @kernel_function(
        description="Activate a vehicle feature",
        name="activate_feature"
    )
    def activate_feature(self, vehicle_id: str, feature: str) -> str:
        """Activate a vehicle feature."""
        # In a real implementation, this would send a command to activate the feature
        # Mock success for demonstration
        success = random.choice([True, False])
        
        if success:
            return f"I've activated the {feature.replace('_', ' ')} feature for you."
        else:
            return (
                f"I couldn't activate the {feature.replace('_', ' ')} feature. "
                "It may not be available for your vehicle or requires a subscription."
            )
    
    @kernel_function(
        description="Deactivate a vehicle feature",
        name="deactivate_feature"
    )
    def deactivate_feature(self, vehicle_id: str, feature: str) -> str:
        """Deactivate a vehicle feature."""
        # In a real implementation, this would send a command to deactivate the feature
        # Mock success for demonstration
        success = random.choice([True, False])
        
        if success:
            return f"I've deactivated the {feature.replace('_', ' ')} feature for you."
        else:
            return (
                f"I couldn't deactivate the {feature.replace('_', ' ')} feature. "
                "It may not be currently active."
            )
    
    def _get_capabilities(self) -> Dict[str, str]:
        """Get the capabilities of this agent."""
        return {
            "climate_control": "Adjust climate settings including temperature and fan speed",
            "feature_activation": "Activate vehicle features like seat heating, parking assist, etc.",
            "feature_deactivation": "Deactivate vehicle features",
            "feature_settings": "View and adjust vehicle feature settings",
            "subscriptions": "Manage vehicle service subscriptions"
        }
