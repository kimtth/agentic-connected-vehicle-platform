from models.base import BaseSchemaModel
from typing import Optional, Dict, Any

class VehicleProfile(BaseSchemaModel):
    """Model for vehicle profile data"""
    id: Optional[str] = None
    vehicle_id: str
    make: str
    model: str
    year: int
    trim: Optional[str] = None
    status: Optional[str] = None
    features: Optional[Dict[str, Any]] = None
    last_location: Optional[Dict[str, float]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "vehicleId": "abc123",
                "make": "Tesla",
                "model": "Model 3",
                "year": 2023,
                "trim": "Performance",
                "status": "Active",
                "features": {
                    "isElectric": True,
                    "hasNavigation": True,
                    "hasAutoPilot": False
                },
                "lastLocation": {
                    "latitude": 37.7749,
                    "longitude": -122.4194
                }
            }
        }