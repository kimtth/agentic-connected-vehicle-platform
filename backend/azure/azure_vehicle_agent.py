"""
Azure-based agent implementation using Semantic Kernel
"""

import os
import json
import logging
import semantic_kernel as sk
from semantic_kernel.core_plugins import TimePlugin, MathPlugin
from utils.semantic_kernel_manager import sk_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AzureVehicleAgent:
    """Azure-based vehicle agent using Semantic Kernel"""
    
    def __init__(self):
        """Initialize the Azure Vehicle Agent"""
        self.kernel = sk_manager.kernel
        
        # Register core plugins
        self._register_core_plugins()
        
        # Register custom plugins
        self._register_custom_plugins()
        
        logger.info("Azure Vehicle Agent initialized successfully")
    
    def _register_core_plugins(self):
        """Register core Semantic Kernel plugins"""
        self.kernel.import_plugin(TimePlugin(), "time")
        self.kernel.import_plugin(MathPlugin(), "math")
        logger.info("Core plugins registered")

    def _register_custom_plugins(self):
        """Register custom plugins"""
        # Implement direct plugin registration without MCP
        # You can add direct plugin implementations here
        logger.info("Custom plugins registered directly")
    
    async def ask(self, query, context_vars=None):
        """Ask the agent a question"""
        try:
            # Create a context with variables
            context = self.kernel.create_new_context()
            
            if context_vars:
                for key, value in context_vars.items():
                    context[key] = value
            
            # Create a semantic function for the query
            prompt_template = f"""
            You are an intelligent agent for a connected vehicle platform.
            Help answer questions and provide insights about vehicles, their status, services, and data.
            
            User query: {{query}}
            
            Analyze the query carefully and provide a helpful response.
            Be concise but informative in your answer.
            
            If you need to use code snippets in your response, use appropriate markdown formatting.
            """
            
            query_function = self.kernel.create_semantic_function(
                prompt_template,
                max_tokens=1500,
                temperature=0.7,
                top_p=0.8
            )
            
            # Set the query in the context
            context["query"] = query
            
            # Execute the function
            result = await query_function.invoke_async(context=context)
            
            return {
                "response": result.result,
                "plugins_used": list(self.kernel.plugins.keys())
            }
        except Exception as e:
            logger.error(f"Error in agent ask: {str(e)}")
            return {
                "response": f"I encountered an error while processing your query: {str(e)}",
                "plugins_used": []
            }

# Initialize the agent
azure_vehicle_agent = AzureVehicleAgent()
