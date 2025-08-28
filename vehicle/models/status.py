from models.base import CamelModel
from typing import Optional, Dict, Any

class VehicleStatus(CamelModel):
    """Canonical vehicle status model (serialized in camelCase)."""
    id: Optional[str] = None
    vehicle_id: str  # Will serialize as vehicleId via CamelModel alias generator
    battery: Optional[float] = None
    temperature: Optional[float] = None
    speed: Optional[float] = None
    oil_remaining: Optional[float] = None
    odometer: Optional[float] = None
    engine_temp: Optional[float] = None
    climate_settings: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None

    class Config:
        # Example reflects camelCase JSON (produced via alias generation)
        json_schema_extra = {  # renamed from schema_extra to suppress Pydantic v2 warning
            "example": {
                "vehicleId": "abc123",
                "battery": 80,
                "temperature": 22,
                "speed": 0,
                "oilRemaining": 90,
                "odometer": 12345,
                "engineTemp": 75,
                "climateSettings": {
                    "temperature": 22,
                    "fanSpeed": "medium",
                    "isAirConditioningOn": True,
                    "isHeatingOn": False
                },
                "timestamp": "2025-08-28T12:34:56Z"
            }
        }
