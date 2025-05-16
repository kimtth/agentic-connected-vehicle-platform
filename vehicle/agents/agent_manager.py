from typing import Dict, Any, Optional, AsyncGenerator
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import (
    OpenAIChatPromptExecutionSettings,
)
from semantic_kernel.functions.kernel_arguments import KernelArguments
from azure.cosmos_db import cosmos_client

from agents.alerts_notifications_agent import AlertsNotificationsAgent
from agents.charging_energy_agent import ChargingEnergyAgent
from agents.diagnostics_battery_agent import DiagnosticsBatteryAgent
from agents.information_services_agent import InformationServicesAgent
from agents.remote_access_agent import RemoteAccessAgent
from agents.safety_emergency_agent import SafetyEmergencyAgent
from agents.vehicle_feature_control_agent import VehicleFeatureControlAgent
from models.vehicle_response import VehicleResponseFormat
from plugin.oai_service import create_chat_service
from plugin.sk_plugin import GeneralPlugin
from utils.logging_config import get_logger

logger = get_logger(__name__)


class AgentManager:
    """
    Vehicle AgentManager refactored to use Semantic Kernel style agents/plugins.
    """

    def __init__(self):
        logger.info("Agent Manager initialized")

        # create a single service factory
        service_factory = create_chat_service()

        # domain agents
        self.remote_access_agent = RemoteAccessAgent().agent
        self.safety_agent = SafetyEmergencyAgent().agent
        self.charging_agent = ChargingEnergyAgent().agent
        self.info_services_agent = InformationServicesAgent().agent
        self.feature_control_agent = VehicleFeatureControlAgent().agent
        self.diagnostics_agent = DiagnosticsBatteryAgent().agent
        self.alerts_agent = AlertsNotificationsAgent().agent
        self.general_agent = ChatCompletionAgent(
            service=service_factory,
            name="GeneralAgent",
            instructions="You handle general vehicle inquiries.",
            plugins=[GeneralPlugin()],
        )

        # top-level manager agent
        self.manager = ChatCompletionAgent(
            service=service_factory,
            name="VehicleManagerAgent",
            instructions=(
                "You coordinate across specialized agents. "
                "Based on the user's request and context, invoke the right plugin. "
                "Return JSON matching VehicleResponseFormat."
            ),
            plugins=[
                self.remote_access_agent,
                self.safety_agent,
                self.charging_agent,
                self.info_services_agent,
                self.feature_control_agent,
                self.diagnostics_agent,
                self.alerts_agent,
                self.general_agent,
            ],
            arguments=KernelArguments(
                settings=OpenAIChatPromptExecutionSettings(
                    response_format=VehicleResponseFormat
                )
            ),
        )
        self.thread: Optional[ChatHistoryAgentThread] = None

    async def _ensure_thread(self, session_id: str):
        if not self.thread or self.thread._thread_id != session_id:
            if self.thread:
                await self.thread.delete()
            self.thread = ChatHistoryAgentThread(thread_id=session_id)

    async def _get_vehicle_data(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        try:
            vehicles = await cosmos_client.list_vehicles()
            return next((v for v in vehicles if v.get("VehicleId") == vehicle_id), None)
        except Exception as e:
            logger.error(f"Error getting vehicle data: {e!s}")
            return None

    async def process_request(
        self, query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        # enrich context
        vid = context.get("vehicle_id")
        if vid:
            try:
                vdata = await self._get_vehicle_data(vid)
                if vdata:
                    context["vehicle_data"] = vdata
                vstatus = await cosmos_client.get_vehicle_status(vid)
                if vstatus:
                    context["vehicle_status"] = vstatus
            except Exception as e:
                logger.error(f"Error enriching context: {e!s}")

        await self._ensure_thread(context.get("session_id", "default"))
        sk_resp = await self.manager.get_response(
            messages={"query": query, **context}, thread=self.thread
        )
        resp = VehicleResponseFormat.model_validate_json(sk_resp.content)
        return {
            "response": resp.message,
            "success": resp.status == "completed",
            "plugins_used": resp.plugins_used,
            **({"data": resp.data} if resp.data else {}),
        }

    async def process_request_stream(
        self, query: str, context: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        vid = context.get("vehicle_id")
        if vid:
            try:
                context["vehicle_data"] = await self._get_vehicle_data(vid)
                context["vehicle_status"] = await cosmos_client.get_vehicle_status(vid)
            except Exception:
                pass

        yield {"response": "Processing your request...", "complete": False}

        await self._ensure_thread(context.get("session_id", "default"))
        chunks = []
        async for c in self.manager.invoke_stream(
            messages={"query": query, **context}, thread=self.thread
        ):
            chunks.append(c)
        final = VehicleResponseFormat.model_validate_json(chunks[-1].content)

        sentences = final.message.split(". ")
        for i, s in enumerate(sentences):
            if i < len(sentences) - 1:
                s += "."
            yield {
                "response": s,
                "complete": i == len(sentences) - 1,
                "plugins_used": final.plugins_used if i == len(sentences) - 1 else [],
            }


# singleton
agent_manager = AgentManager()
