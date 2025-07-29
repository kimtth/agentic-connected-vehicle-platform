"""
Weather MCP server implementation for the Connected Car Platform using FastMCP.

This module provides weather data through the Model Context Protocol (MCP).
"""
from typing import Dict, Any, List
from fastmcp import FastMCP

# Configure logging
from utils.logging_config import get_logger
import asyncio
logger = get_logger(__name__)

# Create an MCP server
mcp_weather_server = FastMCP("weather_service")

@mcp_weather_server.tool()
async def get_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get weather information for a given location.
    
    Args:
        latitude: The latitude coordinate of the location
        longitude: The longitude coordinate of the location
        
    Returns:
        Weather data for the location
    """
    try:
        # In a production environment, this would call an external weather API
        # TODO: Replace with actual weather API call, for example:
        # async with aiohttp.ClientSession() as session:
        #     async with session.get(f"https://weather-api.example.com/current?lat={latitude}&lon={longitude}") as response:
        #         weather_data = await response.json()
        
        # For now, we'll use a simplified formula similar to the original code
        condition = "Sunny" if (latitude + longitude) % 3 == 0 else \
                    "Cloudy" if (latitude + longitude) % 3 == 1 else "Partly Cloudy"
        temperature = int(((latitude + 90) / 180) * 30 + 5)  # Simple formula to generate temperature between 5-35°C
        
        weather_data = {
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "current": {
                "temperature": temperature,
                "condition": condition,
                "humidity": 65,
                "wind_speed": 12
            },
            "forecast": [
                {"day": "Today", "condition": condition, "high": temperature, "low": temperature - 5},
                {"day": "Tomorrow", "condition": "Partly Cloudy", "high": temperature + 2, "low": temperature - 3},
                {"day": "Day After", "condition": "Sunny", "high": temperature + 1, "low": temperature - 4}
            ]
        }
        
        return weather_data
    except Exception as e:
        logger.error(f"Error retrieving weather information: {str(e)}")
        raise

@mcp_weather_server.tool()
async def get_forecast(latitude: float, longitude: float, days: int = 3) -> List[Dict[str, Any]]:
    """
    Get weather forecast for a given location.
    
    Args:
        latitude: The latitude coordinate of the location
        longitude: The longitude coordinate of the location
        days: Number of days to forecast (default: 3)
        
    Returns:
        List of forecast data for each day
    """
    try:
        # Call get_weather to get base weather data and extract the forecast
        weather_data = await get_weather(latitude, longitude)
        
        # Return the forecast part
        return weather_data["forecast"][:days]
    except Exception as e:
        logger.error(f"Error retrieving weather forecast: {str(e)}")
        raise

async def start_weather_server(host: str = "0.0.0.0", port: int = 8001):
    """
    Initialize and start the weather MCP server.
    
    Args:
        host: Host address to bind the server to
        port: Port to listen on
        
    Returns:
        None
    """
    logger.info(f"Starting Weather MCP server on {host}:{port}")
    # If an event-loop is already running, run the server as a background task
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        logger.warning("AsyncIO loop already running – launching Weather MCP server in background")
        # Run the server in the background using the async variant to avoid nesting event loops
        # Use SSE transport so host and port are accepted by FastMCP
        loop.create_task(mcp_weather_server.run_async(transport="sse", host=host, port=port))
    else:
        # Use SSE transport so host and port are accepted by FastMCP
        await mcp_weather_server.run_async(transport="sse", host=host, port=port)
        await mcp_weather_server.run_async(host=host, port=port)
    logger.info("Weather MCP server started successfully")
    
def get_server_instance():
    """
    Get the MCP server instance for direct access.
    
    Returns:
        The Server instance
    """
    return mcp_weather_server
