"""
Information Services Agent for the Connected Car Platform.

This agent provides real-time vehicle-related information such as weather, traffic,
and points of interest.
"""
from typing import Dict, Any, Optional
from semantic_kernel.connectors.mcp import MCPStdioPlugin
from azure.cosmos_db import cosmos_client
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from utils.logging_config import get_logger
from semantic_kernel import create_chat_service
import json

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

    def __init__(self):
        # register MCP-based tools
        self.weather_tool = MCPStdioPlugin("weather_service")
        self.traffic_tool = MCPStdioPlugin("traffic_service")
        self.poi_tool     = MCPStdioPlugin("poi_service")
        self.nav_tool     = MCPStdioPlugin("navigation_service")

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
            # Determine coordinates (fallback to default Toronto, ON)
            coords = await self._get_vehicle_location(vehicle_id)
            # TODO: If location is provided, use it to get coordinates
            if not coords:
                coords = {"latitude": 43.6532, "longitude": -79.3832}
            latitude = coords.get("latitude", 43.6532)
            longitude = coords.get("longitude", -79.3832)
            # Call the MCP weather tool
            return await self.weather_tool.invoke_async(
                "get_weather", latitude, longitude
            )
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
            coords = await self._get_vehicle_location(vehicle_id)
            latitude = coords.get("latitude", 0.0)
            longitude = coords.get("longitude", 0.0)
            result = await self.traffic_tool.invoke_async(
                "get_traffic", route or "current route", latitude, longitude
            )
            return json.dumps(result)
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
            coords = await self._get_vehicle_location(vehicle_id)
            latitude = coords.get("latitude", 0.0)
            longitude = coords.get("longitude", 0.0)
            result = await self.poi_tool.invoke_async(
                "find_pois", category or "general", latitude, longitude
            )
            return json.dumps(result)
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
            coords = await self._get_vehicle_location(vehicle_id)
            latitude = coords.get("latitude", 0.0)
            longitude = coords.get("longitude", 0.0)
            result = await self.nav_tool.invoke_async(
                "get_directions", destination, latitude, longitude
            )
            return json.dumps(result)
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