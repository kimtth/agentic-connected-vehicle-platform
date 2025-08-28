"""
Weather MCP server implementation for the Connected Car Platform using FastMCP.

This module provides weather data through the Model Context Protocol (MCP).
"""
from typing import Dict, Any, List
from fastmcp import FastMCP
import asyncio
from utils.logging_config import get_logger  
from plugin.mcp_mock_data import generate_weather, generate_forecast  


logger = get_logger(__name__)
mcp_weather_server = FastMCP("weather_service")

@mcp_weather_server.tool()
async def get_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get weather information for a given location.
    """
    try:
        return generate_weather(latitude, longitude)
    except Exception as e:
        logger.error(f"Error retrieving weather information: {str(e)}")
        raise

@mcp_weather_server.tool()
async def get_forecast(latitude: float, longitude: float, days: int = 3) -> List[Dict[str, Any]]:
    """
    Get weather forecast for a given location.
    """
    try:
        return generate_forecast(latitude, longitude, days)
    except Exception as e:
        logger.error(f"Error retrieving weather forecast: {str(e)}")
        raise

async def start_weather_server(host: str = "0.0.0.0", port: int = 8001):
    """
    Initialize and start the weather MCP server.
    """
    logger.info(f"Starting Weather MCP server on {host}:{port}")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        logger.warning("AsyncIO loop already running – launching Weather MCP server in background")
        loop.create_task(mcp_weather_server.run_async(transport="sse", host=host, port=port))
    else:
        await mcp_weather_server.run_async(transport="sse", host=host, port=port)
    logger.info("Weather MCP server started successfully")

