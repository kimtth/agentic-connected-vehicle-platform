from pydantic import BaseModel
from typing import Dict, Any, List, Literal

class VehicleResponseFormat(BaseModel):
    """Model for structured SK responses."""
    status: Literal['input_required', 'completed', 'error'] = 'completed'
    message: str
    plugins_used: List[str] = []
    data: Dict[str, Any] = {}