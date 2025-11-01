from typing import Dict, Any, Optional, AsyncGenerator, List
import asyncio
import json
from contextlib import asynccontextmanager
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.filters import FunctionInvocationContext
from azure.cosmos_db import get_cosmos_client

from agents.alerts_notifications_agent import AlertsNotificationsAgent
from agents.charging_energy_agent import ChargingEnergyAgent
from agents.diagnostics_battery_agent import DiagnosticsBatteryAgent
from agents.information_services_agent import InformationServicesAgent
from agents.remote_access_agent import RemoteAccessAgent
from agents.safety_emergency_agent import SafetyEmergencyAgent
from agents.vehicle_feature_control_agent import VehicleFeatureControlAgent
from plugin.oai_service import create_chat_service
from plugin.sk_plugin import GeneralPlugin
from utils.logging_config import get_logger
from utils.vehicle_object_utils import ensure_dict
from models.agent_response import (
    ParsedAgentMessage,
    AgentResponse,
    StreamingChunk,
)

logger = get_logger(__name__)


class AgentManager:
    """
    Vehicle AgentManager refactored to use Semantic Kernel style agents/plugins.
    Coordinates specialized agents for vehicle operations and provides a unified interface.
    """

    def __init__(self):
        self.cosmos_client = get_cosmos_client()
        service_factory = create_chat_service()
        self._initialize_domain_agents(service_factory)
        self._initialize_manager_agent(service_factory)
        self.thread: Optional[ChatHistoryAgentThread] = None

    def _initialize_domain_agents(self, service_factory) -> None:
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
            instructions="You handle general vehicle inquiries and provide helpful information.",
            plugins=[GeneralPlugin()],
        )

    def _initialize_manager_agent(self, service_factory) -> None:
        self.manager = ChatCompletionAgent(
            service=service_factory,
            name="VehicleManagerAgent",
            instructions=(
                "You are a vehicle management coordinator that routes requests to specialized agents. "
                "Analyze the user's request and context to determine the appropriate agent. "
                "Provide clear, helpful responses and indicate which plugins were used. "
                "Highlight keywords in the response. Be concise. "
                "Output with markdown format."
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
        )



    async def _ensure_thread(self, session_id: str) -> None:
        if not self.thread or getattr(self.thread, "_thread_id", None) != session_id:
            if self.thread:
                await self.thread.delete()
            self.thread = ChatHistoryAgentThread(thread_id=session_id)

    async def _get_vehicle_data(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        if not vehicle_id:
            return None
        await self.cosmos_client.ensure_connected()
        vehicle = await self.cosmos_client.get_vehicle(vehicle_id)
        return ensure_dict(vehicle)

    async def _enrich_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        enriched_context = context.copy()
        vehicle_id = context.get("vehicleId")
        if not vehicle_id:
            return enriched_context
        vehicle_data = await self._get_vehicle_data(vehicle_id)
        if vehicle_data:
            enriched_context["vehicleData"] = vehicle_data
            enriched_context["vehicleId"] = vehicle_id
        vehicle_status = ensure_dict(await self.cosmos_client.get_vehicle_status(vehicle_id))
        if vehicle_status:
            enriched_context["vehicleStatus"] = vehicle_status
        return enriched_context

    def _parse_response_safely(self, response_content: str, plugins_used: Optional[List[str]] = None) -> ParsedAgentMessage:
        content = response_content.content if hasattr(response_content, "content") else str(response_content)
        content = content.strip()
        if content.startswith("{") and content.endswith("}"):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return ParsedAgentMessage(
                        message=parsed.get("message") or content,
                        status=parsed.get("status") or "completed",
                        plugins_used=parsed.get("plugins_used") or [],
                        data=parsed.get("data"),
                    )
            except json.JSONDecodeError:
                pass
        return ParsedAgentMessage(
            message=content or "Command executed successfully.",
            plugins_used=[]
        )

    def _build_agent_response(
        self,
        parsed: ParsedAgentMessage,
        fallback_used: bool = False,
        error: Optional[str] = None,
    ) -> AgentResponse:
        """Convert a ParsedAgentMessage into the outward AgentResponse model."""
        return AgentResponse(
            response=parsed.message or "The command has been processed successfully.",
            success=parsed.status == "completed",
            plugins_used=parsed.plugins_used or [],
            data=parsed.data,
            fallback_used=fallback_used,
            error=error,
        )

    async def _prepare_kernel_arguments(self, enriched_context: Dict[str, Any]) -> KernelArguments:
        args = KernelArguments()
        for key in ["vehicleId", "vehicleData", "vehicleStatus", "sessionId", "agentType", "query"]:
            if key in enriched_context:
                args[key.replace("Id", "_id").replace("Data", "_data").replace("Status", "_status").replace("Type", "_type")] = enriched_context[key]
        args["call_context"] = enriched_context
        return args

    async def process_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        session_id = context.get("session_id", "default")
        context["query"] = query
        enriched_context = await self._enrich_context(context)
        await self._ensure_thread(session_id)
        kernel_args = await self._prepare_kernel_arguments(enriched_context)
        try:
            sk_response = await self.manager.get_response(
                messages=f"Query: {query}\nContext: {json.dumps(enriched_context, default=str)}",
                thread=self.thread,
                arguments=kernel_args,
            )
            parsed = self._parse_response_safely(sk_response.message)
            return self._build_agent_response(parsed).model_dump(by_alias=True)
        except Exception:
            return await self._process_with_fallback(query, enriched_context)

    async def _process_with_fallback(self, query: str, enriched_context: Dict[str, Any]) -> Dict[str, Any]:
        fallback_manager = ChatCompletionAgent(
            service=create_chat_service(),
            name="VehicleManagerFallback",
            instructions="You are a vehicle management coordinator. Analyze the user's request and provide a helpful response.",
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
        )
        kernel_args = await self._prepare_kernel_arguments(enriched_context)
        sk_response = await fallback_manager.get_response(
            messages=f"Query: {query}\nContext: {json.dumps(enriched_context, default=str)}",
            thread=self.thread,
            arguments=kernel_args,
        )
        parsed = self._parse_response_safely(sk_response.message)
        return self._build_agent_response(parsed, fallback_used=True).model_dump(by_alias=True)

    def _extract_candidate_text(self, chunk) -> str:
        """Return a single best textual candidate from a streaming chunk."""
        try:
            if chunk is None:
                return ""
            if isinstance(chunk, str):
                return chunk
            for attr in ("message", "content", "text"):
                val = getattr(chunk, attr, None)
                if isinstance(val, str):
                    return val
                if isinstance(val, (list, tuple)):
                    parts = []
                    for p in val:
                        if isinstance(p, str):
                            parts.append(p)
                        else:
                            t = getattr(p, "text", None)
                            if isinstance(t, str):
                                parts.append(t)
                            else:
                                c = getattr(p, "content", None)
                                if isinstance(c, str):
                                    parts.append(c)
                    if parts:
                        return "".join(parts)
            # Fallback (avoid noisy reprs)
            rep = str(chunk)
            if rep.startswith("<"):
                return ""
            return rep
        except Exception:
            return ""

    async def process_request_stream(self, query: str, context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        session_id = context.get("sessionId", "default")
        context["query"] = query
        enriched_context = await self._enrich_context(context)
        yield StreamingChunk(response="Processing your request...", complete=False).model_dump(by_alias=True)
        await self._ensure_thread(session_id)
        full_response = ""
        try:
            async for chunk in self.manager.invoke_stream(
                messages=f"Query: {query}\nContext: {json.dumps(enriched_context, default=str)}",
                thread=self.thread,
            ):
                candidate = self._extract_candidate_text(chunk)
                if candidate:
                    candidate = candidate.replace("\r", "")
                    full_response += candidate
                    yield StreamingChunk(response=full_response, complete=False, plugins_used=[]).model_dump(by_alias=True)
            parsed = self._parse_response_safely(full_response or "I processed your request.")
            yield StreamingChunk(response=parsed.message, complete=True, plugins_used=parsed.plugins_used or []).model_dump(by_alias=True)
        except Exception as e:
            yield StreamingChunk(response="Error processing request.", complete=True, plugins_used=[], error=str(e)).model_dump(by_alias=True)




# FastAPI scoped dependency factory
async def get_agent_manager() -> AgentManager:
    return AgentManager()
