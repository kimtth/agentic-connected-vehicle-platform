"""
Information Services Agent for the Connected Car Platform.
"""
from typing import Dict, Any, Optional
import aiohttp
from azure.cosmos_db import get_cosmos_client
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from utils.logging_config import get_logger
from plugin.oai_service import create_chat_service  # fixed import
import json
import os

logger = get_logger(__name__)

class InformationServicesAgent:
    """
    Information Services Agent for providing real-time information.
    """

    def __init__(self):
        """Initialize the Information Services Agent."""
        # Get the singleton cosmos client instance
        self.cosmos_client = get_cosmos_client()
        service_factory = create_chat_service()
        self.agent = ChatCompletionAgent(
            service=service_factory,
            name="InformationServicesAgent",
            instructions="You specialize in providing real-time information including weather, traffic, navigation, and points of interest.",
            plugins=[InformationServicesPlugin()],
        )

class MCPSSEClient:
    """Simple SSE client for MCP servers."""
    
    def __init__(self, base_url: str, service_name: str):
        self.base_url = base_url
        self.service_name = service_name
        self.session = None
    
    async def invoke_async(self, tool_name: str, *args, **kwargs):
        """Invoke a tool on the MCP server via HTTP."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        # Construct the request payload
        payload = {
            "tool": tool_name,
            "arguments": {
                **{f"arg{i}": arg for i, arg in enumerate(args)},
                **kwargs
            }
        }
        
        try:
            async with self.session.post(
                f"{self.base_url}/invoke",
                json=payload,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"MCP server error: {error_text}")
                    return {"error": f"Server returned {response.status}: {error_text}"}
        except Exception as e:
            logger.error(f"Error invoking MCP tool {tool_name}: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Close the HTTP session."""
        if self.session:
            await self.session.close()

