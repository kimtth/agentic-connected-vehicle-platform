from typing import Optional, Dict, Any
from models.base import CamelModel

class Command(CamelModel):
    id: Optional[str] = None
    command_id: Optional[str] = None
    vehicle_id: str
    command_type: str
    status: Optional[str] = None
    timestamp: Optional[str] = None
    response: Optional[str] = None
    error: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
