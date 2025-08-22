from typing import Dict, Any
from fastmcp import FastMCP
import asyncio
import sys
from pathlib import Path
from utils.logging_config import get_logger  # type: ignore
from plugin.sample_data import generate_traffic  # type: ignore


logger = get_logger(__name__)
mcp_traffic_server = FastMCP("traffic_service")

@mcp_traffic_server.tool()
async def get_traffic(route: str, latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get traffic information for a given route or location.
    """
    try:
        return generate_traffic(route, latitude, longitude)
    except Exception as e:
        logger.error(f"Error retrieving traffic info: {e}")
        raise

async def start_traffic_server(host: str = "0.0.0.0", port: int = 8002):
    """
    Start the traffic MCP server.
    """
    logger.info(f"Starting Traffic MCP server on {host}:{port}")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        loop.create_task(mcp_traffic_server.run_async(transport="sse", host=host, port=port))
    else:
        await mcp_traffic_server.run_async(transport="sse", host=host, port=port)
    logger.info(f"Traffic MCP server is running on {host}:{port}")
