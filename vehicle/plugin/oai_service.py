import os
from typing import Any
from semantic_kernel.connectors.ai.open_ai import (
    AzureChatCompletion,
    OpenAIChatCompletion,
)


def create_chat_service() -> Any:
    """
    Factory: prefer Azure OpenAI if AZURE_OPENAI_API_KEY is set; otherwise use OpenAI.
    """
    azure_key = os.getenv("AZURE_OPENAI_API_KEY")
    if azure_key:
        return AzureChatCompletion(
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            api_key=azure_key,
            endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
            service_id="azure_openai",
        )
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        raise ValueError("No API key found for OpenAI or Azure OpenAI")
    return OpenAIChatCompletion(
        api_key=openai_key,
        ai_model_id=os.getenv("OPENAI_CHAT_MODEL_NAME"),
        service_id="openai",
    )

