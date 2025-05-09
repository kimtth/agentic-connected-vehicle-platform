from pydantic import BaseModel
from typing import Optional

class VehicleProfile(BaseModel):
    Country: str
    Region: str
    ManufacturedYear: int
    Brand: str
    VehicleId: str
    VehicleModel: str
    DataDictionaryType: str
    DataDictionaryVersion: str
