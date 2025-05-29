from typing import Dict, Any, Optional, AsyncGenerator, List
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
    Coordinates specialized agents for vehicle operations and provides a unified interface.
    """

    def __init__(self):
        logger.info("Initializing Agent Manager")

        try:
            # create a single service factory
            service_factory = create_chat_service()

            # domain agents - improve initialization with error handling
            self._initialize_domain_agents(service_factory)
            self._initialize_manager_agent(service_factory)
            
            self.thread: Optional[ChatHistoryAgentThread] = None
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
            self.manager = ChatCompletionAgent(
                service=service_factory,
                name="VehicleManagerAgent",
                instructions=(
                    "You are a vehicle management coordinator that routes requests to specialized agents. "
                    "Analyze the user's request and context to determine the appropriate agent. "
                    "Always return responses in JSON format matching VehicleResponseFormat. "
                    "Provide clear, helpful responses and indicate which plugins were used."
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
        except Exception as e:
            logger.error(f"Failed to initialize manager agent: {e}")
            raise

    async def _ensure_thread(self, session_id: str) -> None:
        """Ensure thread exists and matches session ID."""
        try:
            if not self.thread or getattr(self.thread, '_thread_id', None) != session_id:
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
        """Retrieve vehicle data from Cosmos DB with improved error handling."""
        if not vehicle_id:
            logger.warning("No vehicle ID provided")
            return None
            
        try:
            logger.debug(f"Fetching vehicle data for ID: {vehicle_id}")
            vehicles = await cosmos_client.list_vehicles()
            
            # Handle both vehicleId and VehicleId field names for backward compatibility
            vehicle_data = next((v for v in vehicles if 
                               v.get("vehicleId") == vehicle_id or 
                               v.get("VehicleId") == vehicle_id), None)
            
            if vehicle_data:
                logger.debug(f"Found vehicle data for ID: {vehicle_id}")
            else:
                logger.warning(f"No vehicle found with ID: {vehicle_id}")
                
            return vehicle_data
            
        except Exception as e:
            logger.error(f"Error retrieving vehicle data for {vehicle_id}: {e}")
            return None

    async def _enrich_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich context with vehicle data and status."""
        enriched_context = context.copy()
        vehicle_id = context.get("vehicle_id")
        
        if not vehicle_id:
            return enriched_context
            
        try:
            # Get vehicle data
            vehicle_data = await self._get_vehicle_data(vehicle_id)
            if vehicle_data:
                enriched_context["vehicle_data"] = vehicle_data
                
            # Get vehicle status
            vehicle_status = await cosmos_client.get_vehicle_status(vehicle_id)
            if vehicle_status:
                enriched_context["vehicle_status"] = vehicle_status
                
            logger.debug(f"Context enriched for vehicle {vehicle_id}")
            
        except Exception as e:
            logger.error(f"Error enriching context for vehicle {vehicle_id}: {e}")
            
        return enriched_context

    async def process_request(
        self, query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single vehicle request and return structured response."""
        try:
            logger.info(f"Processing request: {query[:100]}...")
            
            # Enrich context with vehicle data
            enriched_context = await self._enrich_context(context)
            
            # Ensure thread exists
            session_id = context.get("session_id", "default")
            await self._ensure_thread(session_id)
            
            # Get response from manager agent
            sk_response = await self.manager.get_response(
                messages={"query": query, **enriched_context}, 
                thread=self.thread
            )
            
            # Parse and validate response
            response_data = VehicleResponseFormat.model_validate_json(sk_response.content)
            
            result = {
                "response": response_data.message,
                "success": response_data.status == "completed",
                "plugins_used": response_data.plugins_used or [],
            }
            
            if response_data.data:
                result["data"] = response_data.data
                
            logger.info("Request processed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {
                "response": "I apologize, but I encountered an error processing your request. Please try again.",
                "success": False,
                "plugins_used": [],
                "error": str(e)
            }

    async def process_request_stream(
        self, query: str, context: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process request with streaming response."""
        try:
            logger.info(f"Processing streaming request: {query[:100]}...")
            
            # Enrich context
            enriched_context = await self._enrich_context(context)
            
            # Send initial response
            yield {"response": "Processing your request...", "complete": False}

            # Ensure thread exists
            session_id = context.get("session_id", "default")
            await self._ensure_thread(session_id)
            
            # Collect streaming chunks
            chunks: List[Any] = []
            async for chunk in self.manager.invoke_stream(
                messages={"query": query, **enriched_context}, 
                thread=self.thread
            ):
                chunks.append(chunk)

            if not chunks:
                yield {"response": "No response received", "complete": True, "plugins_used": []}
                return

            # Parse final response
            final_response = VehicleResponseFormat.model_validate_json(chunks[-1].content)

            # Stream response sentence by sentence
            sentences = final_response.message.split(". ")
            for i, sentence in enumerate(sentences):
                if i < len(sentences) - 1:
                    sentence += "."
                
                is_last = i == len(sentences) - 1
                yield {
                    "response": sentence,
                    "complete": is_last,
                    "plugins_used": final_response.plugins_used if is_last else [],
                }
                
            logger.info("Streaming request processed successfully")
            
        except Exception as e:
            logger.error(f"Error in streaming request: {e}")
            yield {
                "response": "I apologize, but I encountered an error processing your request.",
                "complete": True,
                "plugins_used": [],
                "error": str(e)
            }

    async def cleanup(self) -> None:
        """Cleanup resources when shutting down."""
        try:
            await self._cleanup_thread()
            logger.info("Agent Manager cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# singleton
agent_manager = AgentManager()
