import datetime
import uuid
from typing import Dict, Any, Optional

from utils.agent_tools import format_notification
from azure.cosmos_db import cosmos_client
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from plugin.oai_service import create_chat_service
from utils.logging_config import get_logger

logger = get_logger(__name__)


class SafetyEmergencyAgent:
    """
    Safety & Emergency Agent for handling emergency-related features.
    """

    def __init__(self):
        service_factory = create_chat_service()
        self.agent = ChatCompletionAgent(
            service=service_factory,
            name="SafetyEmergencyAgent",
            instructions="You specialize in safety and emergency.",
            plugins=[SafetyEmergencyPlugin()],
        )


class SafetyEmergencyPlugin:
    @kernel_function(description="Handle emergency calls")
    async def _handle_emergency_call(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle an emergency call request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle needs emergency assistance.",
                success=False,
            )

        try:
            # Ensure Cosmos DB connection
            await cosmos_client.ensure_connected()

            # Check if vehicle exists
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next(
                (v for v in vehicles if v.get("VehicleId") == vehicle_id), None
            )

            if not vehicle:
                return self._format_response(
                    f"Vehicle with ID {vehicle_id} not found.", success=False
                )

            # Get vehicle location for emergency response
            vehicle_status = await cosmos_client.get_vehicle_status(vehicle_id)

            location = None
            if vehicle_status and "location" in vehicle_status:
                location = vehicle_status["location"]
            elif vehicle and "LastLocation" in vehicle:
                # Convert to lowercase keys for consistency
                location = {
                    "latitude": vehicle["LastLocation"].get("Latitude", 0),
                    "longitude": vehicle["LastLocation"].get("Longitude", 0),
                }

            # Create emergency call command in Cosmos DB
            command_id = (
                f"emergency_call_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            command = {
                "id": str(uuid.uuid4()),
                "commandId": command_id,
                "vehicleId": vehicle_id,
                "commandType": "EMERGENCY_CALL",
                "parameters": {
                    "location": location,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "call_type": "manual",
                },
                "status": "Sent",
                "timestamp": datetime.datetime.now().isoformat(),
                "priority": "Critical",
            }

            await cosmos_client.create_command(command)

            # Create a notification for the emergency call
            notification_id = str(uuid.uuid4())
            notification = {
                "id": str(uuid.uuid4()),
                "notificationId": notification_id,
                "vehicleId": vehicle_id,
                "type": "emergency_call",
                "message": "Emergency call initiated. Help is on the way.",
                "timestamp": datetime.datetime.now().isoformat(),
                "read": False,
                "severity": "critical",
                "source": "System",
                "actionRequired": True,
                "actionUrl": f"/emergency/{notification_id}",
            }

            await cosmos_client.create_notification(notification)

            # Format notification for response
            formatted_notification = format_notification(
                notification_type="system_alert",
                message="Emergency call initiated. Help is on the way.",
                severity="critical",
            )

            return self._format_response(
                "Emergency call has been initiated. Help is on the way. "
                "Stay on the line and follow any instructions from emergency services.",
                data={
                    "action": "emergency_call",
                    "vehicle_id": vehicle_id,
                    "status": "initiated",
                    "notification": formatted_notification,
                    "location": location,
                    "command_id": command_id,
                },
            )

        except Exception as e:
            logger.error(f"Error handling emergency call: {str(e)}")
            return self._format_response(
                "I encountered an error while trying to initiate the emergency call. "
                "Please try again or call emergency services directly.",
                success=False,
            )

    @kernel_function(description="Handle collision alerts")
    async def _handle_collision_alert(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle a collision alert."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle was involved in the collision.",
                success=False,
            )

        try:
            # Ensure Cosmos DB connection
            await cosmos_client.ensure_connected()

            # Check if vehicle exists
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next(
                (v for v in vehicles if v.get("VehicleId") == vehicle_id), None
            )

            if not vehicle:
                return self._format_response(
                    f"Vehicle with ID {vehicle_id} not found.", success=False
                )

            # Get vehicle location for emergency response
            vehicle_status = await cosmos_client.get_vehicle_status(vehicle_id)

            location = None
            if vehicle_status and "location" in vehicle_status:
                location = vehicle_status["location"]
            elif vehicle and "LastLocation" in vehicle:
                # Convert to lowercase keys for consistency
                location = {
                    "latitude": vehicle["LastLocation"].get("Latitude", 0),
                    "longitude": vehicle["LastLocation"].get("Longitude", 0),
                }

            # Create collision alert command in Cosmos DB
            command_id = (
                f"collision_alert_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            command = {
                "id": str(uuid.uuid4()),
                "commandId": command_id,
                "vehicleId": vehicle_id,
                "commandType": "COLLISION_ALERT",
                "parameters": {
                    "location": location,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "severity": "high",
                },
                "status": "Sent",
                "timestamp": datetime.datetime.now().isoformat(),
                "priority": "Critical",
            }

            await cosmos_client.create_command(command)

            # Create a notification for the collision alert
            notification_id = str(uuid.uuid4())
            notification = {
                "id": str(uuid.uuid4()),
                "notificationId": notification_id,
                "vehicleId": vehicle_id,
                "type": "collision_alert",
                "message": "Collision detected. Emergency services have been notified.",
                "timestamp": datetime.datetime.now().isoformat(),
                "read": False,
                "severity": "critical",
                "source": "Vehicle",
                "actionRequired": True,
                "actionUrl": f"/emergency/{notification_id}",
            }

            await cosmos_client.create_notification(notification)

            # Format notification for response
            formatted_notification = format_notification(
                notification_type="system_alert",
                message="Collision detected. Emergency services have been notified.",
                severity="critical",
            )

            return self._format_response(
                "I've detected a collision and notified emergency services. "
                "Are you okay? Do you need any immediate assistance?",
                data={
                    "action": "collision_alert",
                    "vehicle_id": vehicle_id,
                    "status": "processed",
                    "notification": formatted_notification,
                    "location": location,
                    "command_id": command_id,
                },
            )

        except Exception as e:
            logger.error(f"Error handling collision alert: {str(e)}")
            return self._format_response(
                "I encountered an error while processing the collision alert. "
                "Please call emergency services directly if you need immediate assistance.",
                success=False,
            )

    @kernel_function(description="Handle theft notifications")
    async def _handle_theft_notification(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle a theft notification."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you believe has been stolen.",
                success=False,
            )

        try:
            # Ensure Cosmos DB connection
            await cosmos_client.ensure_connected()

            # Check if vehicle exists
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next(
                (v for v in vehicles if v.get("VehicleId") == vehicle_id), None
            )

            if not vehicle:
                return self._format_response(
                    f"Vehicle with ID {vehicle_id} not found.", success=False
                )

            # Get vehicle location for tracking
            vehicle_status = await cosmos_client.get_vehicle_status(vehicle_id)

            location = None
            if vehicle_status and "location" in vehicle_status:
                location = vehicle_status["location"]
            elif vehicle and "LastLocation" in vehicle:
                # Convert to lowercase keys for consistency
                location = {
                    "latitude": vehicle["LastLocation"].get("Latitude", 0),
                    "longitude": vehicle["LastLocation"].get("Longitude", 0),
                }

            # Create theft notification command in Cosmos DB
            command_id = (
                f"theft_notification_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            command = {
                "id": str(uuid.uuid4()),
                "commandId": command_id,
                "vehicleId": vehicle_id,
                "commandType": "THEFT_NOTIFICATION",
                "parameters": {
                    "location": location,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "reported_by": "owner",
                },
                "status": "Sent",
                "timestamp": datetime.datetime.now().isoformat(),
                "priority": "High",
            }

            await cosmos_client.create_command(command)

            # Create a notification for the theft alert
            notification_id = str(uuid.uuid4())
            notification = {
                "id": str(uuid.uuid4()),
                "notificationId": notification_id,
                "vehicleId": vehicle_id,
                "type": "theft_alert",
                "message": "Potential vehicle theft detected. Authorities have been notified.",
                "timestamp": datetime.datetime.now().isoformat(),
                "read": False,
                "severity": "high",
                "source": "System",
                "actionRequired": True,
                "actionUrl": f"/security/{notification_id}",
            }

            await cosmos_client.create_notification(notification)

            # Format notification for response
            formatted_notification = format_notification(
                notification_type="system_alert",
                message="Potential vehicle theft detected. Authorities have been notified.",
                severity="high",
            )

            return self._format_response(
                "I've recorded your vehicle theft report and notified the authorities. "
                "The vehicle's location is being tracked, and you'll receive updates on the situation.",
                data={
                    "action": "theft_notification",
                    "vehicle_id": vehicle_id,
                    "status": "processed",
                    "notification": formatted_notification,
                    "location": location,
                    "command_id": command_id,
                },
            )

        except Exception as e:
            logger.error(f"Error handling theft notification: {str(e)}")
            return self._format_response(
                "I encountered an error while processing the theft notification. "
                "Please contact authorities directly to report the theft.",
                success=False,
            )

    @kernel_function(description="Handle SOS requests")
    async def _handle_sos(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle an SOS request with immediate emergency response."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle needs SOS assistance.",
                success=False,
            )

        try:
            await cosmos_client.ensure_connected()

            # Check if vehicle exists
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next(
                (v for v in vehicles if v.get("VehicleId") == vehicle_id), None
            )

            if not vehicle:
                return self._format_response(
                    f"Vehicle with ID {vehicle_id} not found.", success=False
                )

            # Get vehicle location
            vehicle_status = await cosmos_client.get_vehicle_status(vehicle_id)
            location = None
            if vehicle_status and "location" in vehicle_status:
                location = vehicle_status["location"]
            elif vehicle and "LastLocation" in vehicle:
                location = {
                    "latitude": vehicle["LastLocation"].get("Latitude", 0),
                    "longitude": vehicle["LastLocation"].get("Longitude", 0),
                }

            # Create SOS command
            command_id = f"sos_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

            command = {
                "id": str(uuid.uuid4()),
                "commandId": command_id,
                "vehicleId": vehicle_id,
                "commandType": "SOS_REQUEST",
                "parameters": {
                    "location": location,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "priority": "critical",
                },
                "status": "Sent",
                "timestamp": datetime.datetime.now().isoformat(),
                "priority": "Critical",
            }

            await cosmos_client.create_command(command)

            # Create SOS notification
            notification = {
                "id": str(uuid.uuid4()),
                "notificationId": str(uuid.uuid4()),
                "vehicleId": vehicle_id,
                "type": "sos_request",
                "message": "SOS request activated. Emergency services have been contacted.",
                "timestamp": datetime.datetime.now().isoformat(),
                "read": False,
                "severity": "critical",
                "source": "System",
                "actionRequired": True,
                "actionUrl": f"/emergency/sos/{command_id}",
            }

            await cosmos_client.create_notification(notification)

            formatted_notification = format_notification(
                notification_type="emergency_alert",
                message="SOS request activated. Emergency services have been contacted.",
                severity="critical",
            )

            return self._format_response(
                "SOS request has been activated. Emergency services have been contacted and "
                "are being dispatched to your location. Please stay calm and wait for assistance.",
                data={
                    "action": "sos_request",
                    "vehicle_id": vehicle_id,
                    "status": "activated",
                    "notification": formatted_notification,
                    "location": location,
                    "command_id": command_id,
                },
            )

        except Exception as e:
            logger.error(f"Error handling SOS request: {e}")
            return self._format_response(
                "I encountered an error while processing the SOS request. "
                "Please call emergency services directly at your local emergency number.",
                success=False,
            )

    async def process(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a safety or emergency related query.

        Args:
            query: User query about safety or emergency features
            context: Additional context for the query

        Returns:
            Response with safety or emergency information or actions
        """
        # Extract vehicle ID from context if available
        vehicle_id = context.get("vehicle_id") if context else None

        # Simple keyword-based logic for demonstration
        query_lower = query.lower()

        # Handle emergency call requests
        if "ecall" in query_lower or "emergency call" in query_lower:
            return await self._handle_emergency_call(vehicle_id, context)

        # Handle collision alert requests
        elif (
            "collision" in query_lower
            or "crash" in query_lower
            or "accident" in query_lower
        ):
            return await self._handle_collision_alert(vehicle_id, context)

        # Handle theft notification requests
        elif "theft" in query_lower or "stolen" in query_lower:
            return await self._handle_theft_notification(vehicle_id, context)

        # Handle SOS requests
        elif "sos" in query_lower or "help" in query_lower:
            return await self._handle_sos(vehicle_id, context)

        # Handle speed alert requests
        elif "speed" in query_lower and "alert" in query_lower:
            return await self._handle_speed_alert(vehicle_id, context)

        # Handle curfew alert requests
        elif "curfew" in query_lower:
            return await self._handle_curfew_alert(vehicle_id, context)

        # Handle battery alert requests
        elif "battery" in query_lower and "alert" in query_lower:
            return await self._handle_battery_alert(vehicle_id, context)

        # Handle general information requests
        else:
            return self._format_response(
                "I can help you with safety and emergency features, including emergency calls, "
                "collision alerts, theft notifications, and SOS assistance. "
                "What would you like to do?",
                data=self._get_capabilities(),
            )

    def _get_capabilities(self) -> Dict[str, str]:
        """Get the capabilities of this agent."""
        return {
            "emergency_call": "Initiate emergency calls to local emergency services",
            "collision_alert": "Process collision alerts and notify emergency services",
            "theft_notification": "Report vehicle theft and track vehicle location",
            "sos": "Send an SOS signal for immediate assistance",
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
