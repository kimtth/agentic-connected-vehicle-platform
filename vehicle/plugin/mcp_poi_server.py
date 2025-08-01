from typing import Dict, Any, List
from fastmcp import FastMCP
from datetime import datetime
from utils.logging_config import get_logger
import asyncio

logger = get_logger(__name__)
mcp_poi_server = FastMCP("poi_service")

@mcp_poi_server.tool()
async def find_pois(category: str, latitude: float, longitude: float) -> List[Dict[str, Any]]:
    """
    Find points of interest for a given category and location.
    """
    try:
        sample = [
            {"name": f"{category.title()} Spot A", "distance_km": 1.2},
            {"name": f"{category.title()} Spot B", "distance_km": 2.5},
            {"name": f"{category.title()} Spot C", "distance_km": 3.1}
        ]
        return {"category": category, "location": {"lat": latitude, "lon": longitude}, "results": sample, "timestamp": datetime.utcnow().isoformat()}
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
