from pydantic import BaseModel
from typing import Optional

class Service(BaseModel):
    ServiceCode: str
    Description: str
    StartDate: str  # ISO format
    EndDate: Optional[str] = None
