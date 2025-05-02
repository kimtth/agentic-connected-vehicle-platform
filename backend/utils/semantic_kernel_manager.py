"""
Semantic Kernel integration for the connected vehicle platform.
"""

import os
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion, 
    AzureChatPromptExecutionSettings
)
from semantic_kernel.functions.kernel_arguments import KernelArguments
from semantic_kernel.agents import ChatCompletionAgent, ChatHistoryAgentThread
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SemanticKernelManager:
    """Manager for Semantic Kernel integration"""
    
    def __init__(self):
        """Initialize the Semantic Kernel manager"""
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        
        # Initialize agent and thread
        self.agent = self._create_agent()
        self.thread = None
        logger.info("Semantic Kernel agent initialized successfully")
    
    def _create_agent(self):
        """Create and configure a Semantic Kernel agent"""
        try:
            # Create a ChatCompletionAgent with AzureChatCompletion service
            agent = ChatCompletionAgent(
                service=AzureChatCompletion(
                    deployment_name=self.deployment_name,
                    endpoint=self.endpoint,
                    api_key=self.api_key,
                    api_version=self.api_version
                ),
                name="VehicleAssistantAgent",
                instructions=(
                    "You are an AI assistant specialized in helping with connected vehicle operations. "
                    "Provide helpful information about vehicle status, maintenance, navigation, and other car-related queries. "
                    "You should be concise, accurate, and friendly in your responses."
                ),
                arguments=KernelArguments(
                    settings=AzureChatPromptExecutionSettings(
                        temperature=0.7,
                        max_tokens=1000
                    )
                )
            )
            
            logger.info(f"Created agent with Azure OpenAI deployment: {self.deployment_name}")
            return agent
            
        except Exception as e:
            logger.error(f"Error initializing Semantic Kernel agent: {str(e)}")
            raise
    
    async def ensure_thread_exists(self, session_id: str) -> None:
        """Ensure the thread exists for the given session ID."""
        if self.thread is None or self.thread._thread_id != session_id:
            if self.thread:
                await self.thread.delete()
            self.thread = ChatHistoryAgentThread(thread_id=session_id)
    
    async def get_response(self, user_input: str, session_id: str):
        """Get a single response from the agent"""
        try:
            await self.ensure_thread_exists(session_id)
            
            response = await self.agent.get_response(
                messages=user_input,
                thread=self.thread
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error getting response: {str(e)}")
            raise
    
    async def stream_response(self, user_input: str, session_id: str):
        """Stream a response from the agent"""
        try:
            await self.ensure_thread_exists(session_id)
            
            async for response_chunk in self.agent.invoke_stream(
                messages=user_input,
                thread=self.thread
            ):
                yield response_chunk
                
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}")
            raise

# Initialize the Semantic Kernel manager
sk_manager = SemanticKernelManager()
