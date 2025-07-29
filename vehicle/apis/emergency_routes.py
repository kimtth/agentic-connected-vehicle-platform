from fastapi import APIRouter, HTTPException
from typing import Dict, Any, Optional
from pydantic import BaseModel

from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(
    prefix="/vehicles/{vehicle_id}/emergency", 
    tags=["Emergency & Safety"]
)

# Import agent_manager locally to avoid circular import
def get_agent_manager():
    from agents.agent_manager import agent_manager
    return agent_manager

class EmergencyCallRequest(BaseModel):
    emergency_type: Optional[str] = "general"  # general, medical, fire, police


class CollisionReportRequest(BaseModel):
    severity: str = "unknown"  # minor, major, severe, unknown
    location: Optional[Dict[str, float]] = None


class TheftReportRequest(BaseModel):
    description: Optional[str] = None
    last_seen_location: Optional[Dict[str, float]] = None


@router.post("/call")
async def emergency_call(
    vehicle_id: str,
    request: EmergencyCallRequest
):
    """Initiate an emergency call"""
    try:
        agent_manager = get_agent_manager()
        context = {
            "vehicle_id": vehicle_id,
            "query": f"emergency call {request.emergency_type}",
            "session_id": f"emergency_{vehicle_id}",
            "emergency_type": request.emergency_type
        }
        
        response = await agent_manager.process_request(
            f"I need to make an emergency call for {request.emergency_type} emergency",
            context
        )
        
        if not response.get("success", False):
            raise HTTPException(status_code=400, detail=response.get("response", "Failed to initiate emergency call"))
        
        return {
            "message": response.get("response"),
            "data": response.get("data", {}),
            "plugins_used": response.get("plugins_used", [])
        }
        
    except Exception as e:
        logger.error(f"Error initiating emergency call for vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/collision")
async def report_collision(
    vehicle_id: str,
    request: CollisionReportRequest
):
    """Report a collision incident"""
    try:
        agent_manager = get_agent_manager()
        context = {
            "vehicle_id": vehicle_id,
            "query": f"collision report {request.severity}",
            "session_id": f"collision_{vehicle_id}",
            "collision_severity": request.severity,
            "collision_location": request.location
        }
        
        response = await agent_manager.process_request(
            f"I need to report a {request.severity} collision",
            context
        )
        
        if not response.get("success", False):
            raise HTTPException(status_code=400, detail=response.get("response", "Failed to report collision"))
        
        return {
            "message": response.get("response"),
            "data": response.get("data", {}),
            "plugins_used": response.get("plugins_used", [])
        }
        
    except Exception as e:
        logger.error(f"Error reporting collision for vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/theft")
async def report_theft(
    vehicle_id: str,
    request: TheftReportRequest
):
    """Report vehicle theft"""
    try:
        agent_manager = get_agent_manager()
        context = {
            "vehicle_id": vehicle_id,
            "query": f"theft report",
            "session_id": f"theft_{vehicle_id}",
            "theft_description": request.description,
            "last_location": request.last_seen_location
        }
        
        response = await agent_manager.process_request(
            f"I need to report my vehicle as stolen. {request.description or ''}",
            context
        )
        
        if not response.get("success", False):
            raise HTTPException(status_code=400, detail=response.get("response", "Failed to report theft"))
        
        return {
            "message": response.get("response"),
            "data": response.get("data", {}),
            "plugins_used": response.get("plugins_used", [])
        }
        
    except Exception as e:
        logger.error(f"Error reporting theft for vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/sos")
async def activate_sos(
    vehicle_id: str
):
    """Activate SOS emergency response"""
    try:
        agent_manager = get_agent_manager()
        context = {
            "vehicle_id": vehicle_id,
            "query": "SOS emergency",
            "session_id": f"sos_{vehicle_id}"
        }
        
        response = await agent_manager.process_request(
            "EMERGENCY SOS - I need immediate help",
            context
        )
        
        if not response.get("success", False):
            raise HTTPException(status_code=400, detail=response.get("response", "Failed to activate SOS"))
        
        return {
            "message": response.get("response"),
            "data": response.get("data", {}),
            "plugins_used": response.get("plugins_used", [])
        }
        
    except Exception as e:
        logger.error(f"Error activating SOS for vehicle {vehicle_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
