"""
Information Services Agent for the Connected Car Platform.

This agent provides real-time vehicle-related information such as weather, traffic,
and points of interest.
"""

import os
import sys
import datetime
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

# Use the weather MCP server to get weather data
from semantic_kernel.connectors.mcp import MCPStdioPlugin
from azure.cosmos_db import cosmos_client
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from plugin.oai_service import create_chat_service
from utils.logging_config import get_logger

logger = get_logger(__name__)


class InformationServicesAgent:
    """
    Information Services Agent for providing real-time information.
    """

    def __init__(self):
        """Initialize the Information Services Agent."""
        service_factory = create_chat_service()
        self.agent = ChatCompletionAgent(
            service=service_factory,
            name="InformationServicesAgent",
            instructions="You specialize in providing real-time information including weather, traffic, navigation, and points of interest.",
            plugins=[InformationServicesPlugin()],
        )


class InformationServicesPlugin:
    """Plugin for information services operations."""

    @kernel_function(
        description="Get weather information for the vehicle's location",
        name="get_weather",
    )
    async def _handle_weather(
        self, 
        location: Optional[str] = None,
        vehicle_id: Optional[str] = None
    ) -> str:
        """Get weather information for a specific location or vehicle."""
        # Extract vehicle_id from context if not provided directly
        if not vehicle_id:
            # Try to get vehicle_id from kernel context
            try:
                from semantic_kernel.kernel import Kernel
                kernel = Kernel.get_current()
                if kernel and hasattr(kernel, 'arguments'):
                    vehicle_id = kernel.arguments.get('vehicle_id')
            except:
                pass
        
        logger.info(f"Getting weather information for location: {location}, vehicle: {vehicle_id}")
        
        # If still no vehicle_id, use a default location
        if not location and not vehicle_id:
            location = "Toronto, ON"
            
        try:
            return await weather_service.get_weather(location or "current location")
        except Exception as e:
            logger.error(f"Error getting weather: {e}")
            return f"Weather information is currently unavailable. Error: {str(e)}"

    @kernel_function(
        description="Get traffic information for the vehicle's route",
        name="get_traffic",
    )
    async def _handle_traffic(
        self, 
        route: Optional[str] = None,
        vehicle_id: Optional[str] = None
    ) -> str:
        """Get traffic information for a specific route or vehicle location."""
        # Extract vehicle_id from context if not provided directly
        if not vehicle_id:
            try:
                from semantic_kernel.kernel import Kernel
                kernel = Kernel.get_current()
                if kernel and hasattr(kernel, 'arguments'):
                    vehicle_id = kernel.arguments.get('vehicle_id')
            except:
                pass
                
        logger.info(f"Getting traffic information for route: {route}, vehicle: {vehicle_id}")
        
        try:
            return await traffic_service.get_traffic_info(route or "current route")
        except Exception as e:
            logger.error(f"Error getting traffic information: {e}")
            return f"Traffic information is currently unavailable. Error: {str(e)}"

    @kernel_function(
        description="Find points of interest near the vehicle's location",
        name="find_pois",
    )
    async def _handle_pois(
        self, 
        category: Optional[str] = None,
        vehicle_id: Optional[str] = None
    ) -> str:
        """Find points of interest near the vehicle's location."""
        # Extract vehicle_id from context if not provided directly
        if not vehicle_id:
            try:
                from semantic_kernel.kernel import Kernel
                kernel = Kernel.get_current()
                if kernel and hasattr(kernel, 'arguments'):
                    vehicle_id = kernel.arguments.get('vehicle_id')
            except:
                pass
                
        logger.info(f"Finding POIs for category: {category}, vehicle: {vehicle_id}")
        
        try:
            return await poi_service.find_points_of_interest(
                category or "general", 
                vehicle_id=vehicle_id
            )
        except Exception as e:
            logger.error(f"Error finding POIs: {e}")
            return f"Points of interest search is currently unavailable. Error: {str(e)}"

    @kernel_function(
        description="Get navigation directions to a destination",
        name="get_directions",
    )
    async def _handle_navigation(
        self, 
        destination: str,
        vehicle_id: Optional[str] = None
    ) -> str:
        """Get navigation directions to a destination."""
        # Extract vehicle_id from context if not provided directly
        if not vehicle_id:
            try:
                from semantic_kernel.kernel import Kernel
                kernel = Kernel.get_current()
                if kernel and hasattr(kernel, 'arguments'):
                    vehicle_id = kernel.arguments.get('vehicle_id')
            except:
                pass
                
        logger.info(f"Getting navigation to: {destination}, vehicle: {vehicle_id}")
        
        try:
            return await navigation_service.get_directions(destination, vehicle_id=vehicle_id)
        except Exception as e:
            logger.error(f"Error getting navigation directions: {e}")
            return f"Navigation service is currently unavailable. Error: {str(e)}"

    async def _get_vehicle_location(self, vehicle_id: Optional[str]) -> Dict[str, Any]:
        """Get the vehicle's current location from Cosmos DB."""
        if not vehicle_id:
            return {}

        try:
            # Get vehicle status for location
            vehicle_status = await cosmos_client.get_vehicle_status(vehicle_id)

            if vehicle_status:
                # Check for location in status
                if "location" in vehicle_status:
                    return vehicle_status["location"]

            # Try to get from vehicle data if not in status
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next(
                (v for v in vehicles if v.get("VehicleId") == vehicle_id), None
            )

            if vehicle and "LastLocation" in vehicle:
                # Convert to lowercase keys for consistency
                return {
                    "latitude": vehicle["LastLocation"].get("Latitude", 0),
                    "longitude": vehicle["LastLocation"].get("Longitude", 0),
                }

            return {}
        except Exception as e:
            logger.error(f"Error getting vehicle location: {e}")
            return {}

    async def process(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process information services requests."""
        vehicle_id = context.get("vehicle_id") if context else None
        query_lower = query.lower()

        if "weather" in query_lower:
            return await self._handle_weather(vehicle_id, context)
        elif "traffic" in query_lower:
            return await self._handle_traffic(vehicle_id, context)
        elif "poi" in query_lower or "point of interest" in query_lower or "places" in query_lower:
            return await self._handle_pois(vehicle_id, context)
        elif "navigation" in query_lower or "directions" in query_lower or "route" in query_lower:
            return await self._handle_navigation(vehicle_id, query, context)
        else:
            return self._format_response(
                "I can provide you with real-time information related to your vehicle and journey, "
                "including weather updates, traffic conditions, points of interest, and navigation assistance. "
                "What kind of information would you like?",
                data=self._get_capabilities(),
            )

    def _get_capabilities(self) -> Dict[str, str]:
        """Get the capabilities of this agent."""
        return {
            "weather": "Get current weather and forecast information",
            "traffic": "Check traffic conditions and incidents",
            "points_of_interest": "Find nearby points of interest",
            "navigation": "Set up and manage navigation to destinations",
        }

    def _format_response(
        self, message: str, success: bool = True, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Format the response to be returned by the agent."""
        return {
            "message": message,
            "success": success,
            "data": data or {},
        }
