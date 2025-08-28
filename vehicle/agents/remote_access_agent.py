import datetime
import uuid
from typing import Dict, Any, Optional
from azure.cosmos_db import get_cosmos_client
from utils.agent_tools import validate_command
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from plugin.oai_service import create_chat_service
from utils.logging_config import get_logger
from agents.base.base_agent import BasePlugin
from utils.agent_context import extract_vehicle_id
from utils.vehicle_object_utils import find_vehicle
from models.command import Command  # NEW: use Pydantic model for camelCase serialization

logger = get_logger(__name__)


class RemoteAccessAgent:
    """
    Remote Access Agent for controlling vehicle access and remote operations.
    """

    def __init__(self):
        """Initialize the Remote Access Agent."""
        # Get the singleton cosmos client instance
        self.cosmos_client = get_cosmos_client()
        service_factory = create_chat_service()
        self.agent = ChatCompletionAgent(
            service=service_factory,
            name="RemoteAccessAgent",
            instructions="You specialize in remote vehicle access control including door locks, engine start/stop, and horn/lights.",
            plugins=[RemoteAccessPlugin()],
        )

class RemoteAccessPlugin(BasePlugin):
    """Plugin for remote access operations."""

    def __init__(self):
        # Get the singleton cosmos client instance
        self.cosmos_client = get_cosmos_client()

    @kernel_function(description="Handle a door lock/unlock request.")
    async def _handle_door_lock(
        self,
        vehicle_id: Optional[str] = None,
        lock: Optional[bool] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(context, vehicle_id)
        # Validate lock flag
        if lock is None:
            return self._format_response(
                "Please specify whether to lock or unlock the doors.", success=False
            )

        action = "lock" if lock else "unlock"
        vid = extract_vehicle_id(vehicle_id)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to control.", success=False
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

            # Validate the command
            command_type = "lock_doors" if lock else "unlock_doors"
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

            # Create the command in Cosmos DB via model (replaces raw dict)
            command_obj = Command(
                id=str(uuid.uuid4()),
                command_id=command_id,
                vehicle_id=vid,
                command_type=command_type.lower(),
                parameters={"doors": "all"},
                status="sent",
                timestamp=datetime.datetime.now().isoformat(),
                priority="normal",
            )
            await self.cosmos_client.create_command(command_obj.model_dump(by_alias=True))

            return self._format_response(
                f"I've {action}ed your vehicle doors.",
                data={
                    "action": f"door_{action}",
                    "vehicleId": vid,
                    "commandId": command_id,
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
        vehicle_id: Optional[str] = None,
        start: bool = True,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(context, vehicle_id)
        """Handle remote engine start/stop request."""
        action = "start" if start else "stop"
        vid = extract_vehicle_id(vehicle_id)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to control the engine for.",
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

            command_type = "start_engine" if start else "stop_engine"
            command_id = (
                f"engine_{action}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            command_obj = Command(
                id=str(uuid.uuid4()),
                command_id=command_id,
                vehicle_id=vid,
                command_type=command_type.lower(),
                parameters={"remote": True},
                status="sent",
                timestamp=datetime.datetime.now().isoformat(),
                priority="high",
            )
            await self.cosmos_client.create_command(command_obj.model_dump(by_alias=True))

            return self._format_response(
                f"I've {action}ed your vehicle engine remotely.",
                data={
                    "action": f"engine_{action}",
                    "vehicleId": vid,
                    "commandId": command_id,
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
        self, vehicle_id: Optional[str] = None, action: Optional[str] = "locate"
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(None, vehicle_id)

        if not vid:
            return self._format_response("vehicle_id is required", success=False)

        try:
            await self.cosmos_client.ensure_connected()

            command_id = (
                f"horn_lights_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            )

            command_obj = Command(
                id=str(uuid.uuid4()),
                command_id=command_id,
                vehicle_id=vid,
                command_type="horn_lights",
                parameters={"duration": 10},
                status="sent",
                timestamp=datetime.datetime.now().isoformat(),
                priority="normal",
            )
            await self.cosmos_client.create_command(command_obj.model_dump(by_alias=True))

            return self._format_response(
                "I've activated the horn and lights to help you locate your vehicle.",
                data={
                    "action": "HORN_LIGHTS",
                    "vehicleId": vid,
                    "commandId": command_id,
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
        vehicle_id = (context or {}).get("vehicleId") or (context or {}).get("vehicle_id")
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
            return await self._handle_horn_lights(vehicle_id)
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
            "doorControl": "Lock and unlock vehicle doors",
            "engineControl": "Remotely start and stop the engine",
            "locateVehicle": "Activate horn and lights to locate the vehicle",
        }

    def _format_response(
        self, message: str, success: bool = True, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        resp = {"message": message, "success": success}
        if data:
            resp["data"] = data
        return resp

