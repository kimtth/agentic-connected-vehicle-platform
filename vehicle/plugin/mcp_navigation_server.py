from typing import Dict, Any, List
from fastmcp import FastMCP
from datetime import datetime
from utils.logging_config import get_logger
import asyncio

logger = get_logger(__name__)
mcp_navigation_server = FastMCP("navigation_service")

@mcp_navigation_server.tool()
async def get_directions(destination: str, latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Get navigation directions for a given destination and start location.
    """
    try:
        steps = [
            f"Head north for 1 km from ({latitude:.4f},{longitude:.4f})",
            "Turn right at the next intersection",
            f"Continue straight for 2 km towards {destination}",
            f"Arrive at {destination}"
        ]
        return {"destination": destination, "start": {"lat": latitude, "lon": longitude}, "steps": steps, "timestamp": datetime.utcnow().isoformat()}
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
