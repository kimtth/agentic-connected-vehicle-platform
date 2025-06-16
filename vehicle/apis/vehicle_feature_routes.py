from fastapi import APIRouter, HTTPException
from typing import Optional
from pydantic import BaseModel

from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/vehicles/features", tags=["Vehicle Features"])


class LightsControlRequest(BaseModel):
    light_type: str = "headlights"  # headlights, interior_lights, hazard_lights
    action: str = "on"  # on, off


class ClimateControlRequest(BaseModel):
    temperature: Optional[int] = 22
    action: str = "set_temperature"  # heating, cooling, set_temperature
    auto: bool = True


class WindowsControlRequest(BaseModel):
    action: str = "up"  # up, down
    windows: str = "all"  # all, driver, passenger


# Import agent_manager locally to avoid circular import
def get_agent_manager():
    from agents.agent_manager import agent_manager
    return agent_manager


@router.post("/lights")
async def control_lights(
    vehicle_id: str,
    request: LightsControlRequest
):
    """Control vehicle lights (headlights, interior, hazard)"""
    try:
        agent_manager = get_agent_manager()
        context = {
            "vehicle_id": vehicle_id,
            "query": f"turn {request.action} {request.light_type}",
            "session_id": f"lights_{vehicle_id}"
        }
        
        response = await agent_manager.process_request(
            f"turn {request.action} the {request.light_type}",
            context
        )
        
        if not response.get("success", False):
            raise HTTPException(status_code=400, detail=response.get("response", "Failed to control lights"))
        
        return {
            "message": response.get("response"),
            "data": response.get("data", {}),
            "plugins_used": response.get("plugins_used", [])
        }
        
    except Exception as e:
        logger.error(f"Error controlling lights for vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/climate")
async def control_climate(
    vehicle_id: str,
    request: ClimateControlRequest
):
    """Control vehicle climate settings"""
    try:
        agent_manager = get_agent_manager()
        context = {
            "vehicle_id": vehicle_id,
            "query": f"set climate to {request.temperature} degrees {request.action}",
            "session_id": f"climate_{vehicle_id}"
        }
        
        response = await agent_manager.process_request(
            f"set the climate control to {request.temperature} degrees with {request.action}",
            context
        )
        
        if not response.get("success", False):
            raise HTTPException(status_code=400, detail=response.get("response", "Failed to control climate"))
        
        return {
            "message": response.get("response"),
            "data": response.get("data", {}),
            "plugins_used": response.get("plugins_used", [])
        }
        
    except Exception as e:
        logger.error(f"Error controlling climate for vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/windows")
async def control_windows(
    vehicle_id: str,
    request: WindowsControlRequest
):
    """Control vehicle windows"""
    try:
        agent_manager = get_agent_manager()
        context = {
            "vehicle_id": vehicle_id,
            "query": f"roll {request.action} {request.windows} windows",
            "session_id": f"windows_{vehicle_id}"
        }
        
        response = await agent_manager.process_request(
            f"roll {request.action} the {request.windows} windows",
            context
        )
        
        if not response.get("success", False):
            raise HTTPException(status_code=400, detail=response.get("response", "Failed to control windows"))
        
        return {
            "message": response.get("response"),
            "data": response.get("data", {}),
            "plugins_used": response.get("plugins_used", [])
        }
        
    except Exception as e:
        logger.error(f"Error controlling windows for vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status")
async def get_feature_status(
    vehicle_id: str
):
    """Get current status of vehicle features"""
    try:
        agent_manager = get_agent_manager()
        context = {
            "vehicle_id": vehicle_id,
            "session_id": f"status_{vehicle_id}"
        }
        
        response = await agent_manager.process_request(
            "show me the current status of vehicle features",
            context
        )
        
        return {
            "message": response.get("response"),
            "data": response.get("data", {}),
            "plugins_used": response.get("plugins_used", [])
        }
        
    except Exception as e:
        logger.error(f"Error getting feature status for vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
