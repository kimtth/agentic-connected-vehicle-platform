from __future__ import annotations
"""
Endpoints for interacting with the agentic components of the connected vehicle platform.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from typing import TYPE_CHECKING, Union
from models.agent_request import (
    AgentQueryRequest,
    AnalysisRequest,
    ServiceRecommendationRequest,
)
from models.agent_response import AgentServiceResponse, StreamingChunk
import uuid
import logging
from utils.agent_tools import (
    search_vehicle_database,
    recommend_services,
    validate_command,
    analyze_vehicle_data,
    format_notification,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/agent",
    tags=["Agents"],  # Using "Agents" as a tag example
)

# Lazy import to avoid circular dependency with agents.agent_manager
if TYPE_CHECKING:
    from agents.agent_manager import AgentManager  # type: ignore


async def _resolve_agent_manager() -> "AgentManager":
    """Lazy dependency resolver to avoid circular import at module import time."""
    from agents.agent_manager import AgentManager

    return AgentManager()


# Define request models


# Define tool handlers (kept for backward compatibility)
tool_handlers = {
    "search_vehicle_database": search_vehicle_database,
    "recommend_services": recommend_services,
    "validate_command": validate_command,
    "analyze_vehicle_data": analyze_vehicle_data,
    "format_notification": format_notification,
}


def _build_service_response(raw: dict, session_id: str, vehicle_id: str | None = None) -> AgentServiceResponse:
    """Normalize raw agent_manager output (any casing) into AgentServiceResponse."""
    if raw is None:
        raw = {}
    get = raw.get
    return AgentServiceResponse(
        response=get("response") or get("Response") or "",
        success=bool(get("success") if "success" in raw else get("Success", True)),
        session_id=session_id,
        plugins_used=get("plugins_used") or get("PluginsUsed") or [],
        execution_time=get("execution_time") or get("ExecutionTime") or 0,
        data=get("data"),
        fallback_used=get("fallback_used") or get("FallbackUsed") or False,
        error=get("error") or get("Error"),
        vehicle_id=vehicle_id,
    )


def _streaming_chunk_from(raw: dict, session_id: str) -> StreamingChunk:
    get = raw.get
    return StreamingChunk(
        response=get("response") or get("Response") or "",
        complete=bool(get("complete") or get("Complete") or False),
        plugins_used=get("plugins_used") or get("PluginsUsed") or [],
        error=get("error") or get("Error"),
        session_id=session_id,
    )


# Debug marker to confirm module import success (helps distinguish import vs runtime attach issues)
logger.debug("agent_routes module imported successfully")

# Agent system entry point with streaming support
@router.post("/ask", response_model=None)
async def ask_agent(
    request: AgentQueryRequest,
    agent_manager: "AgentManager" = Depends(_resolve_agent_manager),
):
    """General agent system entry point to ask any question, with optional streaming"""
    try:
        # Ensure we have a session ID
        session_id = request.session_id or str(uuid.uuid4())
        context = request.context or {}
        context["session_id"] = session_id

        agent_type = context.get("agent_type")
        if agent_type:
            # Map frontend agent types to backend agent types
            agent_type_mapping = {
                "remote-access": "remote_access",
                "safety-emergency": "safety_emergency",
                "charging-energy": "charging_energy",
                "information-services": "information_services",
                "feature-control": "vehicle_feature_control",
                "diagnostics-battery": "diagnostics_battery",
                "alerts-notifications": "alerts_notifications",
            }

            # Convert frontend agent type to backend agent type
            mapped_agent_type = agent_type_mapping.get(agent_type, agent_type)
            context["agent_type"] = mapped_agent_type

            logger.info(f"Routing request to agent type: {mapped_agent_type}")

        # Handle streaming if requested
        if request.stream:
            async def stream_generator():
                try:
                    async for chunk in agent_manager.process_request_stream(
                        request.query, context
                    ):
                        sc = _streaming_chunk_from(chunk, session_id)
                        yield f"data: {sc.model_dump_json(by_alias=True)}\n\n"
                except Exception as e:
                    logger.error(f"Error in streaming response: {str(e)}")
                    sc = StreamingChunk(
                        response="",
                        complete=True,
                        plugins_used=[],
                        error="Agent service temporarily unavailable",
                        session_id=session_id,
                    )
                    yield f"data: {sc.model_dump_json(by_alias=True)}\n\n"
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )
        else:
            # Regular non-streaming response
            try:
                raw = await agent_manager.process_request(request.query, context)
                return _build_service_response(raw, session_id)
            except Exception as e:
                logger.error(f"Error in agent processing: {str(e)}")
                return AgentServiceResponse(
                    response="I apologize, but I'm experiencing technical difficulties. Please try again later.",
                    success=False,
                    session_id=session_id,
                    plugins_used=[],
                    execution_time=0,
                    error="Agent service temporarily unavailable",
                )

    except Exception as e:
        logger.error(f"Error in agent ask: {str(e)}")
        raise HTTPException(
            status_code=503, detail="Agent service temporarily unavailable"
        )


# Pattern helper to reduce duplication
async def _handle_direct_agent(request: AgentQueryRequest, agent_key: str, agent_manager: "AgentManager") -> Union[AgentServiceResponse, StreamingResponse]:
    session_id = request.session_id or str(uuid.uuid4())
    context = request.context or {}
    context["agent_type"] = agent_key
    context["session_id"] = session_id
    if request.stream:
        async def stream_generator():
            try:
                async for chunk in agent_manager.process_request_stream(request.query, context):
                    sc = _streaming_chunk_from(chunk, session_id)
                    yield f"data: {sc.model_dump_json(by_alias=True)}\n\n"
            except Exception as e:
                logger.error(f"Streaming error ({agent_key}): {e}")
                sc = StreamingChunk(
                    response="",
                    complete=True,
                    plugins_used=[],
                    error="Agent service temporarily unavailable",
                    session_id=session_id,
                )
                yield f"data: {sc.model_dump_json(by_alias=True)}\n\n"
        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )
    try:
        raw = await agent_manager.process_request(request.query, context)
        return _build_service_response(raw, session_id)
    except Exception as e:
        logger.error(f"Error in {agent_key} agent: {e}")
        return AgentServiceResponse(
            response="Request could not be completed. Please try again later.",
            success=False,
            session_id=session_id,
            plugins_used=[],
            execution_time=0,
            error="Agent service temporarily unavailable",
        )


@router.post("/remote-access", response_model=None)
async def query_remote_access(
    request: AgentQueryRequest,
    agent_manager: "AgentManager" = Depends(_resolve_agent_manager),
):
    """Query the Remote Access Agent directly"""
    return await _handle_direct_agent(request, "remote_access", agent_manager)


@router.post("/safety-emergency", response_model=None)
async def query_safety_emergency(
    request: AgentQueryRequest,
    agent_manager: "AgentManager" = Depends(_resolve_agent_manager),
):
    """Query the Safety & Emergency Agent directly"""
    return await _handle_direct_agent(request, "safety_emergency", agent_manager)


@router.post("/charging-energy", response_model=None)
async def query_charging_energy(
    request: AgentQueryRequest,
    agent_manager: "AgentManager" = Depends(_resolve_agent_manager),
):
    """Query the Charging & Energy Agent directly"""
    return await _handle_direct_agent(request, "charging_energy", agent_manager)


@router.post("/information-services", response_model=None)
async def query_information_services(
    request: AgentQueryRequest,
    agent_manager: "AgentManager" = Depends(_resolve_agent_manager),
):
    """Query the Information Services Agent directly"""
    return await _handle_direct_agent(request, "information_services", agent_manager)


@router.post("/feature-control", response_model=None)
async def query_feature_control(
    request: AgentQueryRequest,
    agent_manager: "AgentManager" = Depends(_resolve_agent_manager),
):
    """Query the Vehicle Feature Control Agent directly"""
    return await _handle_direct_agent(request, "vehicle_feature_control", agent_manager)


@router.post("/diagnostics-battery", response_model=None)
async def query_diagnostics_battery(
    request: AgentQueryRequest,
    agent_manager: "AgentManager" = Depends(_resolve_agent_manager),
):
    """Query the Diagnostics & Battery Agent directly"""
    return await _handle_direct_agent(request, "diagnostics_battery", agent_manager)


@router.post("/alerts-notifications", response_model=None)
async def query_alerts_notifications(
    request: AgentQueryRequest,
    agent_manager: "AgentManager" = Depends(_resolve_agent_manager),
):
    """Query the Alerts & Notifications Agent directly"""
    return await _handle_direct_agent(request, "alerts_notifications", agent_manager)


# Analytics endpoints that use agent capabilities
@router.post("/analyze/vehicle-data")
async def analyze_vehicle_data_endpoint(
    request: AnalysisRequest,
    agent_manager: "AgentManager" = Depends(_resolve_agent_manager),
) -> AgentServiceResponse:
    """Analyze vehicle data using the Diagnostics & Battery Agent"""
    session_id = str(uuid.uuid4())
    context = {
        "agent_type": "diagnostics_battery",
        "vehicle_id": request.vehicle_id,
        "time_period": request.time_period,
        "metrics": request.metrics,
        "session_id": session_id,
    }
    try:
        raw = await agent_manager.process_request("Run a full diagnostic analysis on my vehicle", context)
        return _build_service_response(raw, session_id, vehicle_id=request.vehicle_id)
    except Exception as e:
        logger.error(f"Error in vehicle analysis: {e}")
        return AgentServiceResponse(
            response=f"Unable to complete vehicle analysis for {request.vehicle_id} at this time. Please try again later.",
            success=False,
            session_id=session_id,
            plugins_used=[],
            execution_time=0,
            error="Analysis service temporarily unavailable",
            vehicle_id=request.vehicle_id,
        )


@router.post("/recommend/services")
async def recommend_services_endpoint(
    request: ServiceRecommendationRequest,
    agent_manager: "AgentManager" = Depends(_resolve_agent_manager),
) -> AgentServiceResponse:
    """Get service recommendations using the Feature Control Agent"""
    session_id = str(uuid.uuid4())
    context = {
        "agent_type": "vehicle_feature_control",
        "vehicle_id": request.vehicle_id,
        "mileage": request.mileage,
        "last_service_date": request.last_service_date,
        "session_id": session_id,
    }
    try:
        raw = await agent_manager.process_request(
            "Recommend vehicle services based on my vehicle condition", context
        )
        return _build_service_response(raw, session_id, vehicle_id=request.vehicle_id)
    except Exception as e:
        logger.error(f"Error in service recommendations: {e}")
        return AgentServiceResponse(
            response=f"Unable to generate service recommendations for vehicle {request.vehicle_id} at this time. Please try again later.",
            success=False,
            session_id=session_id,
            plugins_used=[],
            execution_time=0,
            error="Recommendation service temporarily unavailable",
            vehicle_id=request.vehicle_id,
        )