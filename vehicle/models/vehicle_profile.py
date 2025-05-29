from pydantic import BaseModel
from typing import Optional, Dict, Any

class VehicleProfile(BaseModel):
    """Model for vehicle profile data"""
    vehicleId: str  # Changed from VehicleId to vehicleId
    Brand: str
    VehicleModel: str
    Year: int
    Country: str
    Region: str
    VIN: Optional[str] = None
    Color: Optional[str] = None
    Mileage: Optional[int] = 0
    Status: Optional[str] = "Active"
    Features: Optional[Dict[str, Any]] = None
    LastLocation: Optional[Dict[str, float]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "vehicleId": "abc123",
                "Brand": "Tesla",
                "VehicleModel": "Model 3",
                "Year": 2023,
                "Country": "USA",
                "Region": "North America",
                "VIN": "1HGBH41JXMN109186",
                "Color": "Red",
                "Mileage": 15000,
                "Status": "Active",
                "Features": {
                    "IsElectric": True,
                    "HasNavigation": True,
                    "HasAutoPilot": False
                },
                "LastLocation": {
                    "Latitude": 37.7749,
                    "Longitude": -122.4194
                }
            }
        }
