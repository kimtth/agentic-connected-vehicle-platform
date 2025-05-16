"""
Information Services Agent for the Connected Car Platform.

This agent provides real-time vehicle-related information such as weather, traffic,
and points of interest.
"""

import os
import sys
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
    Information Services Agent for providing real-time vehicle information.
    """

    def __init__(self):
        """Initialize the Information Services Agent."""
        service_factory = create_chat_service()
        self.agent = ChatCompletionAgent(
            service=service_factory,
            name="InformationServicesAgent",
            instructions="You specialize in information services.",
            plugins=[InformationServicesPlugin()],
        )


class InformationServicesPlugin:
    @kernel_function(description="Handle weather information requests")
    async def _handle_weather(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle a weather information request."""
        try:
            # Get vehicle location from Cosmos DB
            location = await self._get_vehicle_location(vehicle_id)

            if not location:
                return self._format_response(
                    "I couldn't determine your vehicle's location to fetch weather information.",
                    success=False,
                )

            # Get the path to the weather_mcp.py script
            current_dir = os.path.dirname(os.path.abspath(__file__))
            plugin_dir = os.path.join(os.path.dirname(current_dir), "plugin")

            async with MCPStdioPlugin(
                name="WeatherService",
                description="Weather Service Plugin",
                command=sys.executable,  # Use the current Python executable
                args=[os.path.join(plugin_dir, "weather_mcp.py")],
            ) as weather_plugin:
                # Get latitude and longitude from location
                latitude = location.get("latitude", 0)
                longitude = location.get("longitude", 0)

                # Call the get_weather function from the MCP server
                result = await weather_plugin.invoke_tool(
                    "get_weather", latitude=latitude, longitude=longitude
                )
                weather_data = result.value

                # Extract the current weather and forecast
                current = weather_data["current"]
                forecast = weather_data["forecast"]

                return self._format_response(
                    f"Current weather at your vehicle's location: {current['condition']}, {current['temperature']}°C with "
                    f"{current['humidity']}% humidity and wind at {current['wind_speed']} km/h. "
                    f"\n\nForecast:\n"
                    f"• Today: {forecast[0]['condition']}, {forecast[0]['high']}°C / {forecast[0]['low']}°C\n"
                    f"• Tomorrow: {forecast[1]['condition']}, {forecast[1]['high']}°C / {forecast[1]['low']}°C\n"
                    f"• Day After: {forecast[2]['condition']}, {forecast[2]['high']}°C / {forecast[2]['low']}°C",
                    data={"weather": weather_data, "vehicle_id": vehicle_id},
                )
        except Exception as e:
            logger.error(f"Error retrieving weather information: {str(e)}")
            return self._format_response(
                "I encountered an error while retrieving weather information. Please try again later.",
                success=False,
            )

    @kernel_function(description="Handle traffic information requests")
    async def _handle_traffic(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle a traffic information request."""
        try:
            # Get vehicle location and status from Cosmos DB
            location = await self._get_vehicle_location(vehicle_id)
            vehicle_status = await self._get_vehicle_status(vehicle_id)

            if not location:
                return self._format_response(
                    "I couldn't determine your vehicle's location to fetch traffic information.",
                    success=False,
                )

            # Get current speed from vehicle status if available
            current_speed = vehicle_status.get("Speed", 0) if vehicle_status else 0

            # In a production environment, we would call a traffic API with the location
            # For demonstration, we'll derive some traffic data from the vehicle's status

            # Generate traffic condition based on time of day (rush hour or not)
            current_hour = datetime.now().hour
            is_rush_hour = 7 <= current_hour <= 9 or 16 <= current_hour <= 18

            congestion_level = "High" if is_rush_hour else "Low"
            normal_speed = 100 if not is_rush_hour else 60

            # Generate an incident if in rush hour (with 50% probability)
            incidents = []
            if is_rush_hour and bool(int(location.get("latitude", 0) * 100) % 2):
                incidents.append(
                    {
                        "type": "Congestion",
                        "location": "Highway ahead",
                        "delay_minutes": 15,
                    }
                )

            traffic_data = {
                "location": location,
                "current_speed": current_speed,
                "normal_speed": normal_speed,
                "congestion_level": congestion_level,
                "incidents": incidents,
                "timestamp": datetime.now().isoformat(),
            }

            # Format the response
            incidents_text = ""
            if incidents:
                incidents_text = "\n\nTraffic incidents:\n" + "\n".join(
                    [
                        f"• {incident['type']} at {incident['location']}: {incident['delay_minutes']} min delay"
                        for incident in incidents
                    ]
                )

            return self._format_response(
                f"Current traffic conditions: {congestion_level} congestion. "
                f"Traffic is moving at {current_speed if current_speed > 0 else 'unknown'} km/h "
                f"(normal speed: {normal_speed} km/h).{incidents_text}",
                data={"traffic": traffic_data, "vehicle_id": vehicle_id},
            )
        except Exception as e:
            logger.error(f"Error retrieving traffic information: {str(e)}")
            return self._format_response(
                "I encountered an error while retrieving traffic information. Please try again later.",
                success=False,
            )

    @kernel_function(description="Handle points of interest requests")
    async def _handle_pois(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle a points of interest request."""
        try:
            # Get vehicle location from Cosmos DB
            location = await self._get_vehicle_location(vehicle_id)

            if not location:
                return self._format_response(
                    "I couldn't determine your vehicle's location to find points of interest.",
                    success=False,
                )

            # Get points of interest from Cosmos DB
            category = context.get("poi_category") if context else None

            # Ensure connection to Cosmos DB
            await cosmos_client.ensure_connected()

            # Query for POIs
            query = "SELECT * FROM c"
            if category:
                query += f" WHERE c.category = '{category}'"

            # Get POIs from container
            pois_container = cosmos_client.pois_container
            if not pois_container:
                logger.warning("POIs container not available")
                return self._format_response(
                    "Points of interest data is currently unavailable.", success=False
                )

            items = pois_container.query_items(
                query=query, enable_cross_partition_query=True
            )

            pois = []
            async for item in items:
                # Calculate distance (simplified for demo) - in a real app, use a proper distance calculation
                poi_location = item.get("location", {})
                poi_lat = poi_location.get("latitude", 0)
                poi_lon = poi_location.get("longitude", 0)
                vehicle_lat = location.get("latitude", 0)
                vehicle_lon = location.get("longitude", 0)

                # Simple Euclidean distance (not accurate for geo, but ok for demo)
                distance = (
                    (poi_lat - vehicle_lat) ** 2 + (poi_lon - vehicle_lon) ** 2
                ) ** 0.5 * 111  # rough km conversion

                pois.append(
                    {
                        "name": item.get("name", "Unknown"),
                        "category": item.get("category", "Other"),
                        "rating": item.get("rating", 0),
                        "distance_km": round(distance, 1),
                        "location": poi_location,
                        "address": item.get("address", "No address available"),
                        "features": item.get("features", {}),
                    }
                )

            # Sort by distance
            pois.sort(key=lambda p: p["distance_km"])

            # Take closest 5
            pois = pois[:5]

            # Format the response
            if not pois:
                return self._format_response(
                    f"I couldn't find any points of interest{' in the ' + category + ' category' if category else ''} near you.",
                    success=False,
                )

            pois_text = "\n".join(
                [
                    f"• {poi['name']} ({poi['category']}) - {poi['distance_km']} km away, {poi['rating']}/5 rating"
                    for poi in pois
                ]
            )

            return self._format_response(
                f"Here are points of interest near you:\n\n{pois_text}",
                data={"pois": pois, "vehicle_id": vehicle_id},
            )
        except Exception as e:
            logger.error(f"Error retrieving points of interest: {str(e)}")
            return self._format_response(
                "I encountered an error while retrieving points of interest. Please try again later.",
                success=False,
            )

    @kernel_function(description="Handle navigation requests")
    async def _handle_navigation(
        self,
        vehicle_id: Optional[str],
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle a navigation request."""
        try:
            # Try to extract destination from query
            destination = None
            query_lower = query.lower()

            if "to " in query_lower:
                parts = query_lower.split("to ")
                if len(parts) > 1:
                    destination = parts[1].strip()

            if not destination and context and "destination" in context:
                destination = context["destination"]

            if not destination:
                return self._format_response(
                    "Where would you like to navigate to? Please specify a destination.",
                    success=False,
                )

            # Get vehicle location from Cosmos DB
            location = await self._get_vehicle_location(vehicle_id)

            if not location:
                return self._format_response(
                    "I couldn't determine your vehicle's location to plan navigation.",
                    success=False,
                )

            # In a production environment, we would call a navigation/routing API
            # For demonstration, we'll create a simulated navigation response

            # Generate distance based on destination length (just for demo purposes)
            distance = len(destination) * 1.5
            duration = int(distance * 2)  # ~30 km/h average speed

            navigation_data = {
                "destination": destination.title(),
                "start_location": location,
                "estimated_time": duration,
                "distance_km": round(distance, 1),
                "route_overview": "via main roads",
                "next_turn": f"Continue straight for {int(distance/3)} km",
                "timestamp": datetime.now().isoformat(),
            }

            # Create a command in Cosmos DB for the navigation
            command = {
                "id": str(
                    context.get("session_id", "nav-" + datetime.now().isoformat())
                ),
                "commandId": f"nav-{hash(destination) % 10000:04d}",
                "vehicleId": vehicle_id,
                "commandType": "SET_NAVIGATION",
                "parameters": {
                    "destination": destination,
                    "distance_km": navigation_data["distance_km"],
                    "estimated_time": navigation_data["estimated_time"],
                },
                "status": "Sent",
                "timestamp": datetime.now().isoformat(),
            }

            try:
                await cosmos_client.create_command(command)
            except Exception as e:
                logger.warning(f"Could not save navigation command: {e}")

            return self._format_response(
                f"I've set up navigation to {navigation_data['destination']}. "
                f"It's {navigation_data['distance_km']} km away and should take about {navigation_data['estimated_time']} minutes "
                f"{navigation_data['route_overview']}. {navigation_data['next_turn']}.",
                data={"navigation": navigation_data, "vehicle_id": vehicle_id},
            )
        except Exception as e:
            logger.error(f"Error setting up navigation: {str(e)}")
            return self._format_response(
                "I encountered an error while setting up navigation. Please try again later.",
                success=False,
            )

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
            logger.error(f"Error getting vehicle location: {str(e)}")
            return {}

    async def _get_vehicle_status(self, vehicle_id: Optional[str]) -> Dict[str, Any]:
        """Get the vehicle's current status from Cosmos DB."""
        if not vehicle_id:
            return {}

        try:
            return await cosmos_client.get_vehicle_status(vehicle_id)
        except Exception as e:
            logger.error(f"Error getting vehicle status: {str(e)}")
            return {}

    async def process(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process an information services related query.

        Args:
            query: User query about information services
            context: Additional context for the query

        Returns:
            Response with information services data
        """
        # Extract vehicle ID from context if available
        vehicle_id = context.get("vehicle_id") if context else None

        # Simple keyword-based logic for demonstration
        query_lower = query.lower()

        # Handle weather requests
        if "weather" in query_lower:
            return await self._handle_weather(vehicle_id, context)

        # Handle traffic requests
        elif "traffic" in query_lower:
            return await self._handle_traffic(vehicle_id, context)

        # Handle points of interest requests
        elif (
            "poi" in query_lower
            or "point of interest" in query_lower
            or "places" in query_lower
        ):
            return await self._handle_pois(vehicle_id, context)

        # Handle navigation requests
        elif (
            "navigation" in query_lower
            or "directions" in query_lower
            or "route" in query_lower
        ):
            return await self._handle_navigation(vehicle_id, query, context)

        # Handle general information requests
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
