from typing import List, Optional, Union
from models.base import BaseSchemaModel


class SeedResult(BaseSchemaModel):
    vehicle_id: str
    created_vehicle: bool
    status_seeded: bool


class BulkSeedRequest(BaseSchemaModel):
    vehicles: int = 10
    commands_per_vehicle: int = 2
    notifications_per_vehicle: int = 5
    services_per_vehicle: int = 5
    statuses_per_vehicle: int = 1


class BulkSeedConfig(BaseSchemaModel):
    vehicles: int
    commands_per_vehicle: int
    notifications_per_vehicle: int
    services_per_vehicle: int
    statuses_per_vehicle: int


class BulkSeedCreated(BaseSchemaModel):
    vehicles: int
    statuses: int
    services: int
    commands: int
    notifications: int
    vehicle_ids: List[str]


class BulkSeedSummary(BaseSchemaModel):
    ok: bool
    config: BulkSeedConfig
    created: BulkSeedCreated
    azure_cosmos_connected: bool


class SeedStatus(BaseSchemaModel):
    azure_cosmos_enabled: bool
    azure_cosmos_connected: bool
    last_seed: Optional[Union[BulkSeedSummary, dict]]
    status: str
    last_location: dict
