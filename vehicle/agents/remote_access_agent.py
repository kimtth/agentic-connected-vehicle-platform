import datetime
import uuid
from typing import Dict, Any, Optional

from utils.agent_tools import validate_command
from azure.cosmos_db import cosmos_client
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from plugin.oai_service import create_chat_service
from utils.logging_config import get_logger
from agents.base.base_agent import BasePlugin

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
            instructions="You specialize in remote vehicle access control including door locks, engine start/stop, and horn/lights.",
            plugins=[RemoteAccessPlugin()],
        )


class RemoteAccessPlugin(BasePlugin):
    """Plugin for remote access operations."""

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
                    f"Command validation failed: {validation.get('reason', 'Unknown error')}",
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

            return self._format_response(
                f"I've {action}ed your vehicle doors.",
                data={
                    "action": f"door_{action}",
                    "vehicle_id": vehicle_id,
                    "command_id": command_id,
                },
            )

        except Exception as e:
            logger.error(f"Error handling door lock request: {e}")
            return self._format_response(
                f"I encountered an error while trying to {action} the doors. Please try again.",
                success=False,
            )

    @kernel_function(description="Handle remote engine start/stop request.")
    async def _handle_engine_control(
        self,
        vehicle_id: Optional[str],
        start: bool,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle remote engine start/stop request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to control the engine for.",
                success=False,
            )

        try:
            action = "start" if start else "stop"
            
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

            command_type = "START_ENGINE" if start else "STOP_ENGINE"
            command_id = f"engine_{action}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

            command = {
                "id": str(uuid.uuid4()),
                "commandId": command_id,
                "vehicleId": vehicle_id,
                "commandType": command_type,
                "parameters": {"remote": True},
                "status": "Sent",
                "timestamp": datetime.datetime.now().isoformat(),
                "priority": "High",
            }

            await cosmos_client.create_command(command)

            return self._format_response(
                f"I've {action}ed your vehicle engine remotely.",
                data={
                    "action": f"engine_{action}",
                    "vehicle_id": vehicle_id,
                    "command_id": command_id,
                },
            )

        except Exception as e:
            logger.error(f"Error handling engine control: {e}")
            return self._format_response(
                f"I encountered an error while trying to {action} the engine. Please try again.",
                success=False,
            )

    @kernel_function(description="Handle horn and lights activation.")
    async def _handle_horn_lights(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle horn and lights activation for vehicle location."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to activate horn and lights for.",
                success=False,
            )

        try:
            await cosmos_client.ensure_connected()

            command_id = f"horn_lights_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

            command = {
                "id": str(uuid.uuid4()),
                "commandId": command_id,
                "vehicleId": vehicle_id,
                "commandType": "HORN_LIGHTS",
                "parameters": {"duration": 10},
                "status": "Sent",
                "timestamp": datetime.datetime.now().isoformat(),
                "priority": "Normal",
            }

            await cosmos_client.create_command(command)

            return self._format_response(
                "I've activated the horn and lights to help you locate your vehicle.",
                data={
                    "action": "horn_lights",
                    "vehicle_id": vehicle_id,
                    "command_id": command_id,
                },
            )

        except Exception as e:
            logger.error(f"Error activating horn and lights: {e}")
            return self._format_response(
                "I encountered an error while activating horn and lights. Please try again.",
                success=False,
            )

    async def process(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process remote access requests."""
        vehicle_id = context.get("vehicle_id") if context else None
        query_lower = query.lower()

        if "lock" in query_lower:
            return await self._handle_door_lock(vehicle_id, True, context)
        elif "unlock" in query_lower:
            return await self._handle_door_lock(vehicle_id, False, context)
        elif "start" in query_lower and "engine" in query_lower:
            return await self._handle_engine_control(vehicle_id, True, context)
        elif "stop" in query_lower and "engine" in query_lower:
            return await self._handle_engine_control(vehicle_id, False, context)
        elif "horn" in query_lower or "locate" in query_lower:
            return await self._handle_horn_lights(vehicle_id, context)
        else:
            return self._format_response(
                "I can help you with remote vehicle access including locking/unlocking doors, "
                "starting/stopping the engine, and activating horn and lights to locate your vehicle. "
                "What would you like to do?",
                data=self._get_capabilities(),
            )

    def _get_capabilities(self) -> Dict[str, str]:
        """Get the capabilities of this agent."""
        return {
            "door_control": "Lock and unlock vehicle doors",
            "engine_control": "Remotely start and stop the engine",
            "locate_vehicle": "Activate horn and lights to locate the vehicle",
        }
