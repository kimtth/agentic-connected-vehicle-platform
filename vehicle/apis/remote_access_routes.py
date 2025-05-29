from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from pydantic import BaseModel

from agents.agent_manager import agent_manager
from utils.logging_config import get_logger
from utils.auth import get_current_user

logger = get_logger(__name__)
router = APIRouter(prefix="/api/vehicles/{vehicle_id}/remote", tags=["Remote Access"])


class DoorControlRequest(BaseModel):
    action: str  # lock, unlock


class EngineControlRequest(BaseModel):
    action: str  # start, stop


@router.post("/doors")
async def control_doors(
    vehicle_id: str,
    request: DoorControlRequest,
    user=Depends(get_current_user)
):
    """Lock or unlock vehicle doors remotely"""
    try:
        context = {
            "vehicle_id": vehicle_id,
            "user_id": user.get("sub", "unknown"),
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
    request: EngineControlRequest,
    user=Depends(get_current_user)
):
    """Start or stop vehicle engine remotely"""
    try:
        context = {
            "vehicle_id": vehicle_id,
            "user_id": user.get("sub", "unknown"),
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
    vehicle_id: str,
    user=Depends(get_current_user)
):
    """Activate horn and lights to locate vehicle"""
    try:
        context = {
            "vehicle_id": vehicle_id,
            "user_id": user.get("sub", "unknown"),
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
