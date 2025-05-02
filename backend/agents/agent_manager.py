"""
Agent Manager for the Connected Car Platform.

This module manages the routing of user requests to specialized agents based on intent.
"""

import logging
import os
from typing import Dict, Any, List, Optional, Type, AsyncIterable

import semantic_kernel as sk
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    AzureChatPromptExecutionSettings
)
from semantic_kernel.functions.kernel_arguments import KernelArguments

# Import specialized agents
from agents.remote_access_agent import RemoteAccessAgent
from agents.safety_emergency_agent import SafetyEmergencyAgent
from agents.charging_energy_agent import ChargingEnergyAgent
from agents.information_services_agent import InformationServicesAgent
from agents.vehicle_feature_control_agent import VehicleFeatureControlAgent
from agents.diagnostics_battery_agent import DiagnosticsBatteryAgent
from agents.alerts_notifications_agent import AlertsNotificationsAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentManager:
    """
    AgentManager class interprets user intent and delegates tasks to specialized agents.
    """
    
    def __init__(self):
        """Initialize the AgentManager with specialized agents."""
        # Initialize specialized agents
        self.agents = {
            "remote_access": RemoteAccessAgent(),
            "safety_emergency": SafetyEmergencyAgent(),
            "charging_energy": ChargingEnergyAgent(),
            "information_services": InformationServicesAgent(),
            "vehicle_feature_control": VehicleFeatureControlAgent(),
            "diagnostics_battery": DiagnosticsBatteryAgent(),
            "alerts_notifications": AlertsNotificationsAgent(),
        }
        
        # Create a Semantic Kernel-based orchestrator agent
        self.orchestrator = self._create_orchestrator()
        
        logger.info("AgentManager initialized with specialized agents and orchestrator")
    
    def _create_orchestrator(self) -> ChatCompletionAgent:
        """Create and configure a Semantic Kernel orchestrator agent."""
        try:
            # Get Azure OpenAI credentials from environment
            deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION")
            
            # Create the orchestrator with all specialized agents as plugins
            orchestrator = ChatCompletionAgent(
                service=AzureChatCompletion(
                    deployment_name=deployment_name,
                    endpoint=endpoint,
                    api_key=api_key,
                    api_version=api_version
                ),
                name="VehicleOrchestratorAgent",
                instructions=(
                    "Your role is to analyze the user's request and route it to the appropriate specialized agent. "
                    "Here are the specialized agents available:\n"
                    "- Remote Access Agent: For controlling vehicle access including doors, engine, and data sync.\n"
                    "- Safety Emergency Agent: For handling emergencies, collisions, theft, and SOS.\n"
                    "- Charging Energy Agent: For EV charging, stations, and energy management.\n"
                    "- Information Services Agent: For weather, traffic, POIs, and navigation.\n"
                    "- Vehicle Feature Control Agent: For climate, features, and subscriptions.\n"
                    "- Diagnostics Battery Agent: For diagnostics, system health, and battery status.\n"
                    "- Alerts Notifications Agent: For alerts, speed violations, and notifications.\n\n"
                    "Analyze the request and route it to the most appropriate agent. "
                    "If you're not sure, route to Information Services Agent as the default."
                ),
                arguments=KernelArguments(
                    settings=AzureChatPromptExecutionSettings(
                        temperature=0.3,
                        max_tokens=1000
                    )
                )
            )
            
            # Add all specialized agents as plugins
            for agent_type, agent in self.agents.items():
                orchestrator.add_plugin(agent)
            
            return orchestrator
        except Exception as e:
            logger.error(f"Error creating orchestrator agent: {str(e)}")
            raise
    
    async def process_request(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user request by interpreting intent and delegating to the appropriate agent.
        
        Args:
            query: User query string
            context: Additional context for the query
            
        Returns:
            The response from the appropriate specialized agent
        """
        context = context or {}
        
        # If context already has an agent_type, use it directly
        if "agent_type" in context and context["agent_type"] in self.agents:
            agent_type = context["agent_type"]
            logger.info(f"Using specified agent type from context: {agent_type}")
            return await self.agents[agent_type].process(query, context)
        
        # Create a session ID for the thread if not provided
        session_id = context.get("session_id", "default_session")
        
        # Use simple keyword matching for now
        agent_keywords = {
            "remote_access": ["lock", "unlock", "start", "stop", "engine", "door", "sync", "personal", "data", "remote", "access"],
            "safety_emergency": ["emergency", "crash", "collision", "alert", "ecall", "theft", "safety", "accident", "sos"],
            "charging_energy": ["charge", "charging", "battery", "energy", "station", "range", "electric", "ev"],
            "information_services": ["weather", "traffic", "poi", "points of interest", "navigation", "map", "info"],
            "vehicle_feature_control": ["climate", "temperature", "ac", "heat", "subscription", "feature", "control", "settings"],
            "diagnostics_battery": ["diagnostic", "health", "system", "status", "check", "battery", "level"],
            "alerts_notifications": ["alert", "notification", "speed", "violation", "curfew", "warning"]
        }
        
        query_lower = query.lower()
        
        # Count keyword matches for each agent type
        agent_scores = {}
        for agent_type, keywords in agent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            agent_scores[agent_type] = score
        
        # Find the agent with the highest score
        if not agent_scores or max(agent_scores.values()) == 0:
            # Default to information services if no clear match
            agent_type = "information_services"
        else:
            agent_type = max(agent_scores.items(), key=lambda x: x[1])[0]
        
        logger.info(f"Routing to agent: {agent_type}")
        
        # Process the request with the identified agent
        response = await self.agents[agent_type].process(query, {**context, "session_id": session_id})
        
        # Add agent type to the response
        if "meta" not in response:
            response["meta"] = {}
        response["meta"]["agent_type"] = agent_type
        
        return response
    
    async def process_request_stream(self, query: str, context: Optional[Dict[str, Any]] = None) -> AsyncIterable[Dict[str, Any]]:
        """
        Process a user request and stream the response.
        
        Args:
            query: User query string
            context: Additional context for the query
            
        Returns:
            An async iterable of response dictionaries
        """
        context = context or {}
        
        # If context already has an agent_type, use it directly
        if "agent_type" in context and context["agent_type"] in self.agents:
            agent_type = context["agent_type"]
            logger.info(f"Using specified agent type from context for streaming: {agent_type}")
            async for response in self.agents[agent_type].process_stream(query, context):
                yield response
            return
        
        # Create a session ID for the thread if not provided
        session_id = context.get("session_id", "default_session")
        
        # Simple agent selection (same as non-streaming for now)
        agent_keywords = {
            "remote_access": ["lock", "unlock", "start", "stop", "engine", "door", "sync", "personal", "data", "remote", "access"],
            "safety_emergency": ["emergency", "crash", "collision", "alert", "ecall", "theft", "safety", "accident", "sos"],
            "charging_energy": ["charge", "charging", "battery", "energy", "station", "range", "electric", "ev"],
            "information_services": ["weather", "traffic", "poi", "points of interest", "navigation", "map", "info"],
            "vehicle_feature_control": ["climate", "temperature", "ac", "heat", "subscription", "feature", "control", "settings"],
            "diagnostics_battery": ["diagnostic", "health", "system", "status", "check", "battery", "level"],
            "alerts_notifications": ["alert", "notification", "speed", "violation", "curfew", "warning"]
        }
        
        query_lower = query.lower()
        
        # Count keyword matches for each agent type
        agent_scores = {}
        for agent_type, keywords in agent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in query_lower)
            agent_scores[agent_type] = score
        
        # Find the agent with the highest score
        if not agent_scores or max(agent_scores.values()) == 0:
            # Default to information services if no clear match
            agent_type = "information_services"
        else:
            agent_type = max(agent_scores.items(), key=lambda x: x[1])[0]
        
        logger.info(f"Routing to agent for streaming: {agent_type}")
        
        # Begin streaming responses from the selected agent
        async for response in self.agents[agent_type].process_stream(query, {**context, "session_id": session_id}):
            # Add agent type to each streamed response
            if "meta" not in response:
                response["meta"] = {}
            response["meta"]["agent_type"] = agent_type
            yield response

# Create a singleton instance of the agent manager
agent_manager = AgentManager()
