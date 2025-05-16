"""
Semantic Kernel integration for the connected vehicle platform.
Simplified to use AzureChatCompletion directly.
"""

import os
from dotenv import load_dotenv
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.exceptions.service_exceptions import ServiceInitializationError

from utils.logging_config import get_logger
logger = get_logger(__name__)

class SemanticKernelManager:
    """
    Manages Azure OpenAI chat service for the Connected Car Platform
    """
    
    def __init__(self):
        # Config from env
        load_dotenv(override=True)

        self.api_key = os.getenv("AZURE_OPENAI_API_KEY")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        
        self.chat_service = None
        if all([self.api_key, self.endpoint, self.deployment]):
            try:
                self.chat_service = AzureChatCompletion(
                    deployment_name=self.deployment,
                    endpoint=self.endpoint,
                    api_key=self.api_key,
                    api_version=self.api_version
                )
                logger.info("Azure Chat service initialized")
            except ServiceInitializationError as e:
                logger.error(f"Failed to init AzureChatCompletion: {e}")
        else:
            missing = [k for k in (
                ("AZURE_OPENAI_API_KEY", self.api_key),
                ("AZURE_OPENAI_ENDPOINT", self.endpoint),
                ("AZURE_OPENAI_DEPLOYMENT_NAME", self.deployment)
            ) if not k[1]]
            logger.warning(f"Missing Azure OpenAI config: {', '.join(m[0] for m in missing)}")
    
    def has_agent(self) -> bool:
        return self.chat_service is not None
    
    async def ask_agent(self, prompt: str):
        """
        Ask a question via Azure OpenAI chat endpoint.
        Returns dict with 'response' and optional 'error'.
        """
        if not self.has_agent():
            return {
                "response": "AI agent unavailable. Check Azure OpenAI configuration.",
                "error": "Service not initialized"
            }
        try:
            result = await self.chat_service.complete_chat(
                messages=[
                    {"role": "system", "content": "You are an AI assistant for a connected vehicle platform. Be concise and helpful."},
                    {"role": "user", "content": prompt}
                ]
            )
            # Extract content from first choice
            choice = next(iter(result.choices or []), None)
            content = choice.message.content if choice and hasattr(choice, "message") else str(result)
            return {"response": content, "error": None}
        except Exception as e:
            logger.error(f"Error during chat completion: {e}")
            return {"response": "Error processing request.", "error": str(e)}

# Singleton instance
sk_manager = SemanticKernelManager()
