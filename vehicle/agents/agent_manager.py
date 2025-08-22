from typing import Dict, Any, Optional, AsyncGenerator, List
import asyncio
import json
from contextlib import asynccontextmanager
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import OpenAIChatPromptExecutionSettings
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
                    "Format your response as JSON with the following structure: "
                    '{"message": "your response", "status": "completed", "plugins_used": ["plugin1", "plugin2"]}'
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
            await self.cosmos_client.ensure_connected()
            vehicles = await self.cosmos_client.list_vehicles()
            
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
        # support both keys from frontend payload
        vehicle_id = context.get("vehicle_id") or context.get("vehicleId")

        if not vehicle_id:
            return enriched_context
            
        try:
            # Get vehicle data
            vehicle_data = await self._get_vehicle_data(vehicle_id)
            if vehicle_data:
                enriched_context["vehicle_data"] = vehicle_data
                # ensure a single, unified key
                enriched_context["vehicle_id"] = vehicle_id
                
            # Get vehicle status
            vehicle_status = await self.cosmos_client.get_vehicle_status(vehicle_id)
            if vehicle_status:
                enriched_context["vehicle_status"] = vehicle_status
                
            logger.debug(f"Context enriched for vehicle {vehicle_id}")
            
        except Exception as e:
            logger.error(f"Error enriching context for vehicle {vehicle_id}: {e}")
            
        return enriched_context

    def _parse_response_safely(self, response_content: str) -> Dict[str, Any]:
        """Safely parse response content into the expected format."""
        try:
            # Handle ChatMessageContent objects
            if hasattr(response_content, 'content'):
                content = response_content.content
            else:
                content = str(response_content)
                
            # Clean up the content
            content = content.strip()
            
            # Try to parse as JSON first
            if content.startswith('{') and content.endswith('}'):
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict):
                        # Validate required fields and provide defaults
                        return {
                            "message": parsed.get("message", content),
                            "status": parsed.get("status", "completed"),
                            "plugins_used": parsed.get("plugins_used", []),
                            "data": parsed.get("data")
                        }
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse response as JSON: {content[:100]}...")
            
            # Fallback to plain text response - ensure we have a message
            if content:
                return {
                    "message": content,
                    "status": "completed",
                    "plugins_used": [],
                    "data": None
                }
            else:
                return {
                    "message": "Command executed successfully.",
                    "status": "completed", 
                    "plugins_used": [],
                    "data": None
                }
            
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return {
                "message": "I apologize, but I encountered an error processing the response.",
                "status": "error",
                "plugins_used": [],
                "data": None
            }

    async def _prepare_kernel_arguments(self, enriched_context: Dict[str, Any]) -> KernelArguments:
        """Prepare kernel arguments with proper vehicle context."""
        try:
            # Create kernel arguments with vehicle context
            arguments = KernelArguments()
            
            # Add vehicle_id to arguments for function calls
            vehicle_id = enriched_context.get("vehicle_id")
            if vehicle_id:
                arguments["vehicle_id"] = vehicle_id
                
            # Add other context data
            for key, value in enriched_context.items():
                if key not in ["vehicle_id"]:  # Don't duplicate vehicle_id
                    arguments[key] = value
                    
            return arguments
        except Exception as e:
            logger.error(f"Error preparing kernel arguments: {e}")
            return KernelArguments()

    async def process_request(
        self, query: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a single vehicle request and return structured response."""
        session_id = context.get("session_id", "default")
        
        async with self._managed_session(session_id):
            try:
                logger.info(f"Processing request: {query[:100]}...")
                
                # Enrich context with vehicle data
                enriched_context = await self._enrich_context(context)
                
                # Ensure thread exists
                await self._ensure_thread(session_id)
                
                # Prepare kernel arguments with vehicle context
                kernel_args = await self._prepare_kernel_arguments(enriched_context)
                
                # Get response using the manager agent with proper arguments
                sk_response = await self.manager.get_response(
                    messages=f"Query: {query}\nContext: {json.dumps(enriched_context, default=str)}", 
                    thread=self.thread,
                    arguments=kernel_args
                )
                
                # Log the raw response for debugging
                logger.debug(f"Raw SK response: {sk_response}")
                
                # Parse response safely
                parsed_response = self._parse_response_safely(sk_response.message)
                
                # Ensure we have a valid message
                if not parsed_response.get("message"):
                    parsed_response["message"] = "The command has been processed successfully."
                
                result = {
                    "response": parsed_response["message"],
                    "success": parsed_response["status"] == "completed",
                    "plugins_used": parsed_response["plugins_used"],
                }
                
                if parsed_response.get("data"):
                    result["data"] = parsed_response["data"]
                    
                logger.info(f"Request processed successfully: {result.get('response', '')[:100]}...")
                return result
                
            except Exception as e:
                logger.error(f"Error processing request: {e}", exc_info=True)
                
                # Ensure enriched_context is available for fallback
                try:
                    if 'enriched_context' not in locals():
                        enriched_context = await self._enrich_context(context)
                    
                    fallback_result = await self._process_with_fallback(query, enriched_context)
                    logger.info("Request processed successfully with fallback")
                    return fallback_result
                except Exception as fallback_error:
                    logger.error(f"Fallback also failed: {fallback_error}", exc_info=True)
                    return {
                        "response": "I apologize, but I encountered an error processing your request. Please try again.",
                        "success": False,
                        "plugins_used": [],
                        "error": str(e)
                    }

    async def _process_with_fallback(self, query: str, enriched_context: Dict[str, Any]) -> Dict[str, Any]:
        """Process request using fallback manager without response format constraints."""
        try:
            # Create a simple fallback manager without structured response format
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
            
            # Prepare kernel arguments for fallback
            kernel_args = await self._prepare_kernel_arguments(enriched_context)
            
            # Get response without structured format
            sk_response = await fallback_manager.get_response(
                messages=f"Query: {query}\nContext: {json.dumps(enriched_context, default=str)}", 
                thread=self.thread,
                arguments=kernel_args
            )
            
            # Parse response content safely
            parsed_response = self._parse_response_safely(sk_response.message)
            
            return {
                "response": parsed_response["message"],
                "success": True,
                "plugins_used": parsed_response["plugins_used"],
                "data": parsed_response.get("data"),
                "fallback_used": True
            }
            
        except Exception as e:
            logger.error(f"Fallback processing failed: {e}")
            raise

    async def process_request_stream(
        self, query: str, context: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process request with streaming response."""
        session_id = context.get("session_id", "default")
        
        async with self._managed_session(session_id):
            try:
                logger.info(f"Processing streaming request: {query[:100]}...")
                
                # Enrich context
                enriched_context = await self._enrich_context(context)
                
                # Send initial response
                yield {"response": "Processing your request...", "complete": False}

                # Ensure thread exists
                await self._ensure_thread(session_id)
                
                # Collect streaming chunks
                chunks: List[Any] = []
                async for chunk in self.manager.invoke_stream(
                    messages=f"Query: {query}\nContext: {json.dumps(enriched_context, default=str)}", 
                    thread=self.thread
                ):
                    chunks.append(chunk)

                if not chunks:
                    yield {"response": "No response received", "complete": True, "plugins_used": []}
                    return

                # Parse final response safely
                final_content = chunks[-1].message if hasattr(chunks[-1], 'message') else str(chunks[-1])
                parsed_response = self._parse_response_safely(final_content)

                # Stream response sentence by sentence
                sentences = parsed_response["message"].split(". ")
                for i, sentence in enumerate(sentences):
                    if i < len(sentences) - 1:
                        sentence += "."
                    
                    is_last = i == len(sentences) - 1
                    yield {
                        "response": sentence,
                        "complete": is_last,
                        "plugins_used": parsed_response["plugins_used"] if is_last else [],
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


# singleton
agent_manager = AgentManager()
