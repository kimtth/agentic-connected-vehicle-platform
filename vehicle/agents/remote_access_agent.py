import datetime
import uuid
from typing import Dict, Any, Optional

from utils.agent_tools import validate_command
from azure.cosmos_db import cosmos_client
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from plugin.oai_service import create_chat_service
from utils.logging_config import get_logger

logger = get_logger(__name__)


class RemoteAccessAgent:
    """
    Remote Access Agent for controlling vehicle access and remote operations.
    """

    def __init__(self):
        """Initialize the Remote Access Agent."""
        service_factory = create_chat_service()
        self.agent = ChatCompletionAgent(
            service=service_factory,
            name="RemoteAccessAgent",
            instructions="You specialize in remote access.",
            plugins=[RemoteAccessPlugin()],
        )


class RemoteAccessPlugin:
    @kernel_function(description="Handle a door lock/unlock request.")
    async def _handle_door_lock(
        self,
        vehicle_id: Optional[str],
        lock: bool,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle a door lock/unlock request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to control.", success=False
            )

        try:
            action = "lock" if lock else "unlock"

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

            # Validate the command
            command_type = "LOCK_DOORS" if lock else "UNLOCK_DOORS"
            command_id = f"remote_access_{action}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

            validation = await validate_command(
                command_id=command_id,
                command_type=command_type,
                parameters={"doors": "all"},
            )

            if not validation.get("valid", False):
                return self._format_response(
                    f"I couldn't {action} the doors: {validation.get('error', 'Unknown error')}",
                    success=False,
                )

            # Create the command in Cosmos DB
            command = {
                "id": str(uuid.uuid4()),
                "commandId": command_id,
                "vehicleId": vehicle_id,
                "commandType": command_type,
                "parameters": {"doors": "all"},
                "status": "Sent",
                "timestamp": datetime.datetime.now().isoformat(),
                "priority": "Normal",
            }

            await cosmos_client.create_command(command)

            # Update vehicle status in Cosmos DB
            current_status = await cosmos_client.get_vehicle_status(vehicle_id)

            if current_status:
                # Create updated status with locked doors
                new_status = current_status.copy()

                # Update door status
                if "doorStatus" in new_status:
                    door_status = new_status["doorStatus"]
                    for door in door_status:
                        door_status[door] = "locked" if lock else "unlocked"
                else:
                    # Create door status if it doesn't exist
                    new_status["doorStatus"] = {
                        "driver": "locked" if lock else "unlocked",
                        "passenger": "locked" if lock else "unlocked",
                        "rearLeft": "locked" if lock else "unlocked",
                        "rearRight": "locked" if lock else "unlocked",
                    }

                # Update timestamp
                new_status["timestamp"] = datetime.datetime.now().isoformat()

                # Create a new status document (don't update existing to maintain history)
                new_status["id"] = str(uuid.uuid4())
                await cosmos_client.create_vehicle_status(new_status)

            # Create a notification for the action
            notification = {
                "id": str(uuid.uuid4()),
                "notificationId": str(uuid.uuid4()),
                "vehicleId": vehicle_id,
                "type": "door_operation",
                "message": f"Vehicle doors have been {action}ed remotely",
                "timestamp": datetime.datetime.now().isoformat(),
                "read": False,
                "severity": "low",
                "source": "System",
                "actionRequired": False,
            }

            await cosmos_client.create_notification(notification)

            return self._format_response(
                f"I've sent a request to {action} all doors on your vehicle.",
                data={
                    "command_type": command_type,
                    "vehicle_id": vehicle_id,
                    "status": "sent",
                    "command_id": command_id,
                },
            )

        except Exception as e:
            logger.error(f"Error handling door {action}: {str(e)}")
            return self._format_response(
                f"I encountered an error while trying to {action} the doors. Please try again later.",
                success=False,
            )

    @kernel_function(description="Handle an engine start/stop request.")
    async def _handle_engine_control(
        self,
        vehicle_id: Optional[str],
        start: bool,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle an engine start/stop request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to control.", success=False
            )

        try:
            action = "start" if start else "stop"

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

            # Get current status to check if engine is already in the requested state
            current_status = await cosmos_client.get_vehicle_status(vehicle_id)
            if current_status:
                current_engine_status = current_status.get("engineStatus", "unknown")

                if (start and current_engine_status == "on") or (
                    not start and current_engine_status == "off"
                ):
                    status_text = "already running" if start else "already off"
                    return self._format_response(
                        f"The engine is {status_text}.",
                        success=True,
                        data={
                            "command_type": "ENGINE_CONTROL",
                            "vehicle_id": vehicle_id,
                            "status": "no_action_needed",
                        },
                    )

            # Validate the command
            command_type = "START_ENGINE" if start else "STOP_ENGINE"
            command_id = f"remote_access_{action}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            parameters = {"ignition_level": "run"} if start else {}

            validation = await validate_command(
                command_id=command_id, command_type=command_type, parameters=parameters
            )

            if not validation.get("valid", False):
                return self._format_response(
                    f"I couldn't {action} the engine: {validation.get('error', 'Unknown error')}",
                    success=False,
                )

            # Create the command in Cosmos DB
            command = {
                "id": str(uuid.uuid4()),
                "commandId": command_id,
                "vehicleId": vehicle_id,
                "commandType": command_type,
                "parameters": parameters,
                "status": "Sent",
                "timestamp": datetime.datetime.now().isoformat(),
                "priority": "High",
            }

            await cosmos_client.create_command(command)

            # Update vehicle status in Cosmos DB
            if current_status:
                # Create updated status with new engine state
                new_status = current_status.copy()

                # Update engine status
                new_status["engineStatus"] = "on" if start else "off"

                # If engine starting, set initial speed to 0
                if start:
                    new_status["speed"] = 0

                # Update timestamp
                new_status["timestamp"] = datetime.datetime.now().isoformat()

                # Create a new status document (don't update existing to maintain history)
                new_status["id"] = str(uuid.uuid4())
                await cosmos_client.create_vehicle_status(new_status)

            # Create a notification for the action
            notification = {
                "id": str(uuid.uuid4()),
                "notificationId": str(uuid.uuid4()),
                "vehicleId": vehicle_id,
                "type": "engine_operation",
                "message": f"Vehicle engine has been {action}ed remotely",
                "timestamp": datetime.datetime.now().isoformat(),
                "read": False,
                "severity": "medium",
                "source": "System",
                "actionRequired": False,
            }

            await cosmos_client.create_notification(notification)

            return self._format_response(
                f"I've sent a request to {action} the engine on your vehicle.",
                data={
                    "command_type": command_type,
                    "vehicle_id": vehicle_id,
                    "status": "sent",
                    "command_id": command_id,
                },
            )

        except Exception as e:
            logger.error(f"Error handling engine {action}: {str(e)}")
            return self._format_response(
                f"I encountered an error while trying to {action} the engine. Please try again later.",
                success=False,
            )

    @kernel_function(description="Handle a data sync request.")
    async def _handle_data_sync(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle a data sync request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to sync data with.",
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

            # Create a sync command in Cosmos DB
            command_id = f"data_sync_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

            command = {
                "id": str(uuid.uuid4()),
                "commandId": command_id,
                "vehicleId": vehicle_id,
                "commandType": "SYNC_DATA",
                "parameters": {
                    "sync_type": "personal_data",
                    "timestamp": datetime.datetime.now().isoformat(),
                },
                "status": "Sent",
                "timestamp": datetime.datetime.now().isoformat(),
                "priority": "Low",
            }

            await cosmos_client.create_command(command)

            # Create a notification for the action
            notification = {
                "id": str(uuid.uuid4()),
                "notificationId": str(uuid.uuid4()),
                "vehicleId": vehicle_id,
                "type": "data_sync",
                "message": "Personal data synchronization initiated",
                "timestamp": datetime.datetime.now().isoformat(),
                "read": False,
                "severity": "low",
                "source": "System",
                "actionRequired": False,
            }

            await cosmos_client.create_notification(notification)

            return self._format_response(
                "I've initiated a sync of your personal data with the vehicle. "
                "Your preferences, contacts, and settings will be updated shortly.",
                data={
                    "sync_type": "personal_data",
                    "vehicle_id": vehicle_id,
                    "status": "initiated",
                    "command_id": command_id,
                },
            )

        except Exception as e:
            logger.error(f"Error handling data sync: {str(e)}")
            return self._format_response(
                "I encountered an error while trying to sync your data. Please try again later.",
                success=False,
            )

    async def process(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a remote access related query.

        Args:
            query: User query about remote access features
            context: Additional context for the query

        Returns:
            Response with remote access information or actions
        """
        # Extract vehicle ID from context if available
        vehicle_id = context.get("vehicle_id") if context else None

        # Simple keyword-based logic for demonstration
        query_lower = query.lower()

        # Handle door locking/unlocking requests
        if "lock" in query_lower and "door" in query_lower:
            return await self._handle_door_lock(vehicle_id, True, context)
        elif "unlock" in query_lower and "door" in query_lower:
            return await self._handle_door_lock(vehicle_id, False, context)

        # Handle engine start/stop requests
        elif (
            "start" in query_lower and "engine" in query_lower
        ) or "remote start" in query_lower:
            return await self._handle_engine_control(vehicle_id, True, context)
        elif "stop" in query_lower and "engine" in query_lower:
            return await self._handle_engine_control(vehicle_id, False, context)

        # Handle sync data requests
        elif "sync" in query_lower and (
            "data" in query_lower or "profile" in query_lower
        ):
            return await self._handle_data_sync(vehicle_id, context)

        # Handle general information requests
        else:
            return self._format_response(
                "I can help you with remote vehicle access, including locking/unlocking doors, "
                "starting/stopping the engine remotely, and syncing your personal data with the vehicle. "
                "What would you like to do?",
                data=self._get_capabilities(),
            )

    def _get_capabilities(self) -> Dict[str, str]:
        """Get the capabilities of this agent."""
        return {
            "door_control": "Lock and unlock vehicle doors remotely",
            "engine_control": "Start and stop the engine remotely",
            "data_sync": "Sync personal data and preferences with the vehicle",
        }
