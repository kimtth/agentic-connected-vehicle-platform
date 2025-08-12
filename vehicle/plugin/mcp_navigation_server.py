from typing import Dict, Any
from fastmcp import FastMCP
import asyncio
import sys
from pathlib import Path
from utils.logging_config import get_logger  # type: ignore
from plugin.sample_data import generate_directions  # type: ignore


logger = get_logger(__name__)
mcp_navigation_server = FastMCP("navigation_service")

@mcp_navigation_server.tool()
async def get_directions(destination: str, latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get navigation directions for a given destination and start location.
    """
    try:
        return generate_directions(destination, latitude, longitude)
    except Exception as e:
        logger.error(f"Error retrieving directions: {e}")
        raise

async def start_navigation_server(host: str = "0.0.0.0", port: int = 8004):
    """
    Start the navigation MCP server.
    """
    logger.info(f"Starting Navigation MCP server on {host}:{port}")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        loop.create_task(mcp_navigation_server.run_async(transport="sse", host=host, port=port))
    else:
        await mcp_navigation_server.run_async(transport="sse", host=host, port=port)
