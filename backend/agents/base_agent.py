"""
Base Agent class for the Connected Car Platform specialized agents.
"""

import logging
import os
from typing import Dict, Any, Optional, AsyncIterable
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.agents import ChatHistoryAgentThread
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    AzureChatPromptExecutionSettings
)
from semantic_kernel.contents import (
    StreamingChatMessageContent,
    ChatMessageContent
)
from semantic_kernel.functions.kernel_arguments import KernelArguments

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseAgent:
    """
    Base class for all specialized agents in the Connected Car Platform.
    
    All specialized agents should inherit from this class and implement
    the process method.
    """
    
    def __init__(self, name: str, instructions: str = None):
        """
        Initialize the base agent with Semantic Kernel integration.
        
        Args:
            name: The name of the specialized agent
            instructions: The system prompt/instructions for the agent
        """
        self.name = name
        self.instructions = instructions or f"You are a specialized {name} that helps users with connected vehicle functionality."
        self.sk_agent = self._create_sk_agent()
        self.thread = None
        logger.info(f"Initialized {name} agent with Semantic Kernel")
    
    def _create_sk_agent(self) -> ChatCompletionAgent:
        """Create and configure a Semantic Kernel agent."""
        try:
            # Get Azure OpenAI credentials from environment
            deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION")
            
            # Create the ChatCompletionAgent
            agent = ChatCompletionAgent(
                service=AzureChatCompletion(
                    deployment_name=deployment_name,
                    endpoint=endpoint,
                    api_key=api_key,
                    api_version=api_version
                ),
                name=self.name,
                instructions=self.instructions,
                arguments=KernelArguments(
                    settings=AzureChatPromptExecutionSettings(
                        temperature=0.7,
                        max_tokens=1000
                    )
                )
            )
            
            return agent
        except Exception as e:
            logger.error(f"Error creating Semantic Kernel agent: {str(e)}")
            raise
    
    async def ensure_thread_exists(self, session_id: str) -> None:
        """Ensure the thread exists for the given session ID."""
        if self.thread is None or self.thread._thread_id != session_id:
            if self.thread:
                await self.thread.delete()
            self.thread = ChatHistoryAgentThread(thread_id=session_id)
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a user query and return a response.
        
        Args:
            query: The user's query text
            context: Additional context for processing the query
            
        Returns:
            A dictionary containing the response
        """
        # Create a session ID from context or generate a new one
        session_id = context.get("session_id", "default_session")
        
        # Ensure thread exists
        await self.ensure_thread_exists(session_id)
        
        # Process with SK agent
        response = await self.sk_agent.get_response(
            messages=query,
            thread=self.thread
        )
        
        # Convert SK response to our standard format
        return self._format_response(
            content=response.content,
            success=True
        )
    
    async def process_stream(self, query: str, context: Optional[Dict[str, Any]] = None) -> AsyncIterable[Dict[str, Any]]:
        """
        Process a user query and stream the response.
        
        Args:
            query: The user's query text
            context: Additional context for processing the query
            
        Returns:
            An async iterable of response dictionaries
        """
        # Create a session ID from context or generate a new one
        session_id = context.get("session_id", "default_session")
        
        # Ensure thread exists
        await self.ensure_thread_exists(session_id)
        
        async for response_chunk in self.sk_agent.invoke_stream(
            messages=query,
            thread=self.thread
        ):
            if isinstance(response_chunk.message, ChatMessageContent):
                yield self._format_response(
                    content=response_chunk.message.content,
                    success=True
                )
            elif isinstance(response_chunk, StreamingChatMessageContent):
                yield self._format_response(
                    content=response_chunk.content or "[Processing...]",
                    success=True,
                    streaming=True
                )
    
    def _get_agent_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this agent.
        
        Returns:
            Dictionary of agent metadata
        """
        return {
            "agent_name": self.name,
            "capabilities": self._get_capabilities()
        }
    
    def _get_capabilities(self) -> Dict[str, str]:
        """
        Get the capabilities of this agent.
        
        Returns:
            Dictionary of capability name and description
        """
        return {}
    
    def _format_response(self, content: str, success: bool = True, data: Optional[Dict[str, Any]] = None, streaming: bool = False) -> Dict[str, Any]:
        """
        Format a standard response from the agent.
        
        Args:
            content: The main response content
            success: Whether the request was successful
            data: Additional data to include in the response
            streaming: Whether this is a streaming response
            
        Returns:
            Formatted response dictionary
        """
        response = {
            "response": content,
            "success": success,
            "agent": self.name,
            "streaming": streaming
        }
        
        if data:
            response["data"] = data
            
        return response
