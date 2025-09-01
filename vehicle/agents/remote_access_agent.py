import datetime
import uuid
from typing import Dict, Any, Optional, Annotated
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

    async def _apply_status_update(self, vehicle_id: str, patch: Dict[str, Any]):
        try:
            current = await self.cosmos_client.get_vehicle_status(vehicle_id) or {}
            if not isinstance(current, dict):
                try:
                    current = current.model_dump()
                except Exception:
                    current = {}
            current.update(patch)
            if hasattr(self.cosmos_client, "update_vehicle_status"):
                await self.cosmos_client.update_vehicle_status(vehicle_id, current)
            elif hasattr(self.cosmos_client, "set_vehicle_status"):
                await self.cosmos_client.set_vehicle_status(vehicle_id, current)
            else:
                container = getattr(self.cosmos_client, "status_container", None)
                if container:
                    await container.upsert_item({"id": vehicle_id, "vehicle_id": vehicle_id, **current})
        except Exception as e:
            logger.debug(f"Status update skipped ({vehicle_id}): {e}")

    @kernel_function(description="Handle a door lock/unlock request.")
    async def _handle_door_lock(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID to lock/unlock"] = "",
        lock: Annotated[bool, "True to lock, False to unlock"] = True,
        call_context: Annotated[Dict[str, Any], "Invocation context"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        action = "lock" if lock else "unlock"
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

            await self._apply_status_update(
                vid,
                {
                    "doorsLocked": lock,
                    "doorsUpdatedAt": datetime.datetime.now().isoformat(),
                    "lastDoorCommandId": command_id,
                },
            )
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
        vehicle_id: Annotated[str, "Vehicle GUID to start/stop engine"] = "",
        start: Annotated[bool, "True to start engine, False to stop"] = True,
        call_context: Annotated[Dict[str, Any], "Invocation context"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        action = "start" if start else "stop"
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

            await self._apply_status_update(
                vid,
                {
                    "engineRunning": start,
                    "engineUpdatedAt": datetime.datetime.now().isoformat(),
                    "lastEngineCommandId": command_id,
                },
            )
            verb = "stopped" if action == "stop" else f"{action}ed"
            return self._format_response(
                f"I've {verb} your vehicle engine remotely.",
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
        self,
        vehicle_id: Annotated[str, "Vehicle GUID to activate horn/lights"] = "",
        action: Annotated[str, "Horn/lights action (e.g., locate)"] = "locate",
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(None, vehicle_id or None)

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

            await self._apply_status_update(
                vid,
                {
                    "locateMode": {
                        "active": True,
                        "durationSec": 10,
                        "activatedAt": datetime.datetime.now().isoformat(),
                        "commandId": command_id,
                    }
                },
            )
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

    def _format_response(
        self, message: str, success: bool = True, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        resp = {"message": message, "success": success}
        if data:
            resp["data"] = data
        return resp

