"""
Charging & Energy Agent for the Connected Car Platform.

This agent manages electric vehicle charging operations, energy usage tracking,
and charging station information.
"""

import logging
import datetime
import uuid
from typing import Dict, Any, Optional, List

from agents.base_agent import BaseAgent
from azure.cosmos_db import cosmos_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChargingEnergyAgent(BaseAgent):
    """
    Charging & Energy Agent for electric vehicle charging operations.
    """
    
    def __init__(self):
        """Initialize the Charging & Energy Agent."""
        super().__init__("Charging & Energy Agent")
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a charging or energy related query.
        
        Args:
            query: User query about charging or energy features
            context: Additional context for the query
            
        Returns:
            Response with charging or energy information or actions
        """
        # Extract vehicle ID from context if available
        vehicle_id = context.get("vehicle_id") if context else None
        
        # Simple keyword-based logic for demonstration
        query_lower = query.lower()
        
        # Handle charging station requests
        if "station" in query_lower or "charging station" in query_lower:
            return await self._handle_charging_stations(vehicle_id, context)
        
        # Handle charging status requests
        elif "status" in query_lower and ("charging" in query_lower or "battery" in query_lower):
            return await self._handle_charging_status(vehicle_id, context)
        
        # Handle start charging requests
        elif "start" in query_lower and "charging" in query_lower:
            return await self._handle_start_charging(vehicle_id, context)
        
        # Handle stop charging requests
        elif "stop" in query_lower and "charging" in query_lower:
            return await self._handle_stop_charging(vehicle_id, context)
            
        # Handle energy usage requests
        elif "energy" in query_lower and "usage" in query_lower:
            return await self._handle_energy_usage(vehicle_id, context)
            
        # Handle range estimation requests
        elif "range" in query_lower or "how far" in query_lower:
            return await self._handle_range_estimation(vehicle_id, context)
            
        # Handle general information requests
        else:
            return self._format_response(
                "I can help you with electric vehicle charging and energy management, "
                "including finding charging stations, monitoring charging status, "
                "starting/stopping charging, tracking energy usage, and estimating range. "
                "What would you like to do?",
                data=self._get_capabilities()
            )
    
    async def _handle_charging_stations(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a request for nearby charging stations."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you're using to search for charging stations.", 
                success=False
            )
        
        try:
            # Get vehicle location from Cosmos DB
            location = await self._get_vehicle_location(vehicle_id)
            
            if not location:
                return self._format_response(
                    "I couldn't determine your vehicle's location to find nearby charging stations.",
                    success=False
                )
            
            # Ensure Cosmos DB connection
            await cosmos_client.ensure_connected()
            
            # Look for charging stations in Cosmos DB
            charging_stations_container = cosmos_client.charging_stations_container
            if not charging_stations_container:
                logger.warning("Charging stations container not available")
                return self._format_response(
                    "Charging station data is currently unavailable.",
                    success=False
                )
                
            # Query for all stations (in a real app, would be geo-filtered)
            query = "SELECT * FROM c"
            items = charging_stations_container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
            
            # Process results
            nearby_stations = []
            async for item in items:
                # Calculate distance (simplified for demo) - in a real app, use a proper distance calculation
                station_location = item.get("location", {})
                station_lat = station_location.get("latitude", 0)
                station_lon = station_location.get("longitude", 0)
                vehicle_lat = location.get("latitude", 0)
                vehicle_lon = location.get("longitude", 0)
                
                # Simple Euclidean distance (not accurate for geo, but ok for demo)
                distance = ((station_lat - vehicle_lat)**2 + (station_lon - vehicle_lon)**2)**0.5 * 111  # rough km conversion
                
                if distance < 10:  # Only include stations within ~10km
                    nearby_stations.append({
                        "name": item.get("name", "Unknown Station"),
                        "power_level": item.get("power_level", "Unknown"),
                        "distance_km": round(distance, 1),
                        "available": item.get("available_ports", 0) > 0,
                        "provider": item.get("provider", "Unknown Network"),
                        "cost_per_kwh": item.get("cost_per_kwh", 0.0),
                        "connector_types": item.get("connector_types", []),
                        "is_operational": item.get("is_operational", True)
                    })
            
            # Sort by distance
            nearby_stations.sort(key=lambda s: s["distance_km"])
            
            if not nearby_stations:
                return self._format_response(
                    "I couldn't find any charging stations near your current location.",
                    success=False
                )
            
            # Format the response
            stations_text = "\n".join([
                f"• {station['name']} - {station['distance_km']} km away, "
                f"{station['power_level']}, {'Available' if station['available'] else 'Occupied'}"
                for station in nearby_stations
            ])
            
            return self._format_response(
                f"I found {len(nearby_stations)} charging stations near you:\n\n{stations_text}",
                data={
                    "stations": nearby_stations,
                    "vehicle_id": vehicle_id
                }
            )
        except Exception as e:
            logger.error(f"Error retrieving charging stations: {str(e)}")
            return self._format_response(
                "I encountered an error while retrieving charging stations. Please try again later.",
                success=False
            )
    
    async def _handle_charging_status(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a charging status request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to check the charging status for.", 
                success=False
            )
        
        try:
            # Get vehicle status from Cosmos DB
            vehicle_status = await cosmos_client.get_vehicle_status(vehicle_id)
            
            if not vehicle_status:
                return self._format_response(
                    "I couldn't retrieve the charging status for your vehicle.",
                    success=False
                )
            
            # Extract battery and engine status
            battery_level = vehicle_status.get("Battery", 0)
            engine_status = vehicle_status.get("EngineStatus", "off")
            
            # Get vehicle details to check if it's electric
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next((v for v in vehicles if v.get("VehicleId") == vehicle_id), None)
            
            if not vehicle:
                return self._format_response(
                    "I couldn't find details for your vehicle.",
                    success=False
                )
                
            is_electric = vehicle.get("Features", {}).get("IsElectric", False)
            
            if not is_electric:
                return self._format_response(
                    "This vehicle doesn't appear to be an electric vehicle. Charging status is not applicable.",
                    success=False
                )
            
            # Determine if the vehicle is charging based on available data
            # In a real implementation, there would be a dedicated charging status field
            is_charging = engine_status == "off" and \
                          battery_level > vehicle.get("BatteryLevel", battery_level)
            
            charging_status = {
                "is_charging": is_charging,
                "battery_level": battery_level,
                "time_remaining": 60 if is_charging else None,  # Estimated
                "charging_power": 7.2 if is_charging else None  # Default value
            }
            
            if charging_status["is_charging"]:
                response_text = (
                    f"Your vehicle is currently charging. The battery level is {charging_status['battery_level']}%. "
                    f"Estimated time to full charge: {charging_status['time_remaining']} minutes. "
                    f"Current charging power: {charging_status['charging_power']} kW."
                )
            else:
                response_text = (
                    f"Your vehicle is not currently charging. The battery level is {charging_status['battery_level']}%."
                )
            
            return self._format_response(
                response_text,
                data={
                    "charging_status": charging_status,
                    "vehicle_id": vehicle_id
                }
            )
        except Exception as e:
            logger.error(f"Error retrieving charging status: {str(e)}")
            return self._format_response(
                "I encountered an error while retrieving the charging status. Please try again later.",
                success=False
            )
    
    async def _handle_start_charging(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a start charging request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to start charging.", 
                success=False
            )
        
        try:
            # Get vehicle status
            vehicle_status = await cosmos_client.get_vehicle_status(vehicle_id)
            
            # Get vehicle details to check if it's electric
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next((v for v in vehicles if v.get("VehicleId") == vehicle_id), None)
            
            if not vehicle:
                return self._format_response(
                    "I couldn't find details for your vehicle.",
                    success=False
                )
                
            is_electric = vehicle.get("Features", {}).get("IsElectric", False)
            
            if not is_electric:
                return self._format_response(
                    "This vehicle doesn't appear to be an electric vehicle. Charging is not applicable.",
                    success=False
                )
            
            battery_level = vehicle_status.get("Battery", 0) if vehicle_status else vehicle.get("BatteryLevel", 0)
            
            # Create charging command in Cosmos DB
            command = {
                "id": str(uuid.uuid4()),
                "commandId": f"charge-{str(uuid.uuid4())[:8]}",
                "vehicleId": vehicle_id,
                "commandType": "START_CHARGING",
                "parameters": {},
                "status": "pending",
                "timestamp": datetime.datetime.now().isoformat(),
                "priority": "Normal"
            }
            
            # Store in Cosmos DB
            result = await cosmos_client.create_command(command)
            
            if result:
                return self._format_response(
                    f"I've started charging your vehicle. The current battery level is "
                    f"{battery_level}% and the estimated time to full charge is "
                    f"about {(100 - battery_level) * 2} minutes at a standard charging rate.",
                    data={
                        "action": "start_charging",
                        "vehicle_id": vehicle_id,
                        "status": "success",
                        "command_id": command["commandId"]
                    }
                )
            else:
                return self._format_response(
                    "I couldn't start charging your vehicle. The command was not processed.",
                    success=False,
                    data={
                        "action": "start_charging",
                        "vehicle_id": vehicle_id,
                        "status": "failed",
                        "error": "Command processing failed"
                    }
                )
        except Exception as e:
            logger.error(f"Error starting charging: {str(e)}")
            return self._format_response(
                "I encountered an error while trying to start charging. Please try again later.",
                success=False
            )
    
    async def _handle_stop_charging(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a stop charging request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to stop charging.", 
                success=False
            )
        
        try:
            # Get vehicle status
            vehicle_status = await cosmos_client.get_vehicle_status(vehicle_id)
            
            # Get vehicle details to check if it's electric
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next((v for v in vehicles if v.get("VehicleId") == vehicle_id), None)
            
            if not vehicle:
                return self._format_response(
                    "I couldn't find details for your vehicle.",
                    success=False
                )
                
            is_electric = vehicle.get("Features", {}).get("IsElectric", False)
            
            if not is_electric:
                return self._format_response(
                    "This vehicle doesn't appear to be an electric vehicle. Charging control is not applicable.",
                    success=False
                )
            
            battery_level = vehicle_status.get("Battery", 0) if vehicle_status else vehicle.get("BatteryLevel", 0)
            
            # Create stop charging command in Cosmos DB
            command = {
                "id": str(uuid.uuid4()),
                "commandId": f"stop-charge-{str(uuid.uuid4())[:8]}",
                "vehicleId": vehicle_id,
                "commandType": "STOP_CHARGING",
                "parameters": {},
                "status": "pending",
                "timestamp": datetime.datetime.now().isoformat(),
                "priority": "Normal"
            }
            
            # Store in Cosmos DB
            result = await cosmos_client.create_command(command)
            
            if result:
                return self._format_response(
                    f"I've stopped charging your vehicle. The final battery level is "
                    f"{battery_level}%.",
                    data={
                        "action": "stop_charging",
                        "vehicle_id": vehicle_id,
                        "status": "success",
                        "command_id": command["commandId"]
                    }
                )
            else:
                return self._format_response(
                    "I couldn't stop charging your vehicle. The command was not processed.",
                    success=False,
                    data={
                        "action": "stop_charging",
                        "vehicle_id": vehicle_id,
                        "status": "failed",
                        "error": "Command processing failed"
                    }
                )
        except Exception as e:
            logger.error(f"Error stopping charging: {str(e)}")
            return self._format_response(
                "I encountered an error while trying to stop charging. Please try again later.",
                success=False
            )
    
    async def _handle_energy_usage(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle an energy usage request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to check energy usage for.", 
                success=False
            )
        
        try:
            # Get vehicle status history to calculate energy usage
            # In a production system, this would come from a specific energy usage tracking system
            
            # Get vehicle details to check if it's electric
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next((v for v in vehicles if v.get("VehicleId") == vehicle_id), None)
            
            if not vehicle:
                return self._format_response(
                    "I couldn't find details for your vehicle.",
                    success=False
                )
                
            is_electric = vehicle.get("Features", {}).get("IsElectric", False)
            
            if not is_electric:
                return self._format_response(
                    "This vehicle doesn't appear to be an electric vehicle. Energy usage metrics are not applicable.",
                    success=False
                )
            
            # Get status history
            status_container = cosmos_client.status_container
            
            # Query for recent status entries of this vehicle
            query = "SELECT * FROM c WHERE c.vehicleId = @vehicleId ORDER BY c._ts DESC OFFSET 0 LIMIT 20"
            parameters = [{"name": "@vehicleId", "value": vehicle_id}]
            
            items = status_container.query_items(
                query=query,
                parameters=parameters
            )
            
            # Process status history to calculate energy metrics
            statuses = []
            async for item in items:
                statuses.append(item)
                
            # Calculate metrics based on available data
            # This is a simplified calculation for demonstration
            battery_levels = [s.get("batteryLevel", 0) for s in statuses if "batteryLevel" in s]
            
            if not battery_levels:
                # No battery level data, provide default/estimated values
                energy_usage = {
                    "total_kWh": 18.5,  # Default estimate
                    "avg_efficiency": 16.7,
                    "regenerative_braking": 2.3,
                    "cost_estimate": 4.62
                }
            else:
                # Calculate rough energy usage from battery levels
                # This is simplified; a real implementation would use actual energy measurements
                battery_capacity_kwh = 75.0  # Assume a 75 kWh battery
                
                # If we have multiple readings, look at the changes
                if len(battery_levels) > 1:
                    # Calculate battery percentage used
                    battery_diff = sum([max(0, battery_levels[i] - battery_levels[i+1]) 
                                       for i in range(len(battery_levels)-1)])
                    
                    total_kwh = (battery_diff / 100) * battery_capacity_kwh
                    
                    # Calculate efficiency (kWh/100km) based on mileage if available
                    mileage_readings = [s.get("mileage", 0) for s in statuses if "mileage" in s]
                    
                    if len(mileage_readings) > 1:
                        distance = abs(mileage_readings[0] - mileage_readings[-1])
                        avg_efficiency = (total_kwh / max(1, distance)) * 100
                    else:
                        avg_efficiency = 16.7  # Default efficiency
                        
                    # Estimate regenerative braking (usually ~10-15% of total energy)
                    regen_kwh = total_kwh * 0.12
                    
                    energy_usage = {
                        "total_kWh": round(total_kwh, 1),
                        "avg_efficiency": round(avg_efficiency, 1),
                        "regenerative_braking": round(regen_kwh, 1),
                        "cost_estimate": round(total_kwh * 0.25, 2)  # Assuming $0.25/kWh
                    }
                else:
                    # Not enough data for calculation, use defaults
                    energy_usage = {
                        "total_kWh": 18.5,
                        "avg_efficiency": 16.7,
                        "regenerative_braking": 2.3,
                        "cost_estimate": 4.62
                    }
            
            return self._format_response(
                f"Here's your energy usage summary:\n\n"
                f"• Total energy used: {energy_usage['total_kWh']} kWh\n"
                f"• Average efficiency: {energy_usage['avg_efficiency']} kWh/100 km\n"
                f"• Energy recovered from regenerative braking: {energy_usage['regenerative_braking']} kWh\n"
                f"• Estimated cost: ${energy_usage['cost_estimate']}",
                data={
                    "energy_usage": energy_usage,
                    "vehicle_id": vehicle_id
                }
            )
        except Exception as e:
            logger.error(f"Error retrieving energy usage: {str(e)}")
            return self._format_response(
                "I encountered an error while retrieving energy usage data. Please try again later.",
                success=False
            )
    
    async def _handle_range_estimation(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a range estimation request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to estimate range for.", 
                success=False
            )
        
        try:
            # Get vehicle status
            vehicle_status = await cosmos_client.get_vehicle_status(vehicle_id)
            
            # Get vehicle details
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next((v for v in vehicles if v.get("VehicleId") == vehicle_id), None)
            
            if not vehicle:
                return self._format_response(
                    "I couldn't find details for your vehicle.",
                    success=False
                )
                
            is_electric = vehicle.get("Features", {}).get("IsElectric", False)
            
            if not is_electric:
                return self._format_response(
                    "This vehicle doesn't appear to be an electric vehicle. Range estimation is not applicable.",
                    success=False
                )
            
            battery_level = vehicle_status.get("Battery", 0) if vehicle_status else vehicle.get("BatteryLevel", 0)
            
            # Calculate range based on battery level and vehicle model
            # In a real system, this would use the specific vehicle's efficiency data
            
            # Get vehicle brand and model
            brand = vehicle.get("Brand", "")
            model = vehicle.get("VehicleModel", "")
            
            # Different range estimations based on vehicle type
            base_range = 450  # Default max range in km
            
            # Adjust for specific models (very simplified)
            if brand == "Tesla":
                if "Model S" in model or "Model X" in model:
                    base_range = 560
                else:
                    base_range = 510
            elif "e-tron" in model or "Taycan" in model:
                base_range = 400
            elif "Bolt" in model or "Mach-E" in model:
                base_range = 380
                
            # Calculate range based on battery level
            estimated_range_km = int(base_range * (battery_level / 100))
            
            # Eco mode typically gives ~10-15% more range
            estimated_range_eco_km = int(estimated_range_km * 1.12)
            
            # Get nearest charging station distance
            nearest_station_km = await self._get_nearest_charging_station_distance(vehicle_id)
            
            range_data = {
                "battery_level": battery_level,
                "estimated_range_km": estimated_range_km,
                "estimated_range_eco_km": estimated_range_eco_km,
                "nearest_station_km": nearest_station_km if nearest_station_km else "Unknown"
            }
            
            return self._format_response(
                f"Based on your current battery level of {range_data['battery_level']}%, "
                f"your estimated range is {range_data['estimated_range_km']} km. "
                f"In eco mode, you could potentially reach {range_data['estimated_range_eco_km']} km. "
                f"The nearest charging station is {range_data['nearest_station_km']} km away.",
                data={
                    "range_data": range_data,
                    "vehicle_id": vehicle_id
                }
            )
        except Exception as e:
            logger.error(f"Error estimating range: {str(e)}")
            return self._format_response(
                "I encountered an error while estimating your vehicle's range. Please try again later.",
                success=False
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
            vehicle = next((v for v in vehicles if v.get("VehicleId") == vehicle_id), None)
            
            if vehicle and "LastLocation" in vehicle:
                # Convert to lowercase keys for consistency
                return {
                    "latitude": vehicle["LastLocation"].get("Latitude", 0),
                    "longitude": vehicle["LastLocation"].get("Longitude", 0)
                }
                
            return {}
        except Exception as e:
            logger.error(f"Error getting vehicle location: {str(e)}")
            return {}
            
    async def _get_nearest_charging_station_distance(self, vehicle_id: Optional[str]) -> Optional[float]:
        """Get the distance to the nearest charging station."""
        try:
            # Get vehicle location
            location = await self._get_vehicle_location(vehicle_id)
            
            if not location:
                return None
                
            # Query charging stations
            charging_stations_container = cosmos_client.charging_stations_container
            if not charging_stations_container:
                return None
                
            query = "SELECT * FROM c"
            items = charging_stations_container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
            
            # Find nearest station
            nearest_distance = None
            async for item in items:
                station_location = item.get("location", {})
                station_lat = station_location.get("latitude", 0)
                station_lon = station_location.get("longitude", 0)
                vehicle_lat = location.get("latitude", 0)
                vehicle_lon = location.get("longitude", 0)
                
                # Simple Euclidean distance (not accurate for geo, but ok for demo)
                distance = ((station_lat - vehicle_lat)**2 + (station_lon - vehicle_lon)**2)**0.5 * 111
                
                if nearest_distance is None or distance < nearest_distance:
                    nearest_distance = distance
                    
            return round(nearest_distance, 1) if nearest_distance is not None else None
        except Exception as e:
            logger.error(f"Error finding nearest charging station: {str(e)}")
            return None
    
    def _get_capabilities(self) -> Dict[str, str]:
        """Get the capabilities of this agent."""
        return {
            "charging_stations": "Find and navigate to nearby charging stations",
            "charging_status": "Check the current charging status and battery level",
            "charging_control": "Start or stop vehicle charging",
            "energy_usage": "Track and analyze energy consumption",
            "range_estimation": "Estimate remaining driving range"
        }