class InformationServicesPlugin:
    """Plugin for information services operations."""

    def __init__(self):
        # Get the singleton cosmos client instance
        self.cosmos_client = get_cosmos_client()
        
        try:
            # Get base URLs for each MCP server
            base_host = os.environ.get("MCP_SERVER_HOST", "localhost")
            
            # Initialize SSE clients for each MCP server running on different ports
            self.weather_tool = MCPSSEClient(f"http://{base_host}:8001", "weather_service")
            self.traffic_tool = MCPSSEClient(f"http://{base_host}:8002", "traffic_service")
            self.poi_tool = MCPSSEClient(f"http://{base_host}:8003", "poi_service")
            self.nav_tool = MCPSSEClient(f"http://{base_host}:8004", "navigation_service")
            
            logger.info(f"MCP SSE clients initialized for host: {base_host}")
        except Exception as e:
            logger.warning(f"MCP tools not initialized: {e}")
            self.weather_tool = self.traffic_tool = self.poi_tool = self.nav_tool = None

    @kernel_function(description="Get weather information for the vehicle's location", name="get_weather")
    async def _handle_weather(self, location: Optional[str] = None, vehicle_id: Optional[str] = None) -> str:
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
            if not self.weather_tool:
                return json.dumps({"error": "weather tool unavailable"})
            # Call the MCP weather tool with proper argument names
            result = await self.weather_tool.invoke_async(
                "get_weather", 
                latitude=latitude, 
                longitude=longitude
            )
            return json.dumps(result) if isinstance(result, dict) else result
        except Exception as e:
            logger.error(f"Error getting weather: {e}")
            return f"Weather information is currently unavailable. Error: {str(e)}"

    @kernel_function(description="Get traffic information for the vehicle's route", name="get_traffic")
    async def _handle_traffic(self, route: Optional[str] = None, vehicle_id: Optional[str] = None) -> str:
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
            if not self.traffic_tool:
                return json.dumps({"error": "traffic tool unavailable"})
            result = await self.traffic_tool.invoke_async(
                "get_traffic", 
                route=route or "current route", 
                latitude=coords.get("latitude", 0.0), 
                longitude=coords.get("longitude", 0.0)
            )
            return json.dumps(result) if isinstance(result, dict) else result
        except Exception as e:
            logger.error(f"Error getting traffic information: {e}")
            return f"Traffic information is currently unavailable. Error: {str(e)}"

    @kernel_function(description="Find points of interest near the vehicle's location", name="find_pois")
    async def _handle_pois(self, category: Optional[str] = None, vehicle_id: Optional[str] = None) -> str:
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
            if not self.poi_tool:
                return json.dumps({"error": "poi tool unavailable"})
            result = await self.poi_tool.invoke_async(
                "find_pois", 
                category=category or "general", 
                latitude=coords.get("latitude", 0.0), 
                longitude=coords.get("longitude", 0.0)
            )
            return json.dumps(result) if isinstance(result, dict) else result
        except Exception as e:
            logger.error(f"Error finding POIs: {e}")
            return f"Points of interest search is currently unavailable. Error: {str(e)}"

    @kernel_function(description="Get navigation directions to a destination", name="get_directions")
    async def _handle_navigation(self, destination: str, vehicle_id: Optional[str] = None) -> str:
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
            if not self.nav_tool:
                return json.dumps({"error": "navigation tool unavailable"})
            result = await self.nav_tool.invoke_async(
                "get_directions", 
                destination=destination, 
                latitude=coords.get("latitude", 0.0), 
                longitude=coords.get("longitude", 0.0)
            )
            return json.dumps(result) if isinstance(result, dict) else result
        except Exception as e:
            logger.error(f"Error getting navigation directions: {e}")
            return f"Navigation service is currently unavailable. Error: {str(e)}"

    async def _get_vehicle_location(self, vehicle_id: Optional[str]) -> Dict[str, Any]:
        """Get the vehicle's current location from Cosmos DB."""
        if not vehicle_id:
            return {}

        try:
            # Get vehicle status for location
            vehicle_status = await self.cosmos_client.get_vehicle_status(vehicle_id)

            if vehicle_status:
                # Check for location in status
                if "location" in vehicle_status:
                    return vehicle_status["location"]

            # Try to get from vehicle data if not in status
            vehicles = await self.cosmos_client.list_vehicles()
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

    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process information services requests and wrap tool output."""
        vehicle_id = context.get("vehicle_id") if context else None
        q = (query or "").lower()

        try:
            if "weather" in q:
                raw = await self._handle_weather(vehicle_id=vehicle_id)
                data = self._safe_json(raw)
                return self._format_response("Here is the current weather.", data={"weather": data, "vehicle_id": vehicle_id})
            elif "traffic" in q:
                raw = await self._handle_traffic(route=None, vehicle_id=vehicle_id)
                data = self._safe_json(raw)
                return self._format_response("Here are the current traffic conditions.", data={"traffic": data, "vehicle_id": vehicle_id})
            elif "poi" in q or "point of interest" in q or "places" in q:
                raw = await self._handle_pois(category=None, vehicle_id=vehicle_id)
                data = self._safe_json(raw)
                return self._format_response("Here are nearby points of interest.", data={"pois": data, "vehicle_id": vehicle_id})
            elif "navigation" in q or "directions" in q or "route" in q:
                # naive destination extraction, fallback to 'destination'
                destination = context.get("destination") if context else "destination"
                raw = await self._handle_navigation(destination=destination, vehicle_id=vehicle_id)
                data = self._safe_json(raw)
                return self._format_response(f"Directions to {destination}.", data={"navigation": data, "vehicle_id": vehicle_id})
            else:
                return self._format_response(
                    "I can provide weather updates, traffic conditions, points of interest, and navigation assistance. What do you need?",
                    data=self._get_capabilities(),
                )
        except Exception as e:
            logger.error(f"Information services processing error: {e}")
            return self._format_response("Information services are temporarily unavailable.", success=False)

    def _safe_json(self, value: Any) -> Any:
        try:
            return value if isinstance(value, (dict, list)) else json.loads(value)
        except Exception:
            return {"raw": value}

    def _get_capabilities(self) -> Dict[str, str]:
        """Get the capabilities of this agent."""
        return {
            "weather": "Get current weather and forecast information",
            "traffic": "Check traffic conditions and incidents",
            "points_of_interest": "Find nearby points of interest",
            "navigation": "Set up and manage navigation to destinations",
        }

    def _format_response(self, message: str, success: bool = True, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return {"message": message, "success": success, "data": data or {}}