"""
Data models for the Cosmos DB data generator.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
import uuid


@dataclass
class Location:
    """Geographic location data"""
    latitude: float
    longitude: float
    address: Optional[str] = None


@dataclass
class VehicleFeatures:
    """Vehicle feature configuration"""
    has_autopilot: bool = False
    has_heated_seats: bool = False
    has_remote_start: bool = False
    has_navigation: bool = False
    is_electric: bool = False


@dataclass
class TelemetryData:
    """Vehicle telemetry data"""
    speed: int = 0
    engine_temp: int = 0
    oil_level: int = 0
    tire_pressure: Dict[str, int] = field(default_factory=dict)
    brake_wear: Dict[str, str] = field(default_factory=dict)
    engine_health: str = "Good"
    tire_condition: Dict[str, str] = field(default_factory=dict)
    fuel_economy: int = 0
    odometer: int = 0
    battery_voltage: float = 12.0
    charging_status: str = "Not Charging"
    charging_rate: float = 0.0
    estimated_range: int = 0


@dataclass
class Vehicle:
    """Vehicle data model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vehicle_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    brand: str = ""
    vehicle_model: str = ""
    year: int = 2024
    type: str = ""
    color: str = ""
    vin: str = ""
    license_plate: str = ""
    status: str = "Active"
    mileage: int = 0
    fuel_level: int = 0
    battery_level: int = 100
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    last_location: Optional[Location] = None
    owner_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    features: Optional[VehicleFeatures] = None
    region: str = "North America"
    current_telemetry: Optional[TelemetryData] = None


@dataclass
class ServiceRecord:
    """Service record data model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    service_code: str = ""
    description: str = ""
    start_date: str = ""
    end_date: str = ""
    next_service_date: str = ""
    vehicle_id: str = ""
    mileage: int = 0
    next_service_mileage: int = 0
    cost: float = 0.0
    location: str = ""
    technician: str = ""
    notes: str = ""
    parts_replaced: List[Dict[str, Any]] = field(default_factory=list)
    service_advisories: List[Dict[str, Any]] = field(default_factory=list)
    invoice_number: str = ""
    service_status: str = "Completed"
    service_type: str = "Scheduled"
    customer_rating: Optional[int] = None


@dataclass
class Command:
    """Vehicle command data model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vehicle_id: str = ""
    command_type: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "Pending"
    timestamp: str = ""
    executed_time: Optional[str] = None
    initiated_by: str = ""
    response_code: Optional[int] = None
    response_message: str = ""
    priority: str = "Normal"
    device_type: str = "Mobile App"
    ip_address: str = ""
    authentication_type: str = "Password"
    command_origin: str = "Remote"
    retry_count: int = 0


@dataclass
class Notification:
    """Notification data model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notification_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vehicle_id: str = ""
    type: str = ""
    message: str = ""
    timestamp: str = ""
    read_time: Optional[str] = None
    read: bool = False
    severity: str = "low"
    source: str = "System"
    action_required: bool = False
    action_url: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    location: Optional[Location] = None
    related_commands: List[str] = field(default_factory=list)
    target_users: List[str] = field(default_factory=list)
    phone_number: Optional[str] = None
    is_test_notification: bool = False


@dataclass
class VehicleStatus:
    """Vehicle status data model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    vehicle_id: str = ""
    battery_level: int = 100
    temperature: int = 20
    speed: int = 0
    oil_level: int = 100
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    location: Optional[Location] = None
    engine_status: str = "off"
    door_status: Dict[str, str] = field(default_factory=dict)
    climate_settings: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PointOfInterest:
    """Point of Interest data model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    poi_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    category: str = ""
    rating: float = 0.0
    location: Optional[Location] = None
    description: str = ""
    opening_hours: str = ""
    amenities: List[str] = field(default_factory=list)
    photos: List[str] = field(default_factory=list)
    contact: Dict[str, str] = field(default_factory=dict)
    price_level: int = 1
    tags: List[str] = field(default_factory=list)
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class ChargingStation:
    """Charging station data model"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    station_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    power_level: str = ""
    region: str = ""
    location: Optional[Location] = None
    provider: str = ""
    total_ports: int = 0
    available_ports: int = 0
    charging_points: List[Dict[str, Any]] = field(default_factory=list)
    amenities: List[str] = field(default_factory=list)
    payment_options: List[str] = field(default_factory=list)
    opening_hours: str = "24/7"
    pricing: Dict[str, float] = field(default_factory=dict)
    user_rating: float = 0.0
    status: str = "Operational"
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())
