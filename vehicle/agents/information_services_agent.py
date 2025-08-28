"""
Information Services Agent for the Connected Car Platform.
"""

from typing import Dict, Any, Optional
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
            instructions="You specialize in providing real-time information including weather, traffic, navigation, and points of interest.",
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
            logger.info(f"FastMCP clients initialized for host {self._base_host}")
        except Exception as e:
            logger.warning(
                f"FastMCP client init failed, will fallback to raw HTTP: {e}"
            )
        else:
            logger.info("fastmcp library not available, using raw HTTP fallback")

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
        self, location: Optional[str] = None, vehicle_id: Optional[str] = None
    ) -> str:
        if not vehicle_id:
            vehicle_id = extract_vehicle_id(None, vehicle_id)

        logger.info(
            f"Getting weather information for location: {location}, vehicle: {vehicle_id}"
        )

        # If still no vehicle_id, use a default location
        if not location and not vehicle_id:
            location = "Tokyo, ON"

        try:
            # Determine coordinates (fallback to default Tokyo, ON)
            coords = await self._get_vehicle_location(vehicle_id)
            # TODO: If location is provided, use it to get coordinates
            if not coords:
                coords = {"latitude": 43.6532, "longitude": -79.3832}
            latitude = coords.get("latitude", 43.6532)
            longitude = coords.get("longitude", -79.3832)
            result = await self._invoke_mcp_tool(
                "weather",
                "get_weather",
                latitude=latitude,
                longitude=longitude,
            )
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error getting weather: {e}")
            return json.dumps({"error": str(e)})

    @kernel_function(
        description="Get traffic information for the vehicle's route",
        name="get_traffic",
    )
    async def _handle_traffic(
        self, route: Optional[str] = None, vehicle_id: Optional[str] = None
    ) -> str:
        if not vehicle_id:
            vehicle_id = extract_vehicle_id(None, vehicle_id)

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
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error getting traffic: {e}")
            return json.dumps({"error": str(e)})

    @kernel_function(
        description="Find points of interest near the vehicle's location",
        name="find_pois",
    )
    async def _handle_pois(
        self, category: Optional[str] = None, vehicle_id: Optional[str] = None
    ) -> str:
        if not vehicle_id:
            vehicle_id = extract_vehicle_id(None, vehicle_id)

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
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error finding POIs: {e}")
            return json.dumps({"error": str(e)})

    @kernel_function(
        description="Get navigation directions to a destination", name="get_directions"
    )
    async def _handle_navigation(
        self, destination: str, vehicle_id: Optional[str] = None
    ) -> str:
        if not vehicle_id:
            vehicle_id = extract_vehicle_id(None, vehicle_id)

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
            return json.dumps(result)
        except Exception as e:
            logger.error(f"Error getting navigation: {e}")
            return json.dumps({"error": str(e)})

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
            vehicle_obj = find_vehicle(vehicles, vehicle_id)
            vehicle = {}
            if vehicle_obj:
                if hasattr(vehicle_obj, "model_dump"):
                    try:
                        vehicle = vehicle_obj.model_dump(by_alias=True)
                    except:
                        vehicle = {}
                elif isinstance(vehicle_obj, dict):
                    vehicle = vehicle_obj

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
        vehicle_id = (context or {}).get("vehicleId") or (context or {}).get("vehicle_id")
        q = (query or "").lower()

        try:
            if "weather" in q:
                raw = await self._handle_weather(vehicle_id=vehicle_id)
                data = self._safe_json(raw)
                return self._format_response(
                    "Here is the current weather.",
                    data={"weather": data, "vehicleId": vehicle_id},
                )
            elif "traffic" in q:
                raw = await self._handle_traffic(route=None, vehicle_id=vehicle_id)
                data = self._safe_json(raw)
                return self._format_response(
                    "Here are the current traffic conditions.",
                    data={"traffic": data, "vehicleId": vehicle_id},
                )
            elif "poi" in q or "point of interest" in q or "places" in q:
                raw = await self._handle_pois(category=None, vehicle_id=vehicle_id)
                data = self._safe_json(raw)
                return self._format_response(
                    "Here are nearby points of interest.",
                    data={"pois": data, "vehicleId": vehicle_id},
                )
            elif "navigation" in q or "directions" in q or "route" in q:
                destination = (context or {}).get("destination") or "destination"
                raw = await self._handle_navigation(
                    destination=destination, vehicle_id=vehicle_id
                )
                data = self._safe_json(raw)
                return self._format_response(
                    f"Directions to {destination}.",
                    data={"navigation": data, "vehicleId": vehicle_id},
                )
            else:
                return self._format_response(
                    "I can provide weather updates, traffic conditions, points of interest, and navigation assistance. What do you need?",
                    data=self._get_capabilities(),
                )
        except Exception as e:
            logger.error(f"Information services processing error: {e}")
            return self._format_response(
                "Information services are temporarily unavailable.", success=False
            )

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
            "pointsOfInterest": "Find nearby points of interest",
            "navigation": "Set up and manage navigation to destinations",
        }

    def _format_response(
        self, message: str, success: bool = True, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        resp = {"message": message, "success": success}
        if data:
            resp["data"] = data
        return resp
