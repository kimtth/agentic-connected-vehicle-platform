from datetime import datetime
from typing import Any, Optional, List, Dict
from .base import CamelModel

# Assuming global camelCase alias generation is configured centrally (models.py),
# so we only specify explicit aliases where names differ.

class ActionResponse(CamelModel):
    data: Any

class AIResponse(CamelModel):
    response: str

class SpeechTokenResponse(CamelModel):
    token: str
    region: str

class GenericPayloadResponse(CamelModel):
    payload: Dict[str, Any]

class InfoResponse(CamelModel):
    status: str
    version: str
    azure_cosmos_enabled: bool
    azure_cosmos_connected: bool

class HealthServices(CamelModel):
    api: str
    cosmos_db: str
    mcp_weather: str
    mcp_traffic: str
    mcp_poi: str
    mcp_navigation: str

class HealthResponse(CamelModel):
    status: str
    timestamp: datetime
    services: HealthServices

class CommandHistoryItem(CamelModel):
    timestamp: str
    command: str
    status: str
    response: Optional[str] = ""
    error: Optional[str] = ""

class CommandSubmitResponse(CamelModel):
    command_id: str

class Notification(CamelModel):
    id: str
    vehicle_id: str
    type: str
    message: str
    timestamp: datetime
    read: bool = False

class CreateNotificationResponse(CamelModel):
    id: str
    status: str
    data: Any

class MarkNotificationReadResponse(CamelModel):
    id: str
    status: str
    data: Any

class GenericDetailResponse(CamelModel):
    detail: str
