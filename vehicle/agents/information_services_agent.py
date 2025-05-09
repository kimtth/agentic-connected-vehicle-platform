"""
Information Services Agent for the Connected Car Platform.

This agent provides real-time vehicle-related information such as weather, traffic,
and points of interest.
"""

import logging
import random
from typing import Dict, Any, Optional, List

from agents.base_agent import BaseAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InformationServicesAgent(BaseAgent):
    """
    Information Services Agent for providing real-time vehicle information.
    """
    
    def __init__(self):
        """Initialize the Information Services Agent."""
        super().__init__("Information Services Agent")
        
        # Mock data for demonstration
        self.mock_pois = [
            {"id": "poi001", "name": "Central Park", "category": "Park", "rating": 4.7, "distance_km": 1.2},
            {"id": "poi002", "name": "Downtown Cafe", "category": "Restaurant", "rating": 4.2, "distance_km": 0.8},
            {"id": "poi003", "name": "City Museum", "category": "Museum", "rating": 4.5, "distance_km": 3.5},
            {"id": "poi004", "name": "Shopping Mall", "category": "Shopping", "rating": 4.0, "distance_km": 2.7},
            {"id": "poi005", "name": "Community Theater", "category": "Entertainment", "rating": 4.3, "distance_km": 1.9},
        ]
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
        elif "poi" in query_lower or "point of interest" in query_lower or "places" in query_lower:
            return await self._handle_pois(vehicle_id, context)
            
        # Handle navigation requests
        elif "navigation" in query_lower or "directions" in query_lower or "route" in query_lower:
            return await self._handle_navigation(vehicle_id, query, context)
            
        # Handle general information requests
        else:
            return self._format_response(
                "I can provide you with real-time information related to your vehicle and journey, "
                "including weather updates, traffic conditions, points of interest, and navigation assistance. "
                "What kind of information would you like?",
                data=self._get_capabilities()
            )
    
    async def _handle_weather(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a weather information request."""
        # In a real implementation, this would query a weather API using the vehicle's location
        # Mock data for demonstration
        weather_data = {
            "temperature": random.randint(10, 30),
            "condition": random.choice(["Sunny", "Cloudy", "Partly Cloudy", "Rainy", "Snowy"]),
            "humidity": random.randint(30, 90),
            "wind_speed": random.randint(0, 30),
            "forecast": [
                {"day": "Today", "condition": random.choice(["Sunny", "Cloudy", "Partly Cloudy", "Rainy", "Snowy"]), "high": random.randint(10, 30), "low": random.randint(0, 20)},
                {"day": "Tomorrow", "condition": random.choice(["Sunny", "Cloudy", "Partly Cloudy", "Rainy", "Snowy"]), "high": random.randint(10, 30), "low": random.randint(0, 20)},
                {"day": "Day After", "condition": random.choice(["Sunny", "Cloudy", "Partly Cloudy", "Rainy", "Snowy"]), "high": random.randint(10, 30), "low": random.randint(0, 20)}
            ]
        }
        
        return self._format_response(
            f"Current weather: {weather_data['condition']}, {weather_data['temperature']}°C with "
            f"{weather_data['humidity']}% humidity and wind at {weather_data['wind_speed']} km/h. "
            f"\n\nForecast:\n"
            f"• {weather_data['forecast'][0]['day']}: {weather_data['forecast'][0]['condition']}, {weather_data['forecast'][0]['high']}°C / {weather_data['forecast'][0]['low']}°C\n"
            f"• {weather_data['forecast'][1]['day']}: {weather_data['forecast'][1]['condition']}, {weather_data['forecast'][1]['high']}°C / {weather_data['forecast'][1]['low']}°C\n"
            f"• {weather_data['forecast'][2]['day']}: {weather_data['forecast'][2]['condition']}, {weather_data['forecast'][2]['high']}°C / {weather_data['forecast'][2]['low']}°C",
            data={
                "weather": weather_data,
                "vehicle_id": vehicle_id
            }
        )
    
    async def _handle_traffic(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a traffic information request."""
        # In a real implementation, this would query a traffic API using the vehicle's location
        # Mock data for demonstration
        traffic_data = {
            "current_speed": random.randint(10, 100),
            "normal_speed": random.randint(50, 110),
            "congestion_level": random.choice(["Low", "Moderate", "High", "Severe"]),
            "incidents": [
                {"type": "Accident", "location": "Highway 101, Mile 23", "delay_minutes": random.randint(5, 30)} if random.random() > 0.7 else None,
                {"type": "Construction", "location": "Main Street", "delay_minutes": random.randint(5, 20)} if random.random() > 0.7 else None,
                {"type": "Road Closure", "location": "Downtown Bridge", "delay_minutes": random.randint(10, 45)} if random.random() > 0.7 else None
            ]
        }
        
        # Clean up None values
        traffic_data["incidents"] = [i for i in traffic_data["incidents"] if i]
        
        # Build the response
        incidents_text = ""
        if traffic_data["incidents"]:
            incidents_text = "\n\nTraffic incidents:\n" + "\n".join([
                f"• {incident['type']} at {incident['location']}: {incident['delay_minutes']} min delay"
                for incident in traffic_data["incidents"]
            ])
        
        return self._format_response(
            f"Current traffic conditions: {traffic_data['congestion_level']} congestion. "
            f"Traffic is moving at {traffic_data['current_speed']} km/h "
            f"(normal speed: {traffic_data['normal_speed']} km/h).{incidents_text}",
            data={
                "traffic": traffic_data,
                "vehicle_id": vehicle_id
            }
        )
    
    async def _handle_pois(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a points of interest request."""
        # In a real implementation, this would query a POI API using the vehicle's location
        # Mock data for demonstration
        category = context.get("poi_category") if context else None
        
        if category:
            pois = [poi for poi in self.mock_pois if poi["category"].lower() == category.lower()]
        else:
            pois = self.mock_pois
        
        # Sort by distance
        pois.sort(key=lambda p: p["distance_km"])
        
        # Format the response
        if not pois:
            return self._format_response(
                f"I couldn't find any points of interest{' in the ' + category + ' category' if category else ''} near you.",
                success=False
            )
        
        pois_text = "\n".join([
            f"• {poi['name']} ({poi['category']}) - {poi['distance_km']} km away, {poi['rating']}/5 rating"
            for poi in pois
        ])
        
        return self._format_response(
            f"Here are points of interest near you:\n\n{pois_text}",
            data={
                "pois": pois,
                "vehicle_id": vehicle_id
            }
        )
    
    async def _handle_navigation(self, vehicle_id: Optional[str], query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a navigation request."""
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
                success=False
            )
        
        # In a real implementation, this would query a navigation API with the destination
        # Mock data for demonstration
        navigation_data = {
            "destination": destination.title(),
            "estimated_time": random.randint(5, 60),
            "distance_km": round(random.uniform(1, 50), 1),
            "route_overview": "via Highway 101 and Main Street",
            "next_turn": f"Turn right on {random.choice(['Main Street', 'First Avenue', 'Park Road'])} in {random.randint(1, 10)} km"
        }
        
        return self._format_response(
            f"I've set up navigation to {navigation_data['destination']}. "
            f"It's {navigation_data['distance_km']} km away and should take about {navigation_data['estimated_time']} minutes "
            f"{navigation_data['route_overview']}. {navigation_data['next_turn']}.",
            data={
                "navigation": navigation_data,
                "vehicle_id": vehicle_id
            }
        )
    
    def _get_capabilities(self) -> Dict[str, str]:
        """Get the capabilities of this agent."""
        return {
            "weather": "Get current weather and forecast information",
            "traffic": "Check traffic conditions and incidents",
            "points_of_interest": "Find nearby points of interest",
            "navigation": "Set up and manage navigation to destinations"
        }
