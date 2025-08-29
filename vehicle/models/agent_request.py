from typing import Any, Optional, Dict, List
from models.base import CamelModel


class AgentQueryRequest(CamelModel):
    query: str
    context: Optional[Dict[str, Any]]
    session_id: Optional[str]
    stream: Optional[bool]


class AnalysisRequest(CamelModel):
    vehicle_id: str
    time_period: Optional[str] = "7d"
    metrics: Optional[List[str]] = None


class ServiceRecommendationRequest(CamelModel):
    vehicle_id: str
    mileage: Optional[int] = None
    last_service_date: Optional[str] = None
    last_service_date: Optional[str] = None


class EmergencyCallRequest(CamelModel):
    emergency_type: Optional[str] = "general"  # general, medical, fire, police


class CollisionReportRequest(CamelModel):
    severity: str = "unknown"  # minor, major, severe, unknown
    location: Optional[Dict[str, float]] = None


class TheftReportRequest(CamelModel):
    description: Optional[str] = None
    last_seen_location: Optional[Dict[str, float]] = None


class DoorControlRequest(CamelModel):
    action: str  # lock, unlock


class EngineControlRequest(CamelModel):
    action: str  # start, stop


class LightsControlRequest(CamelModel):
    light_type: str = "headlights"  # headlights, interior_lights, hazard_lights
    action: str = "on"  # on, off


class ClimateControlRequest(CamelModel):
    temperature: Optional[int] = 22
    action: str = "set_temperature"  # heating, cooling, set_temperature
    auto: bool = True


class WindowsControlRequest(CamelModel):
    action: str = "up"  # up, down
    windows: str = "all"  # all, driver, passenger
