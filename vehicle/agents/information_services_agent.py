"""
Information Services Agent for the Connected Car Platform.
"""

from typing import Dict, Any, Optional, Annotated
from azure.cosmos_db import get_cosmos_client
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from utils.logging_config import get_logger
from plugin.oai_service import create_chat_service
from utils.vehicle_object_utils import find_vehicle
from utils.agent_context import extract_vehicle_id
import json
from fastmcp import Client


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
            instructions=(
                "You specialize in providing real-time information including weather, traffic, navigation, and points of interest. "
                "IMPORTANT: Return the EXACT JSON response from your plugin functions without modification."
            ),
            plugins=[InformationServicesPlugin()],
        )


class InformationServicesPlugin:
    """Plugin for information services operations."""

    def __init__(self):
        self.cosmos_client = get_cosmos_client()
        self._base_host = "127.0.0.1"
        # Build base URLs
        self._svc_urls = {
            "weather": f"http://{self._base_host}:8001/mcp",
            "traffic": f"http://{self._base_host}:8002/mcp",
            "poi": f"http://{self._base_host}:8003/mcp",
            "navigation": f"http://{self._base_host}:8004/mcp",
        }
        self.weather_client = None
        self.traffic_client = None
        self.poi_client = None
        self.nav_client = None

        try:
            from fastmcp import Client
            self.weather_client = Client(self._svc_urls["weather"])
            self.traffic_client = Client(self._svc_urls["traffic"])
            self.poi_client = Client(self._svc_urls["poi"])
            self.nav_client = Client(self._svc_urls["navigation"])
            self._fastmcp_entered: dict[str, bool] = {
                "weather": False,
                "traffic": False,
                "poi": False,
                "navigation": False,
            }
            logger.info(f"FastMCP clients initialized successfully for host {self._base_host}")
        except ImportError:
            logger.info("fastmcp library not available, using raw HTTP fallback")
        except Exception as e:
            logger.warning(f"FastMCP client initialization failed, will fallback to raw HTTP: {e}")

    async def _enter_fastmcp(self, service: str, client) -> bool:
        """
        Lazily enter (async context) the FastMCP client once.
        Returns True if ready, False if failed.
        """
        if not client:
            return False
        try:
            if not getattr(self, "_fastmcp_entered", {}).get(service):
                await client.__aenter__()
                self._fastmcp_entered[service] = True
            return True
        except Exception as e:
            logger.debug(f"FastMCP __aenter__ failed for {service}: {e}")
            return False

    async def _invoke_mcp_tool(self, service: str, tool: str, **kwargs) -> dict:
        """
        Invoke an MCP tool using FastMCP (preferred). If fastmcp lib not installed, use raw HTTP.
        """
        url = self._svc_urls.get(service)
        if not url:
            return {"error": f"unknown service {service}"}

        client_map = {
            "weather": self.weather_client,
            "traffic": self.traffic_client,
            "poi": self.poi_client,
            "navigation": self.nav_client,
        }
        client = client_map.get(service)
        if not client or not await self._enter_fastmcp(service, client):
            return {"error": f"{service} client unavailable"}
        try:
            result = await client.call_tool(tool, kwargs)
            return result if isinstance(result, dict) else {"result": result}
        except Exception as e:
            return {"error": f"{service}.{tool} failed", "detail": str(e)}

    @kernel_function(
        description="Get weather information for the vehicle's location",
        name="get_weather",
    )
    async def _handle_weather(
        self,
        location: Annotated[str, "Override location (city or coords)"] = "",
        vehicle_id: Annotated[str, "Vehicle GUID for location lookup"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context"] = {},
        **kwargs
    ) -> str:
        if not vehicle_id:
            vehicle_id = extract_vehicle_id(call_context, vehicle_id or None)

        logger.info(
            f"Getting weather information for location: {location}, vehicle: {vehicle_id}"
        )

        try:
            # Determine coordinates (fallback to default Tokyo)
            coords = await self._get_vehicle_location(vehicle_id)
            if not coords:
                # If coords is None, use the default location.
                coords = {"latitude": 35.6895, "longitude": 139.6917}
            latitude = coords.get("latitude", 35.6895)
            longitude = coords.get("longitude", 139.6917)
            result = await self._invoke_mcp_tool(
                "weather",
                "get_weather",
                latitude=latitude,
                longitude=longitude,
            )
            # ensure result is JSON-serializable
            serializable = self._ensure_serializable(result)
            return json.dumps({
                "message": "Weather data retrieved.",
                "data": serializable,
                "success": True,
                "plugins_used": [f"{self.__class__.__name__}._handle_weather"]
            })
        except Exception as e:
            return json.dumps({
                "message": "Error getting weather.",
                "success": False,
                "error": str(e),
                "plugins_used": [f"{self.__class__.__name__}._handle_weather"]
            })

    @kernel_function(
        description="Get traffic information for the vehicle's route",
        name="get_traffic",
    )
    async def _handle_traffic(
        self,
        route: Annotated[str, "Route or segment description"] = "",
        vehicle_id: Annotated[str, "Vehicle GUID for current position"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context"] = {},
        **kwargs
    ) -> str:
        if not vehicle_id:
            vehicle_id = extract_vehicle_id(call_context, vehicle_id or None)

        logger.info(
            f"Getting traffic information for route: {route}, vehicle: {vehicle_id}"
        )

        try:
            coords = await self._get_vehicle_location(vehicle_id)
            result = await self._invoke_mcp_tool(
                "traffic",
                "get_traffic",
                route=route or "current route",
                latitude=coords.get("latitude", 0.0),
                longitude=coords.get("longitude", 0.0),
            )
            serializable = self._ensure_serializable(result)
            return json.dumps({
                "message": "Traffic data retrieved.",
                "data": serializable,
                "success": True,
                "plugins_used": [f"{self.__class__.__name__}._handle_traffic"]
            })
        except Exception as e:
            return json.dumps({
                "message": "Error getting traffic.",
                "success": False,
                "error": str(e),
                "plugins_used": [f"{self.__class__.__name__}._handle_traffic"]
            })

    @kernel_function(
        description="Find points of interest near the vehicle's location",
        name="find_pois",
    )
    async def _handle_pois(
        self,
        category: Annotated[str, "POI category (e.g., food, gas)"] = "",
        vehicle_id: Annotated[str, "Vehicle GUID for location lookup"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context"] = {},
        **kwargs
    ) -> str:
        if not vehicle_id:
            vehicle_id = extract_vehicle_id(call_context, vehicle_id or None)

        logger.info(f"Finding POIs for category: {category}, vehicle: {vehicle_id}")

        try:
            coords = await self._get_vehicle_location(vehicle_id)
            result = await self._invoke_mcp_tool(
                "poi",
                "find_pois",
                category=category or "general",
                latitude=coords.get("latitude", 0.0),
                longitude=coords.get("longitude", 0.0),
            )
            serializable = self._ensure_serializable(result)
            return json.dumps({
                "message": "POIs retrieved.",
                "data": serializable,
                "success": True,
                "plugins_used": [f"{self.__class__.__name__}._handle_pois"]
            })
        except Exception as e:
            return json.dumps({
                "message": "Error finding POIs.",
                "success": False,
                "error": str(e),
                "plugins_used": [f"{self.__class__.__name__}._handle_pois"]
            })

    @kernel_function(
        description="Get navigation directions to a destination", name="get_directions"
    )
    async def _handle_navigation(
        self,
        destination: Annotated[str, "Destination address or place name"],
        vehicle_id: Annotated[str, "Vehicle GUID for origin"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context"] = {},
        **kwargs
    ) -> str:
        if not vehicle_id:
            vehicle_id = extract_vehicle_id(call_context, vehicle_id or None)

        logger.info(f"Getting navigation to: {destination}, vehicle: {vehicle_id}")

        try:
            coords = await self._get_vehicle_location(vehicle_id)
            result = await self._invoke_mcp_tool(
                "navigation",
                "get_directions",
                destination=destination,
                latitude=coords.get("latitude", 0.0),
                longitude=coords.get("longitude", 0.0),
            )
            # CallToolResult
            serializable = self._ensure_serializable(result)
            return json.dumps({
                "message": "Navigation retrieved.",
                "data": serializable,
                "success": True,
                "plugins_used": [f"{self.__class__.__name__}._handle_navigation"]
            })
        except Exception as e:
            return json.dumps({
                "message": "Error getting navigation.",
                "success": False,
                "error": str(e),
                "plugins_used": [f"{self.__class__.__name__}._handle_navigation"]
            })

    def _ensure_serializable(self, result):
        """Return a JSON-serializable representation of obj."""
        try:
            json.dumps(result)
            return result
        except (TypeError, OverflowError):
            return str(result)

    async def _get_vehicle_location(self, vehicle_id: Optional[str]) -> Dict[str, Any]:
        """Get the vehicle's current location from Cosmos DB."""
        if not vehicle_id:
            return {}

        try:
            # Get vehicle status for location
            vehicle_info = await self.cosmos_client.get_vehicle(vehicle_id)

            if vehicle_info and "lastLocation" in vehicle_info:
                # Convert to lowercase keys for consistency
                return {
                    "latitude": vehicle_info["lastLocation"].get("latitude", 0),
                    "longitude": vehicle_info["lastLocation"].get("longitude", 0),
                }

            return {}
        except Exception as e:
            logger.error(f"Error getting vehicle location: {e}")
            return {}

    def _format_response(
        self, message: str, success: bool = True, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        resp = {"message": message, "success": success}
        if data:
            resp["data"] = data
        return resp
