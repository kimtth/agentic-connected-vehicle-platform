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
