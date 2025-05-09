"""
Azure-based agent implementation using Semantic Kernel (via SemanticKernelManager)
"""

import logging
from utils.semantic_kernel_manager import sk_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureVehicleAgent:
    """Azure-based vehicle agent using Azure OpenAI via SemanticKernelManager"""
    
    def __init__(self):
        """Initialize the Azure Vehicle Agent."""
        self.is_available = sk_manager.has_agent()
        if self.is_available:
            logger.info("Azure Vehicle Agent initialized successfully")
        else:
            logger.warning("Azure Vehicle Agent initialized in limited functionality mode")
    
    async def ask(self, query, context_vars=None):
        """
        Ask the agent a question.
        Delegates to sk_manager.ask_agent.
        """
        # Ignore context_vars since sk_manager only supports prompt
        result = await sk_manager.ask_agent(query)
        return {
            "response": result.get("response"),
            "plugins_used": []  # no plugins in this simplified model
        }

# Singleton instance
azure_vehicle_agent = AzureVehicleAgent()
