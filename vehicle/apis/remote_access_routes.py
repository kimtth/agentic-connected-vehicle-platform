from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from utils.logging_config import get_logger
from models.api_responses import ActionResponse

logger = get_logger(__name__)
logger.debug("remote_access_routes module imported successfully")

router = APIRouter(
    prefix="/vehicles/{vehicle_id}/remote-access", 
    tags=["Remote Access"]
)


class DoorControlRequest(BaseModel):
    action: str  # lock, unlock


class EngineControlRequest(BaseModel):
    action: str  # start, stop


# Lazy dependency resolver to avoid circular import issues
async def _get_agent_manager():
    """Create AgentManager instance for dependency injection."""
    from agents.agent_manager import AgentManager
    return AgentManager()


@router.post("/doors", response_model=ActionResponse)
async def control_doors(
    vehicle_id: str,
    request: DoorControlRequest
    request: DoorControlRequest,
    agent_manager = Depends(_get_agent_manager)
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
        
        return ActionResponse(
            message=response.get("response"),
            data=response.get("data", {}),
            pluginsUsed=response.get("plugins_used", []),
        )
        
    except Exception as e:
        logger.error(f"Error controlling doors for vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/engine", response_model=ActionResponse)
async def control_engine(
    vehicle_id: str,
    request: EngineControlRequest
    request: EngineControlRequest,
    agent_manager = Depends(_get_agent_manager)
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
        
        return ActionResponse(
            message=response.get("response"),
            data=response.get("data", {}),
            pluginsUsed=response.get("plugins_used", []),
        )
        
    except Exception as e:
        logger.error(f"Error controlling engine for vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/locate", response_model=ActionResponse)
async def locate_vehicle(
    vehicle_id: str
    vehicle_id: str,
    agent_manager = Depends(_get_agent_manager)
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
        
        return ActionResponse(
            message=response.get("response"),
            data=response.get("data", {}),
            pluginsUsed=response.get("plugins_used", []),
        )
        
    except Exception as e:
        logger.error(f"Error locating vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
