from typing import Optional
from models.base import BaseSchemaModel

class Notification(BaseSchemaModel):
    id: Optional[str] = None
    vehicle_id: Optional[str] = None
    type: Optional[str] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
    read: Optional[bool] = False
    severity: Optional[str] = None
    source: Optional[str] = None
    action_required: Optional[bool] = None
    created_at: Optional[str] = None
