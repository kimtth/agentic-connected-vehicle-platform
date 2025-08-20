"""
Endpoints for interacting with the agentic components of the connected vehicle platform.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uuid
import logging
import json

# Add this local import function to defer import:
def get_agent_manager():
    from agents.agent_manager import agent_manager
    return agent_manager

from utils.agent_tools import (
    search_vehicle_database,
    recommend_services,
    validate_command,
    analyze_vehicle_data,
    format_notification
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/agent",
    tags=["Agents"], # Using "Agents" as a tag example
)

# Define request models
class AgentQueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    stream: Optional[bool] = False

class AnalysisRequest(BaseModel):
    vehicle_id: str
    time_period: Optional[str] = "7d"
    metrics: Optional[List[str]] = None

class ServiceRecommendationRequest(BaseModel):
    vehicle_id: str
    mileage: Optional[int] = None
    last_service_date: Optional[str] = None

# Define tool handlers (kept for backward compatibility)
tool_handlers = {
    "search_vehicle_database": search_vehicle_database,
    "recommend_services": recommend_services,
    "validate_command": validate_command,
    "analyze_vehicle_data": analyze_vehicle_data,
    "format_notification": format_notification
}

# Agent system entry point with streaming support
@router.post("/ask")
async def ask_agent(request: AgentQueryRequest):
    """General agent system entry point to ask any question, with optional streaming"""
    try:
        # Ensure we have a session ID
        session_id = request.session_id or str(uuid.uuid4())
        context = request.context or {}
        context["session_id"] = session_id
        
        # Handle agent-specific routing based on context
        agent_type = context.get("agentType") or context.get("agent_type")
        if agent_type:
            # Map frontend agent types to backend agent types
            agent_type_mapping = {
                "remote-access": "remote_access",
                "safety-emergency": "safety_emergency", 
                "charging-energy": "charging_energy",
                "information-services": "information_services",
                "feature-control": "vehicle_feature_control",
                "diagnostics-battery": "diagnostics_battery",
                "alerts-notifications": "alerts_notifications"
            }
            
            # Convert frontend agent type to backend agent type
            mapped_agent_type = agent_type_mapping.get(agent_type, agent_type)
            context["agent_type"] = mapped_agent_type
            
            logger.info(f"Routing request to agent type: {mapped_agent_type}")
        
        # Handle streaming if requested
        if request.stream:
            async def stream_generator():
                try:
                    agent_manager = get_agent_manager()
                    async for chunk in agent_manager.process_request_stream(request.query, context):
                        yield f"data: {json.dumps(chunk)}\n\n"
                except Exception as e:
                    logger.error(f"Error in streaming response: {str(e)}")
                    error_chunk = {
                        "error": "Agent service temporarily unavailable",
                        "message": "Please try again later",
                        "session_id": session_id
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                
            return StreamingResponse(
                stream_generator(), 
                media_type="text/event-stream"
            )
        else:
            # Regular non-streaming response
            try:
                agent_manager = get_agent_manager()
                response = await agent_manager.process_request(request.query, context)
                response["session_id"] = session_id
                
                # Ensure response has expected structure
                if "response" not in response:
                    response["response"] = "Request processed successfully"
                if "success" not in response:
                    response["success"] = True
                    
                return response
            except Exception as e:
                logger.error(f"Error in agent processing: {str(e)}")
                # Return a fallback response instead of failing
                return {
                    "response": "I apologize, but I'm experiencing technical difficulties at the moment. Please try again later or contact support if the issue persists.",
                    "success": False,
                    "error": "Agent service temporarily unavailable",
                    "session_id": session_id,
                    "plugins_used": [],
                    "execution_time": 0
                }
            
    except Exception as e:
        logger.error(f"Error in agent ask: {str(e)}")
        raise HTTPException(status_code=503, detail="Agent service temporarily unavailable")

# Direct access to specialized agents
@router.post("/remote-access")
async def query_remote_access(request: AgentQueryRequest):
    """Query the Remote Access Agent directly"""
    try:
        # Set context for the specific agent type
        context = request.context or {}
        context["agent_type"] = "remote_access"
        context["session_id"] = request.session_id or str(uuid.uuid4())
        
        # Handle streaming if requested
        if request.stream:
            async def stream_generator():
                agent_manager = get_agent_manager()
                async for chunk in agent_manager.process_request_stream(request.query, context):
                    yield f"data: {json.dumps(chunk)}\n\n"
                
            return StreamingResponse(
                stream_generator(), 
                media_type="text/event-stream"
            )
        else:
            agent_manager = get_agent_manager()
            response = await agent_manager.process_request(request.query, context)
            response["session_id"] = context["session_id"]
            return response
            
    except Exception as e:
        logger.error(f"Error in remote access agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/safety-emergency")
async def query_safety_emergency(request: AgentQueryRequest):
    """Query the Safety & Emergency Agent directly"""
    try:
        # Set context for the specific agent type
        context = request.context or {}
        context["agent_type"] = "safety_emergency"
        context["session_id"] = request.session_id or str(uuid.uuid4())
        
        # Handle streaming if requested
        if request.stream:
            async def stream_generator():
                agent_manager = get_agent_manager()
                async for chunk in agent_manager.process_request_stream(request.query, context):
                    yield f"data: {json.dumps(chunk)}\n\n"
                
            return StreamingResponse(
                stream_generator(), 
                media_type="text/event-stream"
            )
        else:
            agent_manager = get_agent_manager()
            response = await agent_manager.process_request(request.query, context)
            response["session_id"] = context["session_id"]
            return response
            
    except Exception as e:
        logger.error(f"Error in safety emergency agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/charging-energy")
async def query_charging_energy(request: AgentQueryRequest):
    """Query the Charging & Energy Agent directly"""
    try:
        # Set context for the specific agent type
        context = request.context or {}
        context["agent_type"] = "charging_energy"
        context["session_id"] = request.session_id or str(uuid.uuid4())
        
        # Handle streaming if requested
        if request.stream:
            async def stream_generator():
                agent_manager = get_agent_manager()
                async for chunk in agent_manager.process_request_stream(request.query, context):
                    yield f"data: {json.dumps(chunk)}\n\n"
                
            return StreamingResponse(
                stream_generator(), 
                media_type="text/event-stream"
            )
        else:
            agent_manager = get_agent_manager()
            response = await agent_manager.process_request(request.query, context)
            response["session_id"] = context["session_id"]
            return response
            
    except Exception as e:
        logger.error(f"Error in charging energy agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/information-services")
async def query_information_services(request: AgentQueryRequest):
    """Query the Information Services Agent directly"""
    try:
        # Set context for the specific agent type
        context = request.context or {}
        context["agent_type"] = "information_services"
        context["session_id"] = request.session_id or str(uuid.uuid4())
        
        # Handle streaming if requested
        if request.stream:
            async def stream_generator():
                agent_manager = get_agent_manager()
                async for chunk in agent_manager.process_request_stream(request.query, context):
                    yield f"data: {json.dumps(chunk)}\n\n"
                
            return StreamingResponse(
                stream_generator(), 
                media_type="text/event-stream"
            )
        else:
            agent_manager = get_agent_manager()
            response = await agent_manager.process_request(request.query, context)
            response["session_id"] = context["session_id"]
            return response
            
    except Exception as e:
        logger.error(f"Error in information services agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feature-control")
async def query_feature_control(request: AgentQueryRequest):
    """Query the Vehicle Feature Control Agent directly"""
    try:
        # Set context for the specific agent type
        context = request.context or {}
        context["agent_type"] = "vehicle_feature_control"
        context["session_id"] = request.session_id or str(uuid.uuid4())
        
        # Handle streaming if requested
        if request.stream:
            async def stream_generator():
                agent_manager = get_agent_manager()
                async for chunk in agent_manager.process_request_stream(request.query, context):
                    yield f"data: {json.dumps(chunk)}\n\n"
                
            return StreamingResponse(
                stream_generator(), 
                media_type="text/event-stream"
            )
        else:
            agent_manager = get_agent_manager()
            response = await agent_manager.process_request(request.query, context)
            response["session_id"] = context["session_id"]
            return response
            
    except Exception as e:
        logger.error(f"Error in feature control agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/diagnostics-battery")
async def query_diagnostics_battery(request: AgentQueryRequest):
    """Query the Diagnostics & Battery Agent directly"""
    try:
        # Set context for the specific agent type
        context = request.context or {}
        context["agent_type"] = "diagnostics_battery"
        context["session_id"] = request.session_id or str(uuid.uuid4())
        
        # Handle streaming if requested
        if request.stream:
            async def stream_generator():
                agent_manager = get_agent_manager()
                async for chunk in agent_manager.process_request_stream(request.query, context):
                    yield f"data: {json.dumps(chunk)}\n\n"
                
            return StreamingResponse(
                stream_generator(), 
                media_type="text/event-stream"
            )
        else:
            agent_manager = get_agent_manager()
            response = await agent_manager.process_request(request.query, context)
            response["session_id"] = context["session_id"]
            return response
            
    except Exception as e:
        logger.error(f"Error in diagnostics battery agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/alerts-notifications")
async def query_alerts_notifications(request: AgentQueryRequest):
    """Query the Alerts & Notifications Agent directly"""
    try:
        # Set context for the specific agent type
        context = request.context or {}
        context["agent_type"] = "alerts_notifications"
        context["session_id"] = request.session_id or str(uuid.uuid4())
        
        # Handle streaming if requested
        if request.stream:
            async def stream_generator():
                agent_manager = get_agent_manager()
                async for chunk in agent_manager.process_request_stream(request.query, context):
                    yield f"data: {json.dumps(chunk)}\n\n"
                
            return StreamingResponse(
                stream_generator(), 
                media_type="text/event-stream"
            )
        else:
            agent_manager = get_agent_manager()
            response = await agent_manager.process_request(request.query, context)
            response["session_id"] = context["session_id"]
            return response
            
    except Exception as e:
        logger.error(f"Error in alerts notifications agent: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Analytics endpoints that use agent capabilities
@router.post("/analyze/vehicle-data")
async def analyze_vehicle_data_endpoint(request: AnalysisRequest):
    """Analyze vehicle data using the Diagnostics & Battery Agent"""
    try:
        session_id = str(uuid.uuid4())
        context = {
            "agent_type": "diagnostics_battery",
            "vehicle_id": request.vehicle_id,
            "time_period": request.time_period,
            "metrics": request.metrics,
            "session_id": session_id
        }
        
        try:
            agent_manager = get_agent_manager()
            response = await agent_manager.process_request(
                "Run a full diagnostic analysis on my vehicle",
                context
            )
            response["session_id"] = session_id
            return response
        except Exception as e:
            logger.error(f"Error in vehicle analysis: {str(e)}")
            # Return a fallback response
            return {
                "response": f"Unable to complete vehicle analysis for {request.vehicle_id} at this time. Please try again later.",
                "error": "Analysis service temporarily unavailable",
                "session_id": session_id,
                "vehicle_id": request.vehicle_id,
                "plugins_used": [],
                "execution_time": 0
            }
        
    except Exception as e:
        logger.error(f"Error in vehicle data analysis: {str(e)}")
        raise HTTPException(status_code=503, detail="Analysis service temporarily unavailable")

@router.post("/recommend/services")
async def recommend_services_endpoint(request: ServiceRecommendationRequest):
    """Get service recommendations using the Feature Control Agent"""
    try:
        context = {
            "agent_type": "vehicle_feature_control",
            "vehicle_id": request.vehicle_id,
            "mileage": request.mileage,
            "last_service_date": request.last_service_date
        }
        
        try:
            agent_manager = get_agent_manager()
            response = await agent_manager.process_request(
                "Recommend vehicle services based on my vehicle condition",
                context
            )
            return response
        except Exception as e:
            logger.error(f"Error in service recommendations: {str(e)}")
            # Return a fallback response
            return {
                "response": f"Unable to generate service recommendations for vehicle {request.vehicle_id} at this time. Please try again later.",
                "error": "Recommendation service temporarily unavailable",
                "vehicle_id": request.vehicle_id,
                "plugins_used": [],
                "execution_time": 0
            }
            
    except Exception as e:
        logger.error(f"Error in service recommendations: {str(e)}")
        raise HTTPException(status_code=503, detail="Recommendation service temporarily unavailable")

# Add a log at the end of the module to confirm it's fully parsed when imported
logger.debug("vehicle.apis.agent_routes module loaded and router defined.")
