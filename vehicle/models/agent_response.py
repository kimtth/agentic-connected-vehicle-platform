from typing import List, Optional, Any, Literal
from models.base import CamelModel


class ParsedAgentMessage(CamelModel):
    message: str
    status: Literal["completed", "error", "pending", "unknown"] = "completed"
    plugins_used: List[str] = []
    data: Optional[Any] = None


class AgentResponse(CamelModel):
    response: str
    success: bool
    plugins_used: List[str] = []
    data: Optional[Any] = None
    fallback_used: bool = False
    error: Optional[str] = None


class AgentServiceResponse(CamelModel):
    response: str
    success: bool
    session_id: str
    plugins_used: List[str] = []
    execution_time: float | int = 0
    data: Optional[Any] = None
    fallback_used: bool = False
    error: Optional[str] = None
    vehicle_id: Optional[str] = None


class StreamingChunk(CamelModel):
    response: str
    complete: bool
    plugins_used: List[str] = []
    error: Optional[str] = None
    session_id: Optional[str] = None
