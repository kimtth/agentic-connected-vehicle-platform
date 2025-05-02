from pydantic import BaseModel
from typing import Optional, Dict

class Command(BaseModel):
    commandId: str
    vehicleId: str
    commandType: str
    payload: Dict
    status: Optional[str] = "pending"
