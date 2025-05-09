from pydantic import BaseModel
from typing import Optional

class Notification(BaseModel):
    notificationId: str
    commandId: str
    vehicleId: str
    message: str
    status: str
    timestamp: str  # ISO format
