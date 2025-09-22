import datetime
from typing import Any, Dict, Optional, Annotated
import uuid
from azure.cosmos_db import get_cosmos_client
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from plugin.oai_service import create_chat_service
from utils.logging_config import get_logger
from agents.base.base_agent import BasePlugin
from utils.agent_context import extract_vehicle_id
from models.command import Command  

logger = get_logger(__name__)


class VehicleFeatureControlAgent:
    """
    Vehicle Feature Control Agent for managing in-car features.
    """

    def __init__(self):
        """Initialize the Vehicle Feature Control Agent."""
        # Get the singleton cosmos client instance
        self.cosmos_client = get_cosmos_client()
        service_factory = create_chat_service()
        self.agent = ChatCompletionAgent(
            service=service_factory,
            name="VehicleFeatureControlAgent",
            instructions="You specialize in vehicle feature control including lights, climate, and comfort settings.",
            plugins=[VehicleFeatureControlPlugin()],
        )


class VehicleFeatureControlPlugin(BasePlugin):
    """Plugin for vehicle feature control operations."""

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

    @kernel_function(description="Control vehicle lights (headlights, interior, etc.)")
    async def _handle_lights_control(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID whose lights to control"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context with natural language query"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        query = call_context.get("query", "") if call_context else ""
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to control lights for.",
                success=False,
            )

        try:
            # Extract light type and action from context
            light_type = "headlights"  # default
            action = "on"  # default
            
            if "interior" in query.lower():
                light_type = "interior_lights"
            elif "hazard" in query.lower():
                light_type = "hazard_lights"
            
            if "off" in query.lower() or "turn off" in query.lower():
                action = "off"

            await self.cosmos_client.ensure_connected()

            # Create command
            command_obj = Command(
                id=str(uuid.uuid4()),
                command_id=f"lights_{action}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                vehicle_id=vid,
                command_type=f"lights_{action}",
                parameters={"lightType": light_type},
                status="sent",
                timestamp=datetime.datetime.now().isoformat(),
                priority="normal",
            )
            await self.cosmos_client.create_command(command_obj.model_dump(by_alias=True))

            await self._apply_status_update(
                vid,
                {
                    "lights": {
                        "type": light_type,
                        "state": action,
                        "updatedAt": datetime.datetime.now().isoformat(),
                    }
                },
            )
            return self._format_response(
                f"I've turned {action} the {light_type.replace('_', ' ')} for your vehicle.",
                data={
                    "action": f"lights_{action}",
                    "vehicleId": vid,
                    "lightType": light_type,
                    "commandId": command_obj.command_id,
                },
                function_name="_handle_lights_control",
            )
        except Exception as e:
            return self._format_response(
                "I encountered an error while controlling the lights. Please try again.",
                success=False,
                function_name="_handle_lights_control",
            )

    @kernel_function(description="Control vehicle climate settings")
    async def _handle_climate_control(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID whose climate to control"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context with desired temp/query"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        query = call_context.get("query", "") if call_context else ""
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to control climate for.",
                success=False,
            )

        try:
            # Extract temperature and settings
            temperature = 22  # default
            action = "set_temperature"
            
            # Simple parsing for temperature
            words = query.split()
            for word in words:
                if word.isdigit():
                    temp_val = int(word)
                    if 16 <= temp_val <= 30:
                        temperature = temp_val
                        break

            if "heat" in query.lower():
                action = "heating"
                temperature = max(24, temperature)
            elif "cool" in query.lower() or "ac" in query.lower():
                action = "cooling"
                temperature = min(20, temperature)

            await self.cosmos_client.ensure_connected()

            command_obj = Command(
                id=str(uuid.uuid4()),
                command_id=f"climate_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                vehicle_id=vid,
                command_type="climate_control",
                parameters={
                    "action": action,
                    "temperature": temperature,
                    "auto": True
                },
                status="sent",
                timestamp=datetime.datetime.now().isoformat(),
                priority="normal",
            )
            await self.cosmos_client.create_command(command_obj.model_dump(by_alias=True))

            await self._apply_status_update(
                vid,
                {
                    "climate": {
                        "mode": action,
                        "temperatureC": temperature,
                        "auto": True,
                        "updatedAt": datetime.datetime.now().isoformat(),
                    }
                },
            )
            return self._format_response(
                f"I've set the climate control to {temperature}°C with {action} mode.",
                data={
                    "action": "climate_control",
                    "vehicleId": vid,
                    "temperature": temperature,
                    "mode": action,
                    "commandId": command_obj.command_id,
                },
                function_name="_handle_climate_control",
            )
        except Exception as e:
            return self._format_response(
                "I encountered an error while adjusting the climate control. Please try again.",
                success=False,
                function_name="_handle_climate_control",
            )

    @kernel_function(description="Control vehicle windows")
    async def _handle_windows_control(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID whose windows to control"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context with window action"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        query = call_context.get("query", "") if call_context else ""
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to control windows for.",
                success=False,
            )

        try:
            action = "up" if "up" in query.lower() or "close" in query.lower() else "down"
            window_position = "all"
            
            if "driver" in query.lower():
                window_position = "driver"
            elif "passenger" in query.lower():
                window_position = "passenger"

            await self.cosmos_client.ensure_connected()

            command_obj = Command(
                id=str(uuid.uuid4()),
                command_id=f"windows_{action}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                vehicle_id=vid,
                command_type=f"windows_{action}",
                parameters={"windows": window_position},
                status="sent",
                timestamp=datetime.datetime.now().isoformat(),
                priority="normal",
            )
            await self.cosmos_client.create_command(command_obj.model_dump(by_alias=True))

            await self._apply_status_update(
                vid,
                {
                    "windows": {
                        "target": window_position,
                        "state": action,
                        "updatedAt": datetime.datetime.now().isoformat(),
                    }
                },
            )
            window_text = f"{window_position} windows" if window_position != "all" else "all windows"
            action_text = "rolled up" if action == "up" else "rolled down"

            return self._format_response(
                f"I've {action_text} the {window_text} for your vehicle.",
                data={
                    "action": f"windows_{action}",
                    "vehicleId": vid,
                    "windows": window_position,
                    "commandId": command_obj.command_id,
                },
                function_name="_handle_windows_control",
            )
        except Exception as e:
            return self._format_response(
                "I encountered an error while controlling the windows. Please try again.",
                success=False,
                function_name="_handle_windows_control",
            )

    @kernel_function(description="Get current vehicle feature status")
    async def _handle_feature_status(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID to get feature status for"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        if not vid:
            return self._format_response("Please specify which vehicle to check.", success=False)
        try:
            await self.cosmos_client.ensure_connected()
            status = await self.cosmos_client.get_vehicle_status(vid) or {}
            features = {
                "lights": status.get("lights"),
                "climate": status.get("climate"),
                "windows": status.get("windows"),
                "doorsLocked": status.get("doorsLocked"),
                "engineRunning": status.get("engineRunning"),
            }
            return self._format_response(
                "Feature status retrieved.",
                data={"vehicleId": vid, "features": features},
                function_name="_handle_feature_status",
            )
        except Exception as e:
            return self._format_response(
                "Unable to retrieve feature status.",
                success=False,
                function_name="_handle_feature_status",
            )

    def _format_response(
        self,
        message: str,
        success: bool = True,
        data: Optional[Dict[str, Any]] = None,
        function_name: str | None = None,
    ) -> Dict[str, Any]:
        resp = {"message": message, "success": success}
        if data:
            resp["data"] = data
        resp["plugins_used"] = [f"{self.__class__.__name__}.{function_name}"] if function_name else [self.__class__.__name__]
        return resp


