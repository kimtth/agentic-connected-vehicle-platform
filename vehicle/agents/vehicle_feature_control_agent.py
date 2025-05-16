import datetime
from typing import Any, Dict, Optional
import uuid

from utils.agent_tools import get_latest_status_from_cosmos
from semantic_kernel.functions import kernel_function
from azure.cosmos_db import cosmos_client
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from plugin.oai_service import create_chat_service
from utils.logging_config import get_logger

logger = get_logger(__name__)


class VehicleFeatureControlAgent:
    """
    Vehicle Feature Control Agent for managing in-car features.
    """

    def __init__(self):
        """Initialize the Vehicle Feature Control Agent."""
        service_factory = create_chat_service()
        self.agent = ChatCompletionAgent(
            service=service_factory,
            name="VehicleFeatureControlAgent",
            instructions="You specialize in vehicle feature control.",
            plugins=[VehicleFeatureControlPlugin()],
        )


class VehicleFeatureControlPlugin:
    @kernel_function(
        description="Adjust climate control settings in the vehicle",
        name="adjust_climate_control",
    )
    async def adjust_climate_control(
        self,
        vehicle_id: str,
        temperature: float = 22.0,
        fan_speed: str = "medium",
        ac_on: bool = None,
        heating_on: bool = None,
    ) -> str:
        """Adjust the climate control settings in the vehicle."""
        try:
            # Validate input parameters
            if fan_speed.lower() not in ["low", "medium", "high"]:
                return f"Invalid fan speed: {fan_speed}. Must be one of: low, medium, high."

            if temperature < 16 or temperature > 30:
                return f"Temperature {temperature}°C is outside the acceptable range (16-30°C)."

            # Get current climate settings to determine which values to update
            current_status = await get_latest_status_from_cosmos(vehicle_id)
            if not current_status:
                logger.warning(f"No status found for vehicle {vehicle_id}")

            # Prepare command parameters
            parameters = {"temperature": temperature, "fan_speed": fan_speed.lower()}

            # Only include AC and heating settings if explicitly provided
            if ac_on is not None:
                parameters["isAirConditioningOn"] = ac_on

            if heating_on is not None:
                parameters["isHeatingOn"] = heating_on

            # Create command
            command = {
                "id": str(uuid.uuid4()),
                "commandId": f"climate-{str(uuid.uuid4())[:8]}",
                "vehicleId": vehicle_id,
                "commandType": "SET_CLIMATE",
                "parameters": parameters,
                "status": "pending",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "priority": "Normal",
            }

            # Store in Cosmos DB
            await cosmos_client.create_command(command)

            # Format response based on what was adjusted
            response_parts = [
                f"Temperature set to {temperature}°C",
                f"Fan speed set to {fan_speed}",
            ]

            if ac_on is not None:
                response_parts.append(
                    f"Air conditioning {'turned on' if ac_on else 'turned off'}"
                )

            if heating_on is not None:
                response_parts.append(
                    f"Heating {'turned on' if heating_on else 'turned off'}"
                )

            # Return success message
            return f"Climate control adjusted. {'. '.join(response_parts)}."

        except Exception as e:
            logger.error(f"Error adjusting climate control: {str(e)}")
            return f"Failed to adjust climate control: {str(e)}"

    @kernel_function(
        description="Get active subscriptions for the vehicle", name="get_subscriptions"
    )
    async def get_subscriptions(self, vehicle_id: str) -> str:
        """Get active subscriptions for the vehicle."""
        try:
            # Ensure Cosmos DB connection
            await cosmos_client.ensure_connected()

            # Get vehicle data to check for subscription information
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next(
                (v for v in vehicles if v.get("VehicleId") == vehicle_id), None
            )

            if not vehicle:
                return f"Vehicle with ID {vehicle_id} not found."

            # Look for subscriptions in vehicle data
            # In a real implementation, this would be in a separate collection
            # For now, we'll check the Features field that might contain subscription info
            features = vehicle.get("Features", {})
            subscriptions = []

            # Determine subscriptions based on vehicle features
            if features.get("HasNavigation", False):
                subscriptions.append(
                    {
                        "name": "Navigation Services",
                        "status": "Active",
                        "expiration": "Annual plan",
                    }
                )

            if features.get("HasAutoPilot", False):
                subscriptions.append(
                    {
                        "name": "Advanced Driver Assistance",
                        "status": "Active",
                        "expiration": "Lifetime",
                    }
                )

            # Add some basic subscriptions that most vehicles would have
            subscriptions.append(
                {
                    "name": "Basic Connected Services",
                    "status": "Active",
                    "expiration": "5-year plan",
                }
            )

            # Check if vehicle is electric for EV-specific services
            if features.get("IsElectric", False):
                subscriptions.append(
                    {
                        "name": "EV Charging Network Access",
                        "status": "Active",
                        "expiration": "3-year plan",
                    }
                )

            # Format response
            if not subscriptions:
                return "No active subscriptions found for this vehicle."

            subscription_text = "\n".join(
                [
                    f"• {sub['name']} - {sub['status']} ({sub['expiration']})"
                    for sub in subscriptions
                ]
            )

            return f"Active subscriptions for your vehicle:\n\n{subscription_text}"

        except Exception as e:
            logger.error(f"Error retrieving subscriptions: {str(e)}")
            return f"Failed to retrieve subscription information: {str(e)}"

    @kernel_function(
        description="Set seat heating level in the vehicle", name="set_seat_heating"
    )
    async def set_seat_heating(
        self, vehicle_id: str, seat: str = "driver", level: int = 2
    ) -> str:
        """Set the seat heating level for a specific seat."""
        try:
            # Validate input parameters
            valid_seats = ["driver", "passenger", "rear_left", "rear_right", "all"]
            if seat.lower() not in valid_seats:
                return (
                    f"Invalid seat: {seat}. Must be one of: {', '.join(valid_seats)}."
                )

            if level < 0 or level > 3:
                return f"Invalid heating level: {level}. Must be between 0 (off) and 3 (high)."

            # Create command
            command = {
                "id": str(uuid.uuid4()),
                "commandId": f"seat-heat-{str(uuid.uuid4())[:8]}",
                "vehicleId": vehicle_id,
                "commandType": "SET_SEAT_HEATING",
                "parameters": {"seat": seat.lower(), "level": level},
                "status": "pending",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "priority": "Normal",
            }

            # Store in Cosmos DB
            await cosmos_client.create_command(command)

            # Format response
            seat_display = (
                seat.replace("_", " ").title() if seat != "all" else "All seats"
            )
            level_desc = "Off" if level == 0 else f"Level {level}"

            return f"Seat heating adjusted. {seat_display} heating set to {level_desc}."

        except Exception as e:
            logger.error(f"Error setting seat heating: {str(e)}")
            return f"Failed to set seat heating: {str(e)}"

    @kernel_function(
        description="Get current vehicle settings", name="get_vehicle_settings"
    )
    async def get_vehicle_settings(self, vehicle_id: str) -> str:
        """Get the current settings for a vehicle."""
        try:
            # Get vehicle status from Cosmos DB
            vehicle_status = await get_latest_status_from_cosmos(vehicle_id)

            if not vehicle_status:
                return f"No status information available for vehicle {vehicle_id}."

            # Extract settings from status
            climate_settings = vehicle_status.get("climateSettings", {})
            temp = climate_settings.get("temperature", "N/A")
            fan = climate_settings.get("fanSpeed", "N/A")
            ac_on = climate_settings.get("isAirConditioningOn", False)
            heating_on = climate_settings.get("isHeatingOn", False)

            # Get door status
            door_status = vehicle_status.get("doorStatus", {})
            doors = []
            for door, status in door_status.items():
                doors.append(f"{door.replace('_', ' ').title()}: {status.title()}")

            # Format response
            settings = [
                f"Climate Control:",
                f"  • Temperature: {temp}°C",
                f"  • Fan Speed: {fan.title() if isinstance(fan, str) else fan}",
                f"  • A/C: {'On' if ac_on else 'Off'}",
                f"  • Heating: {'On' if heating_on else 'Off'}",
            ]

            if doors:
                settings.append("Door Status:")
                for door in doors:
                    settings.append(f"  • {door}")

            return "Current Vehicle Settings:\n\n" + "\n".join(settings)

        except Exception as e:
            logger.error(f"Error retrieving vehicle settings: {str(e)}")
            return f"Failed to retrieve vehicle settings: {str(e)}"

    async def process(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Process a vehicle feature control related query.
        """
        vehicle_id = context.get("vehicle_id") if context else None
        if not vehicle_id:
            return "Please specify which vehicle you'd like to control (provide vehicle_id in context)."

        q = query.lower()

        # Climate control
        if any(k in q for k in ["climate", "temperature", "fan", "ac", "heating"]):
            # Advanced: parse out temperature/fan/etc. from the query
            return await self.adjust_climate_control(vehicle_id)

        # Subscriptions
        if "subscription" in q:
            return await self.get_subscriptions(vehicle_id)

        # Seat heating
        if any(k in q for k in ["seat heat", "seat heating", "heated seat"]):
            return await self.set_seat_heating(vehicle_id)

        # Vehicle settings
        if any(k in q for k in ["settings", "status", "current settings"]):
            return await self.get_vehicle_settings(vehicle_id)

        # Fallback help
        return self._format_response(
            "I can help you with the following features:",
            "including adjusting climate control, checking subscriptions, setting seat heating, and getting vehicle settings.",
            data=self._get_capabilities(),
        )

    def _get_capabilities(self) -> Dict[str, str]:
        """Get the capabilities of the agent."""
        return {
            "adjust_climate_control": "Adjust climate control settings",
            "get_subscriptions": "Get active subscriptions",
            "set_seat_heating": "Set seat heating level",
            "get_vehicle_settings": "Get current vehicle settings",
        }
