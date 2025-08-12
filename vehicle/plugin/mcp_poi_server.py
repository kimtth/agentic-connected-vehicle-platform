from typing import Dict, Any
from fastmcp import FastMCP
import asyncio
import sys
from pathlib import Path
from utils.logging_config import get_logger  # type: ignore
from plugin.sample_data import generate_pois  # type: ignore


logger = get_logger(__name__)
mcp_poi_server = FastMCP("poi_service")

@mcp_poi_server.tool()
async def find_pois(category: str, latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Find points of interest for a given category and location.
    """
    try:
        return generate_pois(category, latitude, longitude)
    except Exception as e:
        logger.error(f"Error retrieving POIs: {e}")
        raise

async def start_poi_server(host: str = "0.0.0.0", port: int = 8003):
    """
    Start the POI MCP server.
    """
    logger.info(f"Starting POI MCP server on {host}:{port}")
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        loop.create_task(mcp_poi_server.run_async(transport="sse", host=host, port=port))
    else:
        await mcp_poi_server.run_async(transport="sse", host=host, port=port)

