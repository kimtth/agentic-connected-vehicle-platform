from pydantic import BaseModel
from typing import Optional, Dict, Any

class VehicleStatus(BaseModel):
    """Model for vehicle status data"""
    vehicleId: str
    Battery: int
    Temperature: int
    Speed: int
    OilRemaining: int
    engineStatus: Optional[str] = "off"
    doorStatus: Optional[Dict[str, str]] = None
    climateSettings: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "vehicleId": "abc123",
                "Battery": 80,
                "Temperature": 22,
                "Speed": 0,
                "OilRemaining": 90,
                "engineStatus": "off",
                "doorStatus": {
                    "driver": "locked",
                    "passenger": "locked",
                    "rearLeft": "locked",
                    "rearRight": "locked"
                },
                "climateSettings": {
                    "temperature": 22,
                    "fanSpeed": "medium",
                    "isAirConditioningOn": True,
                    "isHeatingOn": False
                }
            }
        }
