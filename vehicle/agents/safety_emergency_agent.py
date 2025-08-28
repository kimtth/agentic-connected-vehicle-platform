import datetime
import uuid
from typing import Dict, Any, Optional 
from azure.cosmos_db import get_cosmos_client
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from plugin.oai_service import create_chat_service
from utils.logging_config import get_logger
from utils.agent_context import extract_vehicle_id
from utils.vehicle_object_utils import find_vehicle, extract_location
from models.command import Command  # NEW
from models.notification import Notification  # NEW

logger = get_logger(__name__)


class SafetyEmergencyAgent:
    """
    Safety & Emergency Agent for handling emergency-related features.
    """

    def __init__(self):
        # Get the singleton cosmos client instance
        self.cosmos_client = get_cosmos_client()
        service_factory = create_chat_service()
        self.agent = ChatCompletionAgent(
            service=service_factory,
            name="SafetyEmergencyAgent",
            instructions="You specialize in safety and emergency.",
            plugins=[SafetyEmergencyPlugin()],
        )


class SafetyEmergencyPlugin:
    def __init__(self):
        # Get the singleton cosmos client instance
        self.cosmos_client = get_cosmos_client()

    @kernel_function(description="Handle emergency calls")
    async def _handle_emergency_call(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle an emergency call request."""
        vid = extract_vehicle_id(context, vehicle_id)
        if not vid:
            return self._format_response(
                "Please specify which vehicle needs emergency assistance.",
                success=False,
            )

        try:
            # Ensure Cosmos DB connection
            await self.cosmos_client.ensure_connected()

            # Check if vehicle exists
            vehicles = await self.cosmos_client.list_vehicles()
            vehicle = find_vehicle(vehicles, vid)
            if not vehicle:
                return self._format_response(
                    f"Vehicle with ID {vid} not found.", success=False
                )
            vehicle_status = await self.cosmos_client.get_vehicle_status(vid)
            location = extract_location(vehicle_status, vehicle)

            # Create emergency call command in Cosmos DB
            command_id = f"emergency_call_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            command_obj = Command(
                id=str(uuid.uuid4()),
                command_id=command_id,
                vehicle_id=vid,
                command_type="emergency_call",
                parameters={
                    "location": location,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "callType": "manual",
                },
                status="sent",
                timestamp=datetime.datetime.now().isoformat(),
                priority="critical",
            )
            await self.cosmos_client.create_command(command_obj.model_dump(by_alias=True))

            notification_id = str(uuid.uuid4())
            notification_obj = Notification(
                id=str(uuid.uuid4()),
                notification_id=notification_id,
                vehicle_id=vid,
                type="emergency_call",
                message="Emergency call initiated. Help is on the way.",
                timestamp=datetime.datetime.now().isoformat(),
                read=False,
                severity="critical",
                source="system",
                action_required=True,
                action_url=f"/emergency/{notification_id}",
            )
            await self.cosmos_client.create_notification(notification_obj.model_dump(by_alias=True))

            return self._format_response(
                "Emergency call has been initiated. Help is on the way. "
                "Stay on the line and follow any instructions from emergency services.",
                data={
                    "action": "emergency_call",
                    "vehicleId": vid,
                    "status": "initiated",
                    "notification": notification_obj.model_dump(by_alias=True),
                    "location": location,
                    "commandId": command_id,
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
        vid = extract_vehicle_id(context, vehicle_id)
        if not vid:
            return self._format_response(
                "Please specify which vehicle was involved in the collision.",
                success=False,
            )

        try:
            # Ensure Cosmos DB connection
            await self.cosmos_client.ensure_connected()

            # Check if vehicle exists
            vehicles = await self.cosmos_client.list_vehicles()
            vehicle = find_vehicle(vehicles, vid)
            if not vehicle:
                return self._format_response(
                    f"Vehicle with ID {vid} not found.", success=False
                )

            vehicle_status = await self.cosmos_client.get_vehicle_status(vid)
            location = extract_location(vehicle_status, vehicle)

            # Create collision alert command in Cosmos DB
            command_id = f"collision_alert_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            command_obj = Command(
                id=str(uuid.uuid4()),
                command_id=command_id,
                vehicle_id=vid,
                command_type="collision_alert",
                parameters={
                    "location": location,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "severity": "high",
                },
                status="sent",
                timestamp=datetime.datetime.now().isoformat(),
                priority="critical",
            )
            await self.cosmos_client.create_command(command_obj.model_dump(by_alias=True))

            notification_id = str(uuid.uuid4())
            notification_obj = Notification(
                id=str(uuid.uuid4()),
                notification_id=notification_id,
                vehicle_id=vid,
                type="collision_alert",
                message="Collision detected. Emergency services have been notified.",
                timestamp=datetime.datetime.now().isoformat(),
                read=False,
                severity="critical",
                source="vehicle",
                action_required=True,
                action_url=f"/emergency/{notification_id}",
            )
            await self.cosmos_client.create_notification(notification_obj.model_dump(by_alias=True))

            return self._format_response(
                "I've detected a collision and notified emergency services. "
                "Are you okay? Do you need any immediate assistance?",
                data={
                    "action": "collision_alert",
                    "vehicleId": vid,
                    "status": "processed",
                    "notification": notification_obj.model_dump(by_alias=True),
                    "location": location,
                    "commandId": command_id,
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
        vid = extract_vehicle_id(context, vehicle_id)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you believe has been stolen.",
                success=False,
            )

        try:
            # Ensure Cosmos DB connection
            await self.cosmos_client.ensure_connected()

            # Check if vehicle exists
            vehicles = await self.cosmos_client.list_vehicles()
            vehicle = find_vehicle(vehicles, vid)
            if not vehicle:
                return self._format_response(
                    f"Vehicle with ID {vid} not found.", success=False
                )

            vehicle_status = await self.cosmos_client.get_vehicle_status(vid)
            location = extract_location(vehicle_status, vehicle)

            # Create theft notification command in Cosmos DB
            command_id = f"theft_notification_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            command_obj = Command(
                id=str(uuid.uuid4()),
                command_id=command_id,
                vehicle_id=vid,
                command_type="theft_notification",
                parameters={
                    "location": location,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "reportedBy": "owner",
                },
                status="sent",
                timestamp=datetime.datetime.now().isoformat(),
                priority="high",
            )
            await self.cosmos_client.create_command(command_obj.model_dump(by_alias=True))

            notification_id = str(uuid.uuid4())
            notification_obj = Notification(
                id=str(uuid.uuid4()),
                notification_id=notification_id,
                vehicle_id=vid,
                type="theft_alert",
                message="Potential vehicle theft detected. Authorities have been notified.",
                timestamp=datetime.datetime.now().isoformat(),
                read=False,
                severity="high",
                source="system",
                action_required=True,
                action_url=f"/security/{notification_id}",
            )
            await self.cosmos_client.create_notification(notification_obj.model_dump(by_alias=True))

            return self._format_response(
                "I've recorded your vehicle theft report and notified the authorities. "
                "The vehicle's location is being tracked, and you'll receive updates on the situation.",
                data={
                    "action": "theft_notification",
                    "vehicleId": vid,
                    "status": "processed",
                    "notification": notification_obj.model_dump(by_alias=True),
                    "location": location,
                    "commandId": command_id,
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
        vid = extract_vehicle_id(context, vehicle_id)
        if not vid:
            return self._format_response(
                "Please specify which vehicle needs SOS assistance.",
                success=False,
            )

        try:
            await self.cosmos_client.ensure_connected()

            # Check if vehicle exists
            vehicles = await self.cosmos_client.list_vehicles()
            vehicle = find_vehicle(vehicles, vid)
            if not vehicle:
                return self._format_response(
                    f"Vehicle with ID {vid} not found.", success=False
                )

            vehicle_status = await self.cosmos_client.get_vehicle_status(vid)
            location = extract_location(vehicle_status, vehicle)

            # Create SOS command
            command_id = f"sos_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            command_obj = Command(
                id=str(uuid.uuid4()),
                command_id=command_id,
                vehicle_id=vid,
                command_type="sos_request",
                parameters={
                    "location": location,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "priority": "critical",
                },
                status="sent",
                timestamp=datetime.datetime.now().isoformat(),
                priority="critical",
            )
            await self.cosmos_client.create_command(command_obj.model_dump(by_alias=True))

            notification_obj = Notification(
                id=str(uuid.uuid4()),
                notification_id=str(uuid.uuid4()),
                vehicle_id=vid,
                type="sos_request",
                message="SOS request activated. Emergency services have been contacted.",
                timestamp=datetime.datetime.now().isoformat(),
                read=False,
                severity="critical",
                source="system",
                action_required=True,
                action_url=f"/emergency/sos/{command_id}",
            )
            await self.cosmos_client.create_notification(notification_obj.model_dump(by_alias=True))

            return self._format_response(
                "SOS request has been activated. Emergency services have been contacted and "
                "are being dispatched to your location. Please stay calm and wait for assistance.",
                data={
                    "action": "sos_request",
                    "vehicleId": vid,
                    "status": "activated",
                    "notification": notification_obj.model_dump(by_alias=True),
                    "location": location,
                    "commandId": command_id,
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
        vehicle_id = (context or {}).get("vehicleId") or (context or {}).get("vehicle_id")

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
        """Get the capabilities of this agent (camelCase keys)."""
        return {
            "emergencyCall": "Initiate emergency calls to local emergency services",
            "collisionAlert": "Process collision alerts and notify emergency services",
            "theftNotification": "Report vehicle theft and track vehicle location",
            "sos": "Send an SOS signal for immediate assistance",
        }

    def _format_response(
        self, message: str, success: bool = True, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        resp = {"message": message, "success": success}
        if data:
            resp["data"] = data
        return resp

