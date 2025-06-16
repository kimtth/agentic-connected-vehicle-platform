from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/vehicles/{vehicle_id}/remote-access", tags=["Remote Access"])


class DoorControlRequest(BaseModel):
    action: str  # lock, unlock


class EngineControlRequest(BaseModel):
    action: str  # start, stop


# Import agent_manager locally to avoid circular import
def get_agent_manager():
    from agents.agent_manager import agent_manager
    return agent_manager


@router.post("/doors")
async def control_doors(
    vehicle_id: str,
    request: DoorControlRequest
):
    """Lock or unlock vehicle doors remotely"""
    try:
        agent_manager = get_agent_manager()
        context = {
            "vehicle_id": vehicle_id,
            "query": f"{request.action} doors",
            "session_id": f"doors_{vehicle_id}"
        }
        
        response = await agent_manager.process_request(
            f"{request.action} the vehicle doors",
            context
        )
        
        if not response.get("success", False):
            raise HTTPException(status_code=400, detail=response.get("response", "Failed to control doors"))
        
        return {
            "message": response.get("response"),
            "data": response.get("data", {}),
            "plugins_used": response.get("plugins_used", [])
        }
        
    except Exception as e:
        logger.error(f"Error controlling doors for vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/engine")
async def control_engine(
    vehicle_id: str,
    request: EngineControlRequest
):
    """Start or stop vehicle engine remotely"""
    try:
        agent_manager = get_agent_manager()
        context = {
            "vehicle_id": vehicle_id,
            "query": f"{request.action} engine",
            "session_id": f"engine_{vehicle_id}"
        }
        
        response = await agent_manager.process_request(
            f"{request.action} the vehicle engine",
            context
        )
        
        if not response.get("success", False):
            raise HTTPException(status_code=400, detail=response.get("response", "Failed to control engine"))
        
        return {
            "message": response.get("response"),
            "data": response.get("data", {}),
            "plugins_used": response.get("plugins_used", [])
        }
        
    except Exception as e:
        logger.error(f"Error controlling engine for vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/locate")
async def locate_vehicle(
    vehicle_id: str
):
    """Activate horn and lights to locate vehicle"""
    try:
        agent_manager = get_agent_manager()
        context = {
            "vehicle_id": vehicle_id,
            "query": "locate vehicle",
            "session_id": f"locate_{vehicle_id}"
        }
        
        response = await agent_manager.process_request(
            "activate horn and lights to help me find my vehicle",
            context
        )
        
        if not response.get("success", False):
            raise HTTPException(status_code=400, detail=response.get("response", "Failed to locate vehicle"))
        
        return {
            "message": response.get("response"),
            "data": response.get("data", {}),
            "plugins_used": response.get("plugins_used", [])
        }
        
    except Exception as e:
        logger.error(f"Error locating vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
