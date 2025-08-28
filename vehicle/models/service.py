from typing import Optional
from models.base import CamelModel

class Service(CamelModel):
    id: Optional[str] = None
    vehicle_id: str
    service_code: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    next_service_date: Optional[str] = None
    mileage: Optional[int] = None
    next_service_mileage: Optional[int] = None
    cost: Optional[float] = 0.0
    location: Optional[str] = None
    technician: Optional[str] = None
    invoice_number: Optional[str] = None
    service_status: Optional[str] = None
    service_type: Optional[str] = None
    notes: Optional[str] = None
