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
from agents.base.base_agent import BasePlugin

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


class InformationServicesPlugin(BasePlugin):
    """Plugin for information services operations."""

    @kernel_function(description="Handle weather information requests")
    async def _handle_weather(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle weather information requests."""
        try:
            location = await self._get_vehicle_location(vehicle_id)
            
            # Simulated weather data (in production, would call weather API)
            weather_data = {
                "temperature": 22,
                "condition": "Partly Cloudy",
                "humidity": 65,
                "wind_speed": 12,
                "forecast": ["Sunny", "Cloudy", "Rain"],
                "location": location or {"latitude": 0, "longitude": 0},
            }

            return self._format_response(
                f"Current weather: {weather_data['condition']}, {weather_data['temperature']}°C. "
                f"Humidity: {weather_data['humidity']}%, Wind: {weather_data['wind_speed']} km/h. "
                f"Forecast: {', '.join(weather_data['forecast'])}",
                data={"weather": weather_data, "vehicle_id": vehicle_id},
            )

        except Exception as e:
            logger.error(f"Error getting weather information: {e}")
            return self._format_response(
                "I'm having trouble getting weather information right now. Please try again later.",
                success=False,
            )

    @kernel_function(description="Handle traffic information requests")
    async def _handle_traffic(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle traffic information requests."""
        try:
            location = await self._get_vehicle_location(vehicle_id)
            
            # Simulated traffic data
            traffic_data = {
                "overall_condition": "Moderate",
                "incidents": [
                    {"type": "Construction", "location": "Highway 401", "delay": "15 min"},
                    {"type": "Accident", "location": "Main St", "delay": "5 min"},
                ],
                "suggested_routes": ["Route A (fastest)", "Route B (scenic)"],
                "location": location or {"latitude": 0, "longitude": 0},
            }

            incidents_text = "\n".join([
                f"• {incident['type']} on {incident['location']} - {incident['delay']} delay"
                for incident in traffic_data['incidents']
            ])

            return self._format_response(
                f"Traffic condition: {traffic_data['overall_condition']}\n\n"
                f"Current incidents:\n{incidents_text}\n\n"
                f"Suggested routes: {', '.join(traffic_data['suggested_routes'])}",
                data={"traffic": traffic_data, "vehicle_id": vehicle_id},
            )

        except Exception as e:
            logger.error(f"Error getting traffic information: {e}")
            return self._format_response(
                "I'm having trouble getting traffic information right now. Please try again later.",
                success=False,
            )

    @kernel_function(description="Handle points of interest requests")
    async def _handle_pois(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle points of interest requests."""
        try:
            location = await self._get_vehicle_location(vehicle_id)
            
            # Simulated POI data
            pois = [
                {"name": "Downtown Mall", "type": "Shopping", "distance": "2.5 km"},
                {"name": "City Hospital", "type": "Medical", "distance": "1.8 km"},
                {"name": "Riverside Park", "type": "Recreation", "distance": "3.2 km"},
                {"name": "Gas Station", "type": "Fuel", "distance": "0.8 km"},
            ]

            pois_text = "\n".join([
                f"• {poi['name']} ({poi['type']}) - {poi['distance']} away"
                for poi in pois
            ])

            return self._format_response(
                f"Nearby points of interest:\n\n{pois_text}",
                data={"pois": pois, "vehicle_id": vehicle_id, "location": location},
            )

        except Exception as e:
            logger.error(f"Error getting points of interest: {e}")
            return self._format_response(
                "I'm having trouble finding nearby points of interest. Please try again later.",
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
            # Extract destination from query
            destination = "destination"
            if "to " in query.lower():
                destination = query.lower().split("to ")[-1].strip()
            
            # Get vehicle location from Cosmos DB
            location = await self._get_vehicle_location(vehicle_id)

            if not location:
                return self._format_response(
                    "I couldn't determine your vehicle's location for navigation.",
                    success=False,
                )

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
                "timestamp": datetime.datetime.now().isoformat(),
            }

            # Create a command in Cosmos DB for the navigation
            command = {
                "id": str(uuid.uuid4()),
                "commandId": f"nav-{hash(destination) % 10000:04d}",
                "vehicleId": vehicle_id,
                "commandType": "SET_NAVIGATION",
                "parameters": {
                    "destination": destination,
                    "distance_km": navigation_data["distance_km"],
                    "estimated_time": navigation_data["estimated_time"],
                },
                "status": "Sent",
                "timestamp": datetime.datetime.now().isoformat(),
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
            logger.error(f"Error setting up navigation: {e}")
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
