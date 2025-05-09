"""
Agent helper module for the Azure-based connected vehicle platform.
This file serves as a bridge between the original implementation and the Azure-based implementation.
It redirects agent calls to the Azure Vehicle Agent using Semantic Kernel.
"""

import os
import logging
from azure.azure_vehicle_agent import azure_vehicle_agent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check if Azure is enabled
AZURE_ENABLED = os.getenv("AZURE_ENABLED", "false").lower() == "true"

# Wrapper functions for backward compatibility
async def create_profile_manager_agent():
    """
    For backward compatibility - redirects to Azure Vehicle Agent
    """
    logger.info("Using Azure Vehicle Agent for profile management")
    return azure_vehicle_agent

async def create_service_manager_agent():
    """
    For backward compatibility - redirects to Azure Vehicle Agent
    """
    logger.info("Using Azure Vehicle Agent for service management")
    return azure_vehicle_agent

async def create_api_executor_agent():
    """
    For backward compatibility - redirects to Azure Vehicle Agent
    """
    logger.info("Using Azure Vehicle Agent for API execution")
    return azure_vehicle_agent

async def create_data_manager_agent():
    """
    For backward compatibility - redirects to Azure Vehicle Agent
    """
    logger.info("Using Azure Vehicle Agent for data management")
    return azure_vehicle_agent

async def create_notification_handler_agent():
    """
    For backward compatibility - redirects to Azure Vehicle Agent
    """
    logger.info("Using Azure Vehicle Agent for notification handling")
    return azure_vehicle_agent
