from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from semantic_kernel.agents import ChatCompletionAgent
from plugin.oai_service import create_chat_service
from utils.logging_config import get_logger

logger = get_logger(__name__)


class BasePlugin(ABC):
    """
    Base class for all agent plugins. Provides a standardized response formatter.
    """

    def _format_response(
        self, text: str, success: bool = True, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Standardize agent responses.

        Args:
            text: The human-readable response.
            success: Indicates operation success.
            data: Additional structured data to return.

        Returns:
            A dict with text, success flag, and optional data.
        """
        return {
            "text": text,
            "success": success,
            "data": data or {}
        }


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    """

    def __init__(
        self,
        name: str,
        instructions: str,
        plugin_class: type[BasePlugin]
    ):
        """
        Initialize a ChatCompletionAgent with a plugin.

        Args:
            name: Agent name.
            instructions: Prompt instructions for the LLM.
            plugin_class: A BasePlugin subclass.
        """
        service_factory = create_chat_service()
        self.agent = ChatCompletionAgent(
            service=service_factory,
            name=name,
            instructions=instructions,
            plugins=[plugin_class()],
        )

    @abstractmethod
    async def process(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Each concrete agent must implement its own processing logic.

        Args:
            query: The user's request.
            context: Optional context dict.

        Returns:
            A response dict with at least "text", "success", and optional "data".
        """
        pass

    async def run(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Executes the underlying ChatCompletionAgent.

        Args:
            query: The user's request.
            context: Optional context dict.
        """
        try:
            return await self.agent.run_async(query, context)
        except Exception as e:
            logger.error(f"Agent run error: {e}")
            return {
                "text": "An error occurred while processing your request.",
                "success": False,
                "data": {}
            }