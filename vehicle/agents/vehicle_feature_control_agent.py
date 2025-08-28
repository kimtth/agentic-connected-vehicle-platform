import datetime
from typing import Any, Dict, Optional 
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

    @kernel_function(description="Control vehicle lights (headlights, interior, etc.)")
    async def _handle_lights_control(
        self,
        vehicle_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(context, vehicle_id)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to control lights for.",
                success=False,
            )

        try:
            # Extract light type and action from context
            query = context.get("query", "") if context else ""
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

            return self._format_response(
                f"I've turned {action} the {light_type.replace('_', ' ')} for your vehicle.",
                data={
                    "action": f"lights_{action}",
                    "vehicleId": vid,
                    "lightType": light_type,
                    "commandId": command_obj.command_id,
                },
            )

        except Exception as e:
            logger.error(f"Error controlling lights: {e}")
            return self._format_response(
                "I encountered an error while controlling the lights. Please try again.",
                success=False,
            )

    @kernel_function(description="Control vehicle climate settings")
    async def _handle_climate_control(
        self,
        vehicle_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(context, vehicle_id)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to control climate for.",
                success=False,
            )

        try:
            query = context.get("query", "") if context else ""
            
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

            return self._format_response(
                f"I've set the climate control to {temperature}°C with {action} mode.",
                data={
                    "action": "climate_control",
                    "vehicleId": vid,
                    "temperature": temperature,
                    "mode": action,
                    "commandId": command_obj.command_id,
                },
            )

        except Exception as e:
            logger.error(f"Error controlling climate: {e}")
            return self._format_response(
                "I encountered an error while adjusting the climate control. Please try again.",
                success=False,
            )

    @kernel_function(description="Control vehicle windows")
    async def _handle_windows_control(
        self,
        vehicle_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(context, vehicle_id)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to control windows for.",
                success=False,
            )

        try:
            query = context.get("query", "") if context else ""
            
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
            )

        except Exception as e:
            logger.error(f"Error controlling windows: {e}")
            return self._format_response(
                "I encountered an error while controlling the windows. Please try again.",
                success=False,
            )

    async def process(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        vehicle_id = (context or {}).get("vehicleId") or (context or {}).get("vehicle_id")
        query_lower = query.lower()

        if "light" in query_lower:
            return await self._handle_lights_control(vehicle_id, context)
        elif "climate" in query_lower or "temperature" in query_lower or "ac" in query_lower:
            return await self._handle_climate_control(vehicle_id, context)
        elif "window" in query_lower:
            return await self._handle_windows_control(vehicle_id, context)
        else:
            return self._format_response(
                "I can help you control various vehicle features including lights, climate control, and windows. "
                "What would you like to adjust?",
                data=self._get_capabilities(),
            )

    def _get_capabilities(self) -> Dict[str, str]:
        """Get the capabilities of this agent."""
        return {
            "lightsControl": "Control headlights, interior lights, and hazard lights",
            "climateControl": "Adjust temperature, heating, and air conditioning",
            "windowsControl": "Open and close vehicle windows",
        }

    def _format_response(
        self, message: str, success: bool = True, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        resp = {"message": message, "success": success}
        if data:
            resp["data"] = data
        return resp


