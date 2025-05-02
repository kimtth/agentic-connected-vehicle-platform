"""
Vehicle Handler module for the Connected Car Platform.

This module provides a comprehensive interface to all vehicle-related features
and integrates with the agent system to provide both direct API access and
agent-mediated natural language interactions.
"""

from vehicle_handler.vehicle_profile_manager import VehicleProfileManager
from vehicle_handler.vehicle_service_manager import VehicleServiceManager
from vehicle_handler.vehicle_api_executor import VehicleAPIExecutor
from vehicle_handler.vehicle_data_manager import VehicleDataManager
from vehicle_handler.vehicle_notification_handler import VehicleNotificationHandler
from vehicle_handler.vehicle_handler import VehicleHandler

__all__ = [
    'VehicleProfileManager',
    'VehicleServiceManager',
    'VehicleAPIExecutor', 
    'VehicleDataManager',
    'VehicleNotificationHandler',
    'VehicleHandler'
]
