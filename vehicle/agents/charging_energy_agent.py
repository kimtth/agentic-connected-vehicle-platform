import datetime
import uuid
from typing import Dict, Any, Optional, Annotated
import json

from azure.cosmos_db import get_cosmos_client
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from plugin.oai_service import create_chat_service
from utils.logging_config import get_logger
from utils.agent_context import extract_vehicle_id
from utils.vehicle_object_utils import find_vehicle, ensure_dict
import random
from models.command import Command  # NEW: model for command persistence

logger = get_logger(__name__)


class ChargingEnergyAgent:
    """
    Charging & Energy Agent for the Connected Car Platform.
    """

    def __init__(self):
        """Initialize the Charging & Energy Agent."""
        self.cosmos_client = get_cosmos_client()
        service_factory = create_chat_service()
        self.agent = ChatCompletionAgent(
            service=service_factory,
            name="ChargingEnergyAgent",
            instructions=(
                "You specialize in managing vehicle charging and energy consumption. "
                "IMPORTANT: Return the EXACT JSON response from your plugin functions without modification."
            ),
            plugins=[ChargingEnergyPlugin()],
        )


class ChargingEnergyPlugin:
    def __init__(self):
        # Get the singleton cosmos client instance
        self.cosmos_client = get_cosmos_client()

    async def _apply_status_update(self, vehicle_id: str, patch: Dict[str, Any]):
        """Merge patch into vehicle status and persist."""
        try:
            current = await self.cosmos_client.get_vehicle_status(vehicle_id) or {}
            if isinstance(current, dict):
                current_status = current
            else:
                try:
                    current_status = current.model_dump()
                except Exception:
                    current_status = {}
            current_status.update(patch)
            # Prefer explicit API if available
            if hasattr(self.cosmos_client, "update_vehicle_status"):
                await self.cosmos_client.update_vehicle_status(vehicle_id, current_status)
            elif hasattr(self.cosmos_client, "set_vehicle_status"):
                await self.cosmos_client.set_vehicle_status(vehicle_id, current_status)
            else:
                container = getattr(self.cosmos_client, "status_container", None)
                if container:
                    doc = {"id": vehicle_id, "vehicle_id": vehicle_id, **current_status}
                    await container.upsert_item(doc)
        except Exception as e:
            logger.debug(f"Status update skipped ({vehicle_id}): {e}")

    @kernel_function(description="Find nearby charging stations")
    async def _handle_charging_stations(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID to locate nearby chargers for"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you're using to search for charging stations.",
                success=False,
            )

        try:
            # Get vehicle location from Cosmos DB
            location = await self._get_vehicle_location(vid)

            if not location:
                return self._format_response(
                    "I couldn't determine your vehicle's location to find nearby charging stations.",
                    success=False,
                )

            # Ensure Cosmos DB connection
            await self.cosmos_client.ensure_connected()

            # Look for charging stations in Cosmos DB
            charging_stations_container = self.cosmos_client.charging_stations_container
            if not charging_stations_container:
                logger.warning("Charging stations container not available")
                return self._format_response(
                    "Charging station data is currently unavailable.", success=False
                )

            # Query for all stations (in a real app, would be geo-filtered)
            query = "SELECT * FROM c"
            items = charging_stations_container.query_items(
                query=query, enable_cross_partition_query=True
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
                distance = (
                    (station_lat - vehicle_lat) ** 2 + (station_lon - vehicle_lon) ** 2
                ) ** 0.5 * 111  # rough km conversion

                if distance < 10:  # Only include stations within ~10km
                    nearby_stations.append(
                        {
                            "name": item.get("name", "Unknown Station"),
                            "powerLevel": item.get("powerLevel", "Unknown"),
                            "distanceKm": round(distance, 1),
                            "available": item.get("availablePorts", 0) > 0,
                            "provider": item.get("provider", "Unknown Network"),
                            "costPerKwh": item.get("costPerKwh", 0.0),
                            "connectorTypes": item.get("connectorTypes", []),
                            "isOperational": item.get("isOperational", True),
                        }
                    )

            # Sort by distance (fix key: was distance_km)
            nearby_stations.sort(key=lambda s: s["distanceKm"])

            if not nearby_stations:
                return self._format_response(
                    "I couldn't find any charging stations near your current location.",
                    success=False,
                )

            # Format the response
            stations_text = "\n".join(
                [
                    f"• {station['name']} - {station['distanceKm']} km away, "
                    f"{station['powerLevel']}, {'Available' if station['available'] else 'Occupied'}"
                    for station in nearby_stations
                ]
            )

            return self._format_response(
                f"I found {len(nearby_stations)} charging stations near you:\n\n{stations_text}",
                data={"stations": nearby_stations, "vehicleId": vid},
                function_name="_handle_charging_stations",
            )
        except Exception as e:
            logger.error(f"Error retrieving charging stations: {str(e)}")
            return self._format_response(
                "I encountered an error while retrieving charging stations. Please try again later.",
                success=False,
                function_name="_handle_charging_stations",
            )

    @kernel_function(description="Check charging status and battery")
    async def _handle_charging_status(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID to check charging status for"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to check the charging status for.",
                success=False,
            )

        try:
            # Get vehicle status from Cosmos DB
            vehicle_status = await self.cosmos_client.get_vehicle_status(vid)

            if not vehicle_status:
                return self._format_response(
                    "I couldn't retrieve the charging status for your vehicle.",
                    success=False,
                )

            # Extract battery and engine status
            battery_level = vehicle_status.get("battery", 0)
            engine_status = "on" if int(vehicle_status.get("engineTemp", "")) > 0 else "off"

            # Get vehicle details to check if it's electric
            vehicles = await self.cosmos_client.list_vehicles()
            vehicle_obj = find_vehicle(vehicles, vid)
            if not vehicle_obj:
                return self._format_response(
                    "I couldn't find details for your vehicle.", success=False
                )

            # Determine if the vehicle is charging based on available data
            is_charging = engine_status == "off" and battery_level > 0 and battery_level < 100

            charging_status = {
                "isCharging": is_charging,
                "batteryLevel": battery_level,
                "timeRemaining": 60 if is_charging else None,  # Estimated
                "chargingPower": 7.2 if is_charging else None,  # Default value
            }

            if charging_status["isCharging"]:
                response_text = (
                    f"Your vehicle is currently charging. The battery level is {charging_status['batteryLevel']}%. "
                    f"Estimated time to full charge: {charging_status['timeRemaining']} minutes. "
                    f"Current charging power: {charging_status['chargingPower']} kW."
                )
            else:
                response_text = f"Your vehicle is not currently charging. The battery level is {charging_status['batteryLevel']}%."

            return self._format_response(
                response_text,
                data={"chargingStatus": charging_status, "vehicleId": vid},
                function_name="_handle_charging_status",
            )
        except Exception as e:
            logger.error(f"Error retrieving charging status: {str(e)}")
            return self._format_response(
                "I encountered an error while retrieving the charging status. Please try again later.",
                success=False,
                function_name="_handle_charging_status",
            )

    @kernel_function(description="Start vehicle charging")
    async def _handle_start_charging(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID to start charging"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to start charging.",
                success=False,
            )

        try:
            # Get vehicle status
            vehicle_status = await self.cosmos_client.get_vehicle_status(vid)

            # Get vehicle details to check if it's electric
            vehicles = await self.cosmos_client.list_vehicles()
            vehicle_obj = find_vehicle(vehicles, vid)
            if not vehicle_obj:
                return self._format_response(
                    "I couldn't find details for your vehicle.", success=False
                )

            battery_level = vehicle_status.get("battery", 0)

            # Create charging command in Cosmos DB
            await self.cosmos_client.ensure_connected()
            command_obj = Command(
                id=str(uuid.uuid4()),
                command_id=f"charge-{str(uuid.uuid4())[:8]}",
                vehicle_id=vid,
                command_type="start_charging",
                parameters={},
                status="pending",
                timestamp=datetime.datetime.now().isoformat(),
                priority="normal",
            )
            result = await self.cosmos_client.create_command(command_obj.model_dump(by_alias=True))

            if result:
                await self._apply_status_update(
                    vid,
                    {
                        "charging": True,
                        "lastChargeCommandId": command_obj.command_id,
                        "chargeStartedAt": datetime.datetime.now().isoformat(),
                    },
                )
                return self._format_response(
                    f"I've started charging your vehicle. The current battery level is "
                    f"{battery_level}% and the estimated time to full charge is "
                    f"about {(100 - battery_level) * 2} minutes at a standard charging rate.",
                    data={
                        "action": "start_charging",
                        "vehicleId": vid,
                        "status": "success",
                        "commandId": command_obj.command_id,
                    },
                    function_name="_handle_start_charging",
                )
            else:
                return self._format_response(
                    "I couldn't start charging your vehicle. The command was not processed.",
                    success=False,
                    data={
                        "action": "start_charging",
                        "vehicleId": vid,
                        "status": "failed",
                        "error": "Command processing failed",
                    },
                    function_name="_handle_start_charging",
                )
        except Exception as e:
            logger.error(f"Error starting charging: {str(e)}")
            return self._format_response(
                "I encountered an error while trying to start charging. Please try again later.",
                success=False,
                function_name="_handle_start_charging",
            )

    @kernel_function(description="Stop vehicle charging")
    async def _handle_stop_charging(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID to stop charging"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to stop charging.",
                success=False,
            )

        try:
            # Get vehicle status
            vehicle_status = await self.cosmos_client.get_vehicle_status(vid)

            # Get vehicle details to check if it's electric
            vehicles = await self.cosmos_client.list_vehicles()
            vehicle_obj = find_vehicle(vehicles, vid)
            if not vehicle_obj:
                return self._format_response(
                    "I couldn't find details for your vehicle.", success=False
                )

            battery_level = vehicle_status.get("battery", 0)

            # Create stop charging command in Cosmos DB
            await self.cosmos_client.ensure_connected()
            command_obj = Command(
                id=str(uuid.uuid4()),
                command_id=f"stop-charge-{str(uuid.uuid4())[:8]}",
                vehicle_id=vid,
                command_type="stop_charging",
                parameters={},
                status="pending",
                timestamp=datetime.datetime.now().isoformat(),
                priority="normal",
            )
            result = await self.cosmos_client.create_command(command_obj.model_dump(by_alias=True))

            if result:
                await self._apply_status_update(
                    vid,
                    {
                        "charging": False,
                        "lastChargeCommandId": command_obj.command_id,
                        "chargeStoppedAt": datetime.datetime.now().isoformat(),
                    },
                )
                return self._format_response(
                    f"I've stopped charging your vehicle. The final battery level is "
                    f"{battery_level}%.",
                    data={
                        "action": "stop_charging",
                        "vehicleId": vid,
                        "status": "success",
                        "commandId": command_obj.command_id,
                    },
                    function_name="_handle_stop_charging",
                )
            else:
                return self._format_response(
                    "I couldn't stop charging your vehicle. The command was not processed.",
                    success=False,
                    data={
                        "action": "stop_charging",
                        "vehicleId": vid,
                        "status": "failed",
                        "error": "Command processing failed",
                    },
                    function_name="_handle_stop_charging",
                )
        except Exception as e:
            logger.error(f"Error stopping charging: {str(e)}")
            return self._format_response(
                "I encountered an error while trying to stop charging. Please try again later.",
                success=False,
                function_name="_handle_stop_charging",
            )

    @kernel_function(description="Get energy usage metrics")
    async def _handle_energy_usage(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID to retrieve energy usage for"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to check energy usage for.",
                success=False,
            )

        try:
            # Get vehicle status history to calculate energy usage
            # In a production system, this would come from a specific energy usage tracking system

            # Get vehicle details to check if it's electric
            vehicles = await self.cosmos_client.list_vehicles()
            vehicle_obj = find_vehicle(vehicles, vid)
            if not vehicle_obj:
                return self._format_response(
                    "I couldn't find details for your vehicle.", success=False
                )

            # Get status history
            status_container = await self.cosmos_client.status_container

            # Query for recent status entries of this vehicle
            query = "SELECT * FROM c WHERE c.vehicle_id = @vehicleId ORDER BY c._ts DESC OFFSET 0 LIMIT 20"
            parameters = [{"name": "@vehicleId", "value": vid}]

            items = status_container.query_items(query=query, parameters=parameters)

            # Process status history to calculate energy metrics
            statuses = []
            async for item in items:
                statuses.append(item)

            # Calculate metrics based on available data
            # This is a simplified calculation for demonstration
            battery_levels = [
                s.get("battery", 0) for s in statuses if "battery" in s
            ]

            if not battery_levels:
                # No battery level data, provide default/estimated values
                energy_usage = {
                    "totalKwh": 18.5,  # Default estimate
                    "avgEfficiency": 16.7,
                    "regenerativeBraking": 2.3,
                    "costEstimate": 4.62,
                }
            else:
                # Calculate rough energy usage from battery levels
                # This is simplified; a real implementation would use actual energy measurements
                battery_capacity_kwh = 75.0  # Assume a 75 kWh battery

                # If we have multiple readings, look at the changes
                if len(battery_levels) > 1:
                    # Calculate battery percentage used
                    battery_diff = sum(
                        [
                            max(0, battery_levels[i] - battery_levels[i + 1])
                            for i in range(len(battery_levels) - 1)
                        ]
                    )

                    total_kwh = (battery_diff / 100) * battery_capacity_kwh

                    # Calculate efficiency (kWh/100km) based on mileage if available
                    mileage_readings = [
                        s.get("mileage", 0) for s in statuses if "mileage" in s
                    ]

                    if len(mileage_readings) > 1:
                        distance = abs(mileage_readings[0] - mileage_readings[-1])
                        avg_efficiency = (total_kwh / max(1, distance)) * 100
                    else:
                        avg_efficiency = 16.7  # Default efficiency

                    # Estimate regenerative braking (usually ~10-15% of total energy)
                    regen_kwh = total_kwh * 0.12

                    energy_usage = {
                        "totalKwh": round(total_kwh, 1),
                        "avgEfficiency": round(avg_efficiency, 1),
                        "regenerativeBraking": round(regen_kwh, 1),
                        "costEstimate": round(total_kwh * 0.25, 2),  # Assuming $0.25/kWh
                    }
                else:
                    # Not enough data for calculation, use defaults
                    energy_usage = {
                        "totalKwh": 18.5,
                        "avgEfficiency": 16.7,
                        "regenerativeBraking": 2.3,
                        "costEstimate": 4.62,
                    }

            return self._format_response(
                f"Here's your energy usage summary:\n\n"
                f"• Total energy used: {energy_usage['totalKwh']} kWh\n"
                f"• Average efficiency: {energy_usage['avgEfficiency']} kWh/100 km\n"
                f"• Energy recovered from regenerative braking: {energy_usage['regenerativeBraking']} kWh\n"
                f"• Estimated cost: ${energy_usage['costEstimate']}",
                data={"energyUsage": energy_usage, "vehicleId": vid},
                function_name="_handle_energy_usage",
            )
        except Exception as e:
            logger.error(f"Error retrieving energy usage: {str(e)}")
            return self._format_response(
                "I encountered an error while retrieving energy usage data. Please try again later.",
                success=False,
                function_name="_handle_energy_usage",
            )

    @kernel_function(description="Estimate vehicle range")
    async def _handle_range_estimation(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID to estimate range for"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to estimate range for.",
                success=False,
            )

        try:
            # Get vehicle status
            vehicle_status = await self.cosmos_client.get_vehicle_status(vid)

            # Get vehicle details
            vehicles = await self.cosmos_client.list_vehicles()
            vehicle_obj = find_vehicle(vehicles, vid)
            if not vehicle_obj:
                return self._format_response(
                    "I couldn't find details for your vehicle.", success=False
                )
            vehicle = ensure_dict(vehicle_obj)

            battery_level = vehicle_status.get("battery", 0)

            # Calculate range based on battery level and vehicle model
            # In a real system, this would use the specific vehicle's efficiency data

            # Get vehicle brand and model
            brand = vehicle.get("make", "")
            model = vehicle.get("model", "")

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
            nearest_station_km = await self._get_nearest_charging_station_distance(vid)

            range_data = {
                "batteryLevel": battery_level,
                "estimatedRangeKm": estimated_range_km,
                "estimatedRangeEcoKm": estimated_range_eco_km,
                "nearestStationKm": (nearest_station_km if nearest_station_km else "Unknown"),
            }
            return self._format_response(
                f"Based on your current battery level of {range_data['batteryLevel']}%, "
                f"your estimated range is {range_data['estimatedRangeKm']} km. "
                f"In eco mode, you could potentially reach {range_data['estimatedRangeEcoKm']} km. "
                f"The nearest charging station is {range_data['nearestStationKm']} km away.",
                data={"rangeData": range_data, "vehicleId": vid},
                function_name="_handle_range_estimation",
            )
        except Exception as e:
            logger.error(f"Error estimating range: {str(e)}")
            return self._format_response(
                "I encountered an error while estimating your vehicle's range. Please try again later.",
                success=False,
                function_name="_handle_range_estimation",
            )

    async def _get_vehicle_location(self, vehicle_id: Optional[str]) -> Dict[str, Any]:
        """Get the vehicle's current location from Cosmos DB."""
        if not vehicle_id:
            return {}

        try:
            # Get vehicle status for location
            vehicle = await self.cosmos_client.get_vehicle(vehicle_id)

            if vehicle:
                # Check for location in status
                if "lastLocation" in vehicle:
                    return vehicle["lastLocation"]

            if vehicle and "lastLocation" in vehicle:
                # Convert to lowercase keys for consistency
                return {
                    "latitude": vehicle["lastLocation"].get("latitude", 0),
                    "longitude": vehicle["lastLocation"].get("longitude", 0),
                }

            return {}
        except Exception as e:
            logger.error(f"Error getting vehicle location: {str(e)}")
            return {}

    async def _get_nearest_charging_station_distance(
        self, vehicle_id: Optional[str]
    ) -> Optional[float]:
        """Get the distance to the nearest charging station."""
        try:
            # Get vehicle location
            location = await self._get_vehicle_location(vehicle_id)

            if not location:
                return None
            
            # Dev: Generate random location (for testing)
            async def _random_station_items():
                for i in range(6):
                    lat = location.get("latitude", 0) + random.uniform(-0.05, 0.05)
                    lon = location.get("longitude", 0) + random.uniform(-0.05, 0.05)
                    yield {
                        "id": f"dev-{i}",
                        "name": f"Dev Station {i+1}",
                        "location": {"latitude": lat, "longitude": lon},
                    }

            items = _random_station_items()

            # Find nearest station
            nearest_distance = None
            async for item in items:
                station_location = item.get("location", {})
                station_lat = station_location.get("latitude", 0)
                station_lon = station_location.get("longitude", 0)
                vehicle_lat = location.get("latitude", 0)
                vehicle_lon = location.get("longitude", 0)

                # Simple Euclidean distance (not accurate for geo, but ok for demo)
                distance = (
                    (station_lat - vehicle_lat) ** 2 + (station_lon - vehicle_lon) ** 2
                ) ** 0.5 * 111

                if nearest_distance is None or distance < nearest_distance:
                    nearest_distance = distance

            return round(nearest_distance, 1) if nearest_distance is not None else None
        except Exception as e:
            logger.error(f"Error finding nearest charging station: {str(e)}")
            return None

    def _format_response(
        self,
        message: str,
        success: bool = True,
        data: Optional[Dict[str, Any]] = None,
        function_name: str = "",
    ) -> str:  # Changed from Dict to str
        """Return JSON string to preserve structure through SK's LLM layer."""
        resp = {
            "message": message,
            "success": success,
            "plugins_used": [f"{self.__class__.__name__}.{function_name}"] if function_name else [self.__class__.__name__],
        }
        if data:
            resp["data"] = data
        return json.dumps(resp)  # Return JSON string instead of dict