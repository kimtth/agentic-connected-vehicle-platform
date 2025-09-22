from typing import Dict, Any, Optional, AsyncGenerator, List
import asyncio
import json
from contextlib import asynccontextmanager
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.functions.kernel_arguments import KernelArguments
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
        logger.info("Initializing Agent Manager")

        try:
            # Get the singleton cosmos client instance
            self.cosmos_client = get_cosmos_client()

            # create a single service factory
            service_factory = create_chat_service()

            # domain agents - improve initialization with error handling
            self._initialize_domain_agents(service_factory)
            self._initialize_manager_agent(service_factory)

            self.thread: Optional[ChatHistoryAgentThread] = None
            self._active_sessions = set()  # Track active sessions for cleanup
            logger.info("Agent Manager successfully initialized")

        except Exception as e:
            logger.error(f"Failed to initialize Agent Manager: {e}")
            raise

    def _initialize_domain_agents(self, service_factory) -> None:
        """Initialize all domain-specific agents."""
        try:
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
        except Exception as e:
            logger.error(f"Failed to initialize domain agents: {e}")
            raise

    def _initialize_manager_agent(self, service_factory) -> None:
        """Initialize the top-level manager agent."""
        try:
            # Create manager without response format initially to avoid schema issues
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
        except Exception as e:
            logger.error(f"Failed to initialize manager agent: {e}")
            raise

    @asynccontextmanager
    async def _managed_session(self, session_id: str):
        """Context manager for proper session lifecycle management."""
        self._active_sessions.add(session_id)
        try:
            yield
        except Exception as e:
            logger.error(f"Error in managed session {session_id}: {e}")
            raise
        finally:
            self._active_sessions.discard(session_id)
            # Cleanup any resources specific to this session
            await self._cleanup_session_resources(session_id)

    async def _cleanup_session_resources(self, session_id: str) -> None:
        """Clean up resources for a specific session."""
        try:
            # Add any session-specific cleanup logic here
            logger.debug(f"Cleaned up resources for session: {session_id}")
        except Exception as e:
            logger.warning(f"Error cleaning up session {session_id}: {e}")

    async def _ensure_thread(self, session_id: str) -> None:
        """Ensure thread exists and matches session ID."""
        try:
            if (
                not self.thread
                or getattr(self.thread, "_thread_id", None) != session_id
            ):
                if self.thread:
                    await self._cleanup_thread()
                self.thread = ChatHistoryAgentThread(thread_id=session_id)
                logger.debug(f"Created new thread for session: {session_id}")
        except Exception as e:
            logger.error(f"Error ensuring thread for session {session_id}: {e}")
            raise

    async def _cleanup_thread(self) -> None:
        """Safely cleanup existing thread."""
        try:
            if self.thread:
                await self.thread.delete()
                logger.debug("Thread cleanup completed")
        except Exception as e:
            logger.warning(f"Error during thread cleanup: {e}")

    async def _get_vehicle_data(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single vehicle data from Cosmos DB and return as camelCase dict."""
        if not vehicle_id:
            logger.warning("No vehicle_id provided")
            return None
        try:
            await self.cosmos_client.ensure_connected()
            vehicle = await self.cosmos_client.get_vehicle(vehicle_id)
            vehicle_dict = ensure_dict(vehicle)
            if not vehicle_dict:
                logger.warning(f"No vehicle found with ID: {vehicle_id}")
                return None
            return vehicle_dict
        except Exception as e:
            logger.error(f"Error retrieving vehicle data for {vehicle_id}: {e}")
            return None

    async def _enrich_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Expect camelCase only
        enriched_context = context.copy()
        vehicle_id = context.get("vehicleId")
        if not vehicle_id:
            return enriched_context
        try:
            vehicle_data = await self._get_vehicle_data(vehicle_id)
            if vehicle_data:
                enriched_context["vehicleData"] = vehicle_data
                enriched_context["vehicleId"] = vehicle_id
            vehicle_status_raw = await self.cosmos_client.get_vehicle_status(vehicle_id)
            vehicle_status = ensure_dict(vehicle_status_raw)
            if vehicle_status:
                enriched_context["vehicleStatus"] = vehicle_status
            logger.debug(f"Context enriched for vehicleId {vehicle_id}")
        except Exception as e:
            logger.error(f"Error enriching context for vehicleId {vehicle_id}: {e}")
        return enriched_context

    def _parse_response_safely(self, response_content: str) -> ParsedAgentMessage:
        """Safely parse response content into ParsedAgentMessage model."""
        try:
            if hasattr(response_content, "content"):
                content = response_content.content
            else:
                content = str(response_content)
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
                    logger.warning(
                        f"Failed to parse response as JSON: {content[:100]}..."
                    )
            if content:
                return ParsedAgentMessage(message=content)
            return ParsedAgentMessage(message="Command executed successfully.")
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return ParsedAgentMessage(
                message="I apologize, but I encountered an error processing the response.",
                status="error",
                plugins_used=[],
                data=None,
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

    async def _prepare_kernel_arguments(
        self, enriched_context: Dict[str, Any]
    ) -> KernelArguments:
        try:
            args = KernelArguments()
            if "vehicleId" in enriched_context:
                args["vehicle_id"] = enriched_context["vehicleId"]
            if "vehicleData" in enriched_context:
                args["vehicle_data"] = enriched_context["vehicleData"]
            if "vehicleStatus" in enriched_context:
                args["vehicle_status"] = enriched_context["vehicleStatus"]
            if "sessionId" in enriched_context:
                args["session_id"] = enriched_context["sessionId"]
            if "agentType" in enriched_context:
                args["agent_type"] = enriched_context["agentType"]
            if "query" in enriched_context:
                args["query"] = enriched_context["query"]
            # renamed to avoid collision with SK internal context
            args["call_context"] = enriched_context
            logger.debug(f"Prepared kernel arguments with keys: {list(args.keys())}")
            return args
        except Exception as e:
            logger.error(f"Error preparing kernel arguments: {e}")
            return KernelArguments()

    async def process_request(
        self, query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single vehicle request and return structured response (aliased dict)."""
        session_id = context.get("session_id", "default")
        async with self._managed_session(session_id):
            try:
                logger.info(f"Processing request: {query[:100]}...")
                # Attach query into context for kernel argument usage
                context["query"] = query
                enriched_context = await self._enrich_context(context)
                await self._ensure_thread(session_id)
                kernel_args = await self._prepare_kernel_arguments(enriched_context)
                sk_response = await self.manager.get_response(
                    messages=f"Query: {query}\nContext: {json.dumps(enriched_context, default=str)}",
                    thread=self.thread,
                    arguments=kernel_args,
                )
                logger.debug(f"Raw SK response: {sk_response}")
                parsed = self._parse_response_safely(sk_response.message)
                agent_resp = self._build_agent_response(parsed)
                logger.info(
                    f"Request processed successfully: {agent_resp.response[:100]}..."
                )
                return agent_resp.model_dump(by_alias=True)
            except Exception as e:
                logger.error(f"Error processing request: {e}", exc_info=True)
                try:
                    if "enriched_context" not in locals():
                        enriched_context = await self._enrich_context(context)
                    fallback_result = await self._process_with_fallback(
                        query, enriched_context
                    )
                    logger.info("Request processed successfully with fallback")
                    return fallback_result
                except Exception as fallback_error:
                    logger.error(
                        f"Fallback also failed: {fallback_error}", exc_info=True
                    )
                    failure = AgentResponse(
                        response="I apologize, but I encountered an error processing your request. Please try again.",
                        success=False,
                        plugins_used=[],
                        data=None,
                        fallback_used=False,
                        error=str(e),
                    )
                    return failure.model_dump(by_alias=True)

    async def _process_with_fallback(
        self, query: str, enriched_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process request using fallback manager without response format constraints."""
        try:
            fallback_manager = ChatCompletionAgent(
                service=create_chat_service(),
                name="VehicleManagerFallback",
                instructions=(
                    "You are a vehicle management coordinator. "
                    "Analyze the user's request and provide a helpful response. "
                    "Be concise and clear in your responses."
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
            kernel_args = await self._prepare_kernel_arguments(enriched_context)
            sk_response = await fallback_manager.get_response(
                messages=f"Query: {query}\nContext: {json.dumps(enriched_context, default=str)}",
                thread=self.thread,
                arguments=kernel_args,
            )
            parsed = self._parse_response_safely(sk_response.message)
            agent_resp = self._build_agent_response(parsed, fallback_used=True)
            return agent_resp.model_dump(by_alias=True)
        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            raise

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

    async def process_request_stream(
        self, query: str, context: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process request with streaming response (yield serialized StreamingChunk)."""
        session_id = context.get("sessionId", "default")
        async with self._managed_session(session_id):
            try:
                logger.info(f"Processing streaming request: {query[:100]}...")
                context["query"] = query
                enriched_context = await self._enrich_context(context)

                yield StreamingChunk(response="Processing your request...", complete=False).model_dump(by_alias=True)

                await self._ensure_thread(session_id)

                full_response = ""
                plugins_used = []
                async for chunk in self.manager.invoke_stream(
                    messages=f"Query: {query}\nContext: {json.dumps(enriched_context, default=str)}",
                    thread=self.thread,
                ):
                    candidate = self._extract_candidate_text(chunk)
                    if candidate is None:
                        continue
                    candidate = candidate.replace("\r", "")

                    # Extract plugins_used if present in chunk
                    if hasattr(chunk, "plugins_used"):
                        plugins_used = getattr(chunk, "plugins_used", []) or []
                    elif isinstance(chunk, dict) and "plugins_used" in chunk:
                        plugins_used = chunk.get("plugins_used") or []
                    # Always append every non-empty candidate (preserve all spaces and formatting)
                    if candidate:
                        full_response += candidate
                        yield StreamingChunk(
                            response=full_response,
                            complete=False,
                            plugins_used=plugins_used,
                        ).model_dump(by_alias=True)
                    # else skip empty

                if not full_response.strip():
                    full_response = "I processed your request."

                parsed = self._parse_response_safely(full_response)

                yield StreamingChunk(
                    response=parsed.message,
                    complete=True,
                    plugins_used=parsed.plugins_used or [],
                ).model_dump(by_alias=True)

                logger.info("Streaming request processed successfully")
            except Exception as e:
                logger.error(f"Error in streaming request: {e}", exc_info=True)
                err = StreamingChunk(
                    response="I apologize, but I encountered an error processing your request.",
                    complete=True,
                    plugins_used=[],
                    error=str(e),
                )
                yield err.model_dump(by_alias=True)

    @DeprecationWarning
    async def cleanup(self) -> None:
        """Cleanup resources when shutting down."""
        try:
            # Clean up all active sessions
            cleanup_tasks = [
                self._cleanup_session_resources(session_id)
                for session_id in list(self._active_sessions)
            ]
            if cleanup_tasks:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)

            # Clean up thread
            await self._cleanup_thread()

            # Clear active sessions
            self._active_sessions.clear()

            logger.info("Agent Manager cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# FastAPI scoped dependency factory
async def get_agent_manager() -> AgentManager:
    """
    Provides a scoped (per-request) AgentManager instance.
    Usage (FastAPI):
        @app.get("/endpoint")
        async def endpoint(agent_manager: AgentManager = Depends(get_agent_manager)):
            return await agent_manager.process_request(...)

    A new AgentManager is created per request and cleaned up automatically.
    """
    manager = AgentManager()
    try:
        return manager
    finally:
        # Note: cleanup will happen via context managers in the manager itself
        pass
