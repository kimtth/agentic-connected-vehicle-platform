"""
Sample data generator for Cosmos DB.

This script generates and inserts sample data for the Connected Vehicle Platform:
- Vehicles
- Services
- Commands
- Notifications
- Vehicle Status data
"""

import os
import sys
import argparse
import random
import uuid
import asyncio

import time
import json
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

from azure.cosmos.aio import CosmosClient
from azure.core.exceptions import AzureError, ServiceRequestError, ServiceResponseError
from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError
from azure.cosmos import PartitionKey
from azure.core.tracing.decorator import distributed_trace

# Configure logging
from utils.logging_config import get_logger
logger = get_logger(__name__)

# Sample data constants
VEHICLE_MAKES = ["Tesla", "BMW", "Mercedes", "Toyota", "Honda", "Ford", "Chevrolet", "Audi", "Porsche", "Lexus"]
VEHICLE_MODELS = {
    "Tesla": ["Model S", "Model 3", "Model X", "Model Y", "Cybertruck"],
    "BMW": ["3 Series", "5 Series", "7 Series", "X3", "X5", "i4", "iX"],
    "Mercedes": ["C-Class", "E-Class", "S-Class", "GLC", "EQS"],
    "Toyota": ["Camry", "Corolla", "RAV4", "Highlander", "Prius"],
    "Honda": ["Civic", "Accord", "CR-V", "Pilot", "Odyssey"],
    "Ford": ["F-150", "Mustang", "Explorer", "Escape", "Mach-E"],
    "Chevrolet": ["Silverado", "Equinox", "Tahoe", "Corvette", "Bolt"],
    "Audi": ["A4", "A6", "Q5", "Q7", "e-tron"],
    "Porsche": ["911", "Taycan", "Cayenne", "Macan", "Panamera"],
    "Lexus": ["ES", "RX", "NX", "LS", "IS"]
}
VEHICLE_TYPES = ["Sedan", "SUV", "Truck", "Coupe", "Hatchback", "Van"]
VEHICLE_COLORS = ["Red", "Blue", "Black", "White", "Silver", "Gray", "Green", "Yellow"]
VEHICLE_STATUS = ["Active", "Inactive", "Maintenance", "Offline"]
SERVICE_TYPES = ["Oil Change", "Tire Rotation", "Brake Service", "Battery Replacement", "Air Filter", "Transmission Service"]
COMMAND_TYPES = ["LockDoors", "UnlockDoors", "StartEngine", "StopEngine", "HonkHorn", "FlashLights", "SetTemperature"]
COMMAND_STATUS = ["Pending", "Sent", "Delivered", "Executed", "Failed"]
NOTIFICATION_TYPES = ["service_reminder", "low_fuel_alert", "low_battery_alert", "security_alert", "system_update", "speed_alert", "curfew_alert", "geofence_alert"]
NOTIFICATION_PRIORITY = ["low", "medium", "high", "critical"]

# Points of interest data for information services
POINTS_OF_INTEREST = [
    {"name": "Central Park", "category": "Park", "rating": 4.7},
    {"name": "Downtown Cafe", "category": "Restaurant", "rating": 4.2},
    {"name": "City Museum", "category": "Museum", "rating": 4.5},
    {"name": "Shopping Mall", "category": "Shopping", "rating": 4.0},
    {"name": "Community Theater", "category": "Entertainment", "rating": 4.3},
    {"name": "Tech Hub", "category": "Business", "rating": 4.1},
    {"name": "Riverside Walk", "category": "Park", "rating": 4.6},
    {"name": "Fine Dining Restaurant", "category": "Restaurant", "rating": 4.8},
    {"name": "Convention Center", "category": "Business", "rating": 4.0},
    {"name": "Public Library", "category": "Education", "rating": 4.4}
]

# Charging stations data
CHARGING_STATIONS = [
    {"name": "City Center Station", "power_level": "Level 3", "ports": 4},
    {"name": "Shopping Mall Station", "power_level": "Level 2", "ports": 6},
    {"name": "Highway Rest Stop", "power_level": "Level 3", "ports": 8},
    {"name": "Office Park Station", "power_level": "Level 2", "ports": 4},
    {"name": "Residential Area Station", "power_level": "Level 2", "ports": 2},
    {"name": "Hotel Charging Hub", "power_level": "Level 3", "ports": 6},
    {"name": "Airport Long-term Parking", "power_level": "Level 2", "ports": 12},
    {"name": "Downtown Garage", "power_level": "Level 2", "ports": 8},
    {"name": "Supermarket", "power_level": "Level 2", "ports": 4},
    {"name": "Fast Charging Hub", "power_level": "Level 3", "ports": 10}
]

# Alert message templates
ALERT_MESSAGES = {
    "speed_alert": [
        "Vehicle exceeded speed limit of {value} km/h",
        "Speed threshold of {value} km/h has been surpassed",
        "Warning: Speed limit ({value} km/h) violation detected"
    ],
    "low_battery_alert": [
        "Battery level below {value}%", 
        "Vehicle battery is running low: {value}%", 
        "Low battery warning: {value}% remaining"
    ],
    "curfew_alert": [
        "Vehicle used outside allowed hours ({start_time} to {end_time})",
        "Curfew violation: Vehicle active during restricted period",
        "Alert: Vehicle operation detected during curfew hours"
    ],
    "geofence_alert": [
        "Vehicle has left designated area",
        "Geofence boundary crossed",
        "Vehicle location outside approved zone"
    ],
    "security_alert": [
        "Unauthorized access attempt detected",
        "Security event: Unusual activity detected",
        "Vehicle security breach attempt"
    ]
}

# Enhanced diagnostic and battery data
DIAGNOSTIC_ISSUE_TYPES = [
    "ENGINE_CHECK", "ABS_WARNING", "TIRE_PRESSURE_LOW", "BATTERY_LOW", 
    "OIL_PRESSURE_LOW", "TRANSMISSION_WARNING", "BRAKE_SYSTEM_WARNING",
    "AIRBAG_SYSTEM_WARNING", "COOLANT_TEMPERATURE_HIGH", "ELECTRICAL_SYSTEM_WARNING"
]

BRAKE_WEAR_LEVELS = ["Good", "Fair", "Poor", "Critical"]
ENGINE_HEALTH_LEVELS = ["Excellent", "Good", "Fair", "Poor", "Critical"]
TIRE_CONDITIONS = ["Excellent", "Good", "Fair", "Worn", "Needs Replacement"]

# Security and remote access events
REMOTE_ACCESS_EVENTS = [
    "DOOR_LOCK", "DOOR_UNLOCK", "ENGINE_START", "ENGINE_STOP", 
    "CLIMATE_CONTROL_ON", "CLIMATE_CONTROL_OFF", "HORN_HONK", 
    "LIGHTS_FLASH", "WINDOW_OPEN", "WINDOW_CLOSE"
]

# Safety and emergency events
SAFETY_EVENT_TYPES = [
    "COLLISION_DETECTED", "AIRBAG_DEPLOYED", "EMERGENCY_CALL_INITIATED",
    "THEFT_ALERT", "PANIC_BUTTON_PRESSED", "BREAKDOWN_DETECTED",
    "HAZARD_WARNING", "SPEED_LIMIT_EXCEEDED", "SEVERE_WEATHER_ALERT",
    "ROAD_HAZARD_ALERT", "SOS_SIGNAL_SENT"
]

SAFETY_EVENT_SEVERITY = ["Low", "Medium", "High", "Critical"]

# Additional sample data for battery diagnostics
BATTERY_DIAGNOSTICS = {
    "12V_BATTERY": {
        "voltage_range": (10.5, 14.8),
        "health_range": (60, 100),
        "resistance_range": (0.01, 0.15),
        "charging_rate_range": (0.5, 5.0)
    },
    "EV_BATTERY": {
        "cell_voltage_range": (3.2, 4.2),
        "temperature_range": (15, 45),
        "charge_cycles_range": (0, 2000),
        "degradation_rate_range": (0.01, 0.15),
        "fast_charge_count_range": (0, 300),
        "cell_balance_deviation_range": (0.01, 0.2)
    }
}

# Enhanced charging and energy data for charging_energy_agent.py
CHARGING_NETWORK_PROVIDERS = [
    "ChargePoint", "Electrify America", "EVgo", "Tesla Supercharger", "Blink", 
    "Shell Recharge", "Volta", "Ionity", "FastNed", "GreenWay"
]

CHARGING_STATION_AMENITIES = [
    "Restrooms", "Food", "WiFi", "Shopping", "Waiting Area", "24/7 Access", 
    "Covered Parking", "Security Cameras", "Lounge", "Restaurant"
]

CHARGING_SESSIONS = [
    {
        "start_time": "08:30",
        "duration_minutes": 45,
        "energy_delivered_kwh": 35.6,
        "cost": 12.46,
        "charging_speed_kw": 50,
        "location_type": "Public"
    },
    {
        "start_time": "18:15",
        "duration_minutes": 30,
        "energy_delivered_kwh": 22.4,
        "cost": 7.84,
        "charging_speed_kw": 50,
        "location_type": "Public"
    },
    {
        "start_time": "22:00",
        "duration_minutes": 360,
        "energy_delivered_kwh": 42.8,
        "cost": 5.99,
        "charging_speed_kw": 7.2,
        "location_type": "Home"
    },
    {
        "start_time": "12:45",
        "duration_minutes": 25,
        "energy_delivered_kwh": 40.2,
        "cost": 14.07,
        "charging_speed_kw": 150,
        "location_type": "Supercharger"
    },
    {
        "start_time": "15:30",
        "duration_minutes": 40,
        "energy_delivered_kwh": 25.1,
        "cost": 8.78,
        "charging_speed_kw": 50,
        "location_type": "Work"
    }
]

ENERGY_EFFICIENCY_FACTORS = [
    "Highway Driving", "City Driving", "Climate Control Use", 
    "Tire Pressure", "Outside Temperature", "Vehicle Speed",
    "Regenerative Braking Settings"
]

# Enhanced information services data for information_services_agent.py
WEATHER_CONDITIONS = [
    "Clear", "Partly Cloudy", "Cloudy", "Light Rain", "Heavy Rain", 
    "Thunderstorm", "Snow", "Sleet", "Fog", "Windy"
]

TRAFFIC_CONGESTION_LEVELS = ["None", "Light", "Moderate", "Heavy", "Severe"]

TRAFFIC_INCIDENTS = [
    "Accident", "Road Construction", "Lane Closure", "Disabled Vehicle", 
    "Special Event", "Road Closure", "Object on Road", "Emergency Vehicles"
]

POI_CATEGORIES = [
    "Restaurant", "Gas Station", "Hotel", "Shopping", "Attraction", 
    "Parking", "EV Charging", "Park", "Medical", "Entertainment"
]

NAVIGATION_ROUTE_OPTIONS = [
    "Fastest Route", "Shortest Route", "Eco-friendly Route", 
    "Avoid Highways", "Avoid Tolls", "Scenic Route"
]

# Enhanced vehicle feature control data for vehicle_feature_control_agent.py
VEHICLE_FEATURES = [
    "Climate Control", "Media System", "Interior Lighting", "Ambient Lighting",
    "Driving Mode", "Suspension Setting", "Steering Sensitivity", "Auto Folding Mirrors",
    "Auto Locking", "Window Control", "Seat Position", "Seat Heating/Cooling",
    "Steering Wheel Heating", "Driver Assistance", "Display Settings"
]

CLIMATE_PRESETS = [
    "Eco", "Comfort", "Max", "Defrost", "Driver Only", "Custom"
]

DRIVING_MODES = [
    "Comfort", "Sport", "Eco", "Snow/Ice", "Off-Road", "Individual", "Track"
]

DRIVER_ASSISTANCE_SETTINGS = [
    "Lane Keeping", "Adaptive Cruise Control", "Emergency Braking", 
    "Blind Spot Detection", "Park Assist", "Traffic Sign Recognition",
    "Driver Attention Monitor", "Pedestrian Detection"
]

class CosmosDataGenerator:
    """Generator for Cosmos DB sample data"""
    
    def __init__(self):
        """Initialize the data generator"""
        self.endpoint = os.getenv("COSMOS_DB_ENDPOINT")
        self.key = os.getenv("COSMOS_DB_KEY")
        self.database_name = os.getenv("COSMOS_DB_DATABASE")
        self.use_aad_auth = os.getenv("COSMOS_DB_USE_AAD", "false").lower() == "true"
        
        # Container names
        self.vehicles_container_name = os.getenv("COSMOS_DB_CONTAINER_VEHICLES", "vehicles")
        self.services_container_name = os.getenv("COSMOS_DB_CONTAINER_SERVICES", "services")
        self.commands_container_name = os.getenv("COSMOS_DB_CONTAINER_COMMANDS", "commands")
        self.notifications_container_name = os.getenv("COSMOS_DB_CONTAINER_NOTIFICATIONS", "notifications")
        self.status_container_name = os.getenv("COSMOS_DB_CONTAINER_STATUS", "VehicleStatus")
        self.pois_container_name = os.getenv("COSMOS_DB_CONTAINER_POIS", "PointsOfInterest")
        self.charging_stations_container_name = os.getenv("COSMOS_DB_CONTAINER_CHARGING", "ChargingStations")
        
        # Configure telemetry if connection string is provided
        app_insights_conn_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        if app_insights_conn_string:
            try:
                logger.info("Azure Monitor telemetry configured")
            except Exception as e:
                logger.warning(f"Failed to configure Azure Monitor telemetry: {e}")
        
        # Client will be initialized in the connect method
        self.client = None
        self.database = None
        self.vehicles_container = None
        self.services_container = None
        self.commands_container = None
        self.notifications_container = None
        self.status_container = None
        self.pois_container = None
        self.charging_stations_container = None
        
        # Store generated vehicle IDs for later use
        self.vehicle_ids = []
        
        # Configure retry settings
        self.max_retry_attempts = 5
        self.retry_base_delay = 1  # seconds
        
        # Add a flag to track if we're using a serverless account - default to true for safety
        self.is_serverless = True
        
        logger.info("Cosmos DB data generator initialized")
    
    @distributed_trace
    async def connect(self):
        """Connect to Cosmos DB with retry logic"""
        if not all([self.endpoint, self.database_name]):
            logger.error("Cosmos DB connection information missing. Please check environment variables.")
            sys.exit(1)

        retry_count = 0
        while retry_count < self.max_retry_attempts:
            try:
                # Choose auth method
                if self.use_aad_auth:
                    credential = DefaultAzureCredential()
                    self.client = CosmosClient(self.endpoint, credential=credential)
                else:
                    try:
                        self.client = CosmosClient(self.endpoint, credential=self.key)
                    except AzureError as e:
                        # Detect disabled local auth
                        msg = str(e).lower()
                        if "authorization is disabled" in msg or "use an aad token" in msg:
                            logger.warning("Master key auth disabled (%s). Falling back to AAD auth.", e)
                            self.use_aad_auth = True
                            credential = DefaultAzureCredential()
                            self.client = CosmosClient(self.endpoint, credential=credential)
                        else:
                            raise

                # Create database if it doesn't exist
                try:
                    # Get database client
                    self.database = self.client.get_database_client(self.database_name)
                    # Attempt to read database properties to check if it exists
                    await self.database.read()
                    logger.info(f"Using existing database: {self.database_name}")
                except CosmosResourceNotFoundError:
                    logger.info(f"Database {self.database_name} does not exist. Creating...")
                    self.database = await self.client.create_database(self.database_name)
                    logger.info(f"Database {self.database_name} created successfully")

                await self._ensure_containers_exist()
                logger.info("Successfully connected to Cosmos DB")
                
                # Connection successful, break out of retry loop
                break
                
            except (ServiceRequestError, ServiceResponseError) as e:
                retry_count += 1
                if retry_count >= self.max_retry_attempts:
                    logger.error(f"Max retry attempts reached. Failed to connect to Cosmos DB: {e}")
                    sys.exit(1)
                    
                # Calculate exponential backoff with jitter
                delay = self.retry_base_delay * (2 ** (retry_count - 1)) + random.uniform(0, 1)
                logger.warning(f"Connection attempt {retry_count} failed: {e}. Retrying in {delay:.2f} seconds...")
                await asyncio.sleep(delay)
            
            except Exception as e:
                logger.error(f"Failed to connect to Cosmos DB: {e}")
                sys.exit(1)
    
    @distributed_trace
    async def _ensure_containers_exist(self):
        """Ensure all Cosmos DB containers exist, creating them if missing."""
        container_pks = {
            self.vehicles_container_name: "/vehicleId",
            self.services_container_name: "/vehicleId",
            self.commands_container_name: "/vehicleId",
            self.notifications_container_name: "/vehicleId",
            self.status_container_name: "/vehicleId",
            self.pois_container_name: "/category",
            self.charging_stations_container_name: "/region",
        }
        
        for container_id, pk in container_pks.items():
            try:
                container = self.database.get_container_client(container_id)
                await container.read()
                logger.debug(f"Container {container_id} already exists")
            except CosmosResourceNotFoundError:
                logger.info(f"Creating container: {container_id}")
                
                # Set time-to-live for specific containers
                ttl = -1  # -1 means no TTL
                if container_id == self.status_container_name:
                    # Status data might be kept for 30 days
                    ttl = 60 * 60 * 24 * 30
                elif container_id == self.commands_container_name or container_id == self.notifications_container_name:
                    # Commands and notifications might be kept for 90 days
                    ttl = 60 * 60 * 24 * 90
                
                try:
                    # For serverless accounts, don't set throughput
                    await self.database.create_container(
                        id=container_id,
                        partition_key=PartitionKey(path=pk),
                        default_ttl=ttl
                    )
                    logger.info(f"Container {container_id} created with TTL={ttl}s")
                except Exception as e:
                    logger.error(f"Failed to create container {container_id}: {e}")
                    raise
        
        # Re-initialize container references
        self._initialize_container_references()
    
    def _initialize_container_references(self):
        """Initialize container references after ensuring they exist"""
        self.vehicles_container = self.database.get_container_client(self.vehicles_container_name)
        self.services_container = self.database.get_container_client(self.services_container_name)
        self.commands_container = self.database.get_container_client(self.commands_container_name)
        self.notifications_container = self.database.get_container_client(self.notifications_container_name)
        self.status_container = self.database.get_container_client(self.status_container_name)
        self.pois_container = self.database.get_container_client(self.pois_container_name)
        self.charging_stations_container = self.database.get_container_client(self.charging_stations_container_name)
    
    async def close(self):
        """Close the connection"""
        if self.client:
            await self.client.close()
            logger.info("Cosmos DB connection closed")
    
    def generate_vehicle(self):
        """Generate sample vehicle data"""
        vehicle_id = str(uuid.uuid4())
        make = random.choice(VEHICLE_MAKES)
        model = random.choice(VEHICLE_MODELS[make])
        current_year = datetime.now().year
        year = random.randint(current_year - 8, current_year)
        
        # Determine if the vehicle is electric based on make/model
        is_electric = (
            make in ["Tesla"] or 
            model in ["i4", "iX", "e-tron", "Taycan", "Mach-E", "Bolt", "EQS"] or
            random.random() < 0.3  # 30% chance for other vehicles to be electric
        )
        
        # Add more detailed diagnostics information for agents
        diagnostic_history = []
        for i in range(random.randint(0, 5)):
            issue_date = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 365))
            resolved_date = issue_date + timedelta(days=random.randint(1, 30)) if random.random() > 0.3 else None
            diagnostic_history.append({
                "issueType": random.choice(DIAGNOSTIC_ISSUE_TYPES),
                "description": f"System detected {random.choice(['anomaly', 'warning', 'error'])} in {random.choice(['engine', 'transmission', 'electrical', 'cooling', 'fuel'])} system",
                "dateDetected": issue_date.isoformat(),
                "dateResolved": resolved_date.isoformat() if resolved_date else None,
                "status": "Resolved" if resolved_date else "Active"
            })
        
        # Enhanced telemetry for vehicle
        telemetry = {
            "Speed": random.randint(0, 80),
            "EngineTemp": random.randint(170, 220) if not is_electric else 0,
            "OilLevel": random.randint(30, 100) if not is_electric else 0,
            "TirePressure": {
                "FrontLeft": random.randint(32, 36),
                "FrontRight": random.randint(32, 36),
                "RearLeft": random.randint(32, 36),
                "RearRight": random.randint(32, 36)
            },
            "BrakeWear": {
                "FrontLeft": random.choice(BRAKE_WEAR_LEVELS),
                "FrontRight": random.choice(BRAKE_WEAR_LEVELS),
                "RearLeft": random.choice(BRAKE_WEAR_LEVELS),
                "RearRight": random.choice(BRAKE_WEAR_LEVELS)
            },
            "EngineHealth": random.choice(ENGINE_HEALTH_LEVELS),
            "TireCondition": {
                "FrontLeft": random.choice(TIRE_CONDITIONS),
                "FrontRight": random.choice(TIRE_CONDITIONS),
                "RearLeft": random.choice(TIRE_CONDITIONS),
                "RearRight": random.choice(TIRE_CONDITIONS)
            },
            "FuelEconomy": random.randint(15, 40) if not is_electric else 0,
            "Odometer": random.randint(1000, 100000),
            "BatteryVoltage": round(random.uniform(12.0, 14.2), 1),
            "ChargingStatus": random.choice(["Not Charging", "Charging", "Fast Charging"]) if is_electric else "N/A",
            "ChargingRate": round(random.uniform(0, 150), 1) if is_electric else 0,
            "EstimatedRange": random.randint(150, 400) if is_electric else random.randint(300, 600)
        }
        
        # Security and remote access data
        security_features = {
            "RemoteAccessEnabled": random.choice([True, False]),
            "ImmobilizerActive": random.choice([True, False]),
            "GeoFencingActive": random.choice([True, False]),
            "LastRemoteAccess": (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 30))).isoformat() if random.random() > 0.3 else None,
            "RemoteAccessHistory": [
                {
                    "type": random.choice(REMOTE_ACCESS_EVENTS),
                    "timestamp": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60))).isoformat(),
                    "user": f"User{random.randint(1, 5)}",
                    "successful": random.random() > 0.1
                } for _ in range(random.randint(0, 5))
            ],
            "AuthorizedUsers": [f"User{random.randint(1, 10)}" for _ in range(random.randint(1, 3))]
        }
        
        # Safety and emergency systems data
        safety_systems = {
            "EmergencyCallSystem": {
                "isActive": random.choice([True, False]),
                "lastTested": (datetime.now(timezone.utc) - timedelta(days=random.randint(0, 180))).isoformat()
            },
            "AntiTheftSystem": {
                "isActive": random.choice([True, False]),
                "sensitivity": random.choice(["Low", "Medium", "High"])
            },
            "EmergencyEvents": [
                {
                    "type": random.choice(SAFETY_EVENT_TYPES),
                    "timestamp": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 365))).isoformat(),
                    "severity": random.choice(SAFETY_EVENT_SEVERITY),
                    "location": {
                        "latitude": round(random.uniform(25.0, 49.0), 6),
                        "longitude": round(random.uniform(-125.0, -70.0), 6)
                    },
                    "resolved": random.choice([True, False])
                } for _ in range(random.randint(0, 3))
            ],
            "CollisionDetectionSensitivity": random.choice(["Low", "Medium", "High"]),
            "AutomaticEmergencyBraking": random.choice([True, False]),
            "LaneDepartureWarning": random.choice([True, False]),
            "BlindSpotMonitoring": random.choice([True, False])
        }
        
        # Battery specific data for diagnostics agent
        battery_data = {}
        if is_electric:
            # EV battery details
            ev_data = BATTERY_DIAGNOSTICS["EV_BATTERY"]
            cell_count = random.choice([96, 108, 144, 192, 384])
            cell_capacity = random.choice([2.5, 3.0, 3.6, 4.0, 4.5])  # Ah
            battery_data = {
                "batteryType": random.choice(["Lithium-Ion", "LiFePO4", "NMC", "LTO"]),
                "nominalCapacity": round(cell_count * cell_capacity, 1),  # kWh
                "nominalVoltage": round(3.7 * (cell_count / 96) * 96, 1),  # V
                "cellCount": cell_count,
                "cellGroups": round(cell_count / random.choice([8, 12, 16])),
                "cellVoltage": {
                    "min": round(random.uniform(ev_data["cell_voltage_range"][0], ev_data["cell_voltage_range"][1] - 0.2), 2),
                    "max": round(random.uniform(ev_data["cell_voltage_range"][1] - 0.2, ev_data["cell_voltage_range"][1]), 2),
                    "average": round(random.uniform(ev_data["cell_voltage_range"][0] + 0.3, ev_data["cell_voltage_range"][1] - 0.3), 2)
                },
                "temperature": {
                    "min": random.randint(ev_data["temperature_range"][0], ev_data["temperature_range"][1] - 5),
                    "max": random.randint(ev_data["temperature_range"][1] - 5, ev_data["temperature_range"][1]),
                    "average": random.randint(ev_data["temperature_range"][0] + 5, ev_data["temperature_range"][1] - 8)
                },
                "chargeCycles": random.randint(ev_data["charge_cycles_range"][0], ev_data["charge_cycles_range"][1]),
                "fastChargeCount": random.randint(ev_data["fast_charge_count_range"][0], ev_data["fast_charge_count_range"][1]),
                "cellBalanceDeviation": round(random.uniform(ev_data["cell_balance_deviation_range"][0], ev_data["cell_balance_deviation_range"][1]), 3),
                "estimatedDegradation": round(random.uniform(0, 20), 1),  # percentage
                "manufacturingDate": (datetime.now(timezone.utc) - timedelta(days=random.randint(365, 365*8))).strftime("%Y-%m-%d"),
                "estimatedReplacement": (datetime.now(timezone.utc) + timedelta(days=random.randint(365, 365*10))).strftime("%Y-%m-%d"),
                "estimatedRangeNew": random.randint(350, 650),  # km when new
                "estimatedRangeCurrent": random.randint(300, 600),  # km current
                "coolingSystem": random.choice(["Air Cooled", "Liquid Cooled"]),
                "batteryHealth": random.randint(80, 100)  # percentage
            }
        else:
            # 12V battery details
            v12_data = BATTERY_DIAGNOSTICS["12V_BATTERY"]
            battery_data = {
                "batteryType": random.choice(["Lead-Acid", "AGM", "EFB"]),
                "voltage": round(random.uniform(v12_data["voltage_range"][0], v12_data["voltage_range"][1]), 1),
                "coldCrankingAmps": random.choice([550, 600, 650, 700, 750, 800]),
                "reserveCapacity": random.randint(90, 150),  # minutes
                "ageInMonths": random.randint(1, 60),
                "health": random.randint(v12_data["health_range"][0], v12_data["health_range"][1]),
                "lastReplacementDate": (datetime.now(timezone.utc) - timedelta(days=random.randint(30, 1460))).strftime("%Y-%m-%d"),
                "internalResistance": round(random.uniform(v12_data["resistance_range"][0], v12_data["resistance_range"][1]), 3),
                "chargingSystem": {
                    "alternatorOutput": round(random.uniform(13.2, 14.8), 1),
                    "chargingRate": round(random.uniform(v12_data["charging_rate_range"][0], v12_data["charging_rate_range"][1]), 1)
                },
                "batteryHealth": random.randint(70, 100)  # percentage
            }
        
        # Add feature control settings for vehicle_feature_control_agent.py
        feature_control_settings = {
            "climate": {
                "enabled": random.choice([True, False]), 
                "temperature": random.randint(16, 28),
                "fanSpeed": random.choice(["low", "medium", "high"]),
                "airConditioningOn": random.choice([True, False]),
                "heatingOn": random.choice([True, False]),
                "autoMode": random.choice([True, False]),
                "recirculation": random.choice([True, False]),
                "zoneSetting": random.choice(["all", "driver", "passenger", "rear"]),
                "defrostFront": random.choice([True, False]),
                "defrostRear": random.choice([True, False]),
                "currentPreset": random.choice(CLIMATE_PRESETS)
            },
            "drivingMode": {
                "currentMode": random.choice(DRIVING_MODES),
                "customized": random.choice([True, False]),
                "autoMode": random.choice([True, False]),
                "ecoModeEnabled": is_electric or random.choice([True, False])
            },
            "lights": {
                "headlights": random.choice(["auto", "off", "parking", "on", "high_beam"]),
                "interiorBrightness": random.randint(1, 10),
                "ambientLightingEnabled": random.choice([True, False]),
                "ambientLightingColor": random.choice(["blue", "red", "green", "purple", "white", "orange"]),
                "welcomeLightsEnabled": random.choice([True, False]),
                "autoHighBeamEnabled": random.choice([True, False])
            },
            "media": {
                "volume": random.randint(0, 30),
                "source": random.choice(["radio", "bluetooth", "usb", "streaming"]),
                "equalizerSettings": {
                    "bass": random.randint(-5, 5),
                    "mid": random.randint(-5, 5),
                    "treble": random.randint(-5, 5),
                    "balance": random.randint(-5, 5),
                    "fader": random.randint(-5, 5)
                },
                "surroundEnabled": random.choice([True, False])
            },
            "seats": {
                "driver": {
                    "position": random.randint(1, 10),
                    "height": random.randint(1, 10),
                    "recline": random.randint(1, 10),
                    "lumbar": random.randint(1, 5),
                    "heatingLevel": random.randint(0, 3),
                    "coolingLevel": random.randint(0, 3) if random.choice([True, False]) else 0,
                    "memoryEnabled": random.choice([True, False])
                },
                "passenger": {
                    "position": random.randint(1, 10),
                    "height": random.randint(1, 10),
                    "recline": random.randint(1, 10),
                    "lumbar": random.randint(1, 5),
                    "heatingLevel": random.randint(0, 3),
                    "coolingLevel": random.randint(0, 3) if random.choice([True, False]) else 0
                }
            },
            "driverAssistance": {
                "enabled": random.choice([True, False]),
                "settings": {
                    setting: random.choice([True, False]) 
                    for setting in DRIVER_ASSISTANCE_SETTINGS
                },
                "sensitivityLevel": random.choice(["low", "medium", "high"]),
                "warningMode": random.choice(["visual", "audio", "both"])
            }
        }
        
        # Enhance vehicle with charging data for charging_energy_agent.py
        charging_energy_data = {}
        if is_electric:
            charging_energy_data = {
                "chargingProfile": {
                    "preferredStartTime": f"{random.randint(0, 23):02d}:{random.choice(['00', '30'])}",
                    "preferredEndTime": f"{random.randint(0, 23):02d}:{random.choice(['00', '30'])}",
                    "targetChargeLevel": random.choice([80, 85, 90, 95, 100]),
                    "scheduledDepartures": [
                        {
                            "day": day,
                            "time": f"{random.randint(5, 9):02d}:{random.choice(['00', '15', '30', '45'])}"
                        } 
                        for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                        if random.choice([True, False])
                    ],
                    "preferredLocations": [
                        {"name": "Home", "isDefault": True},
                        {"name": "Work", "isDefault": False}
                    ] + [
                        {"name": f"Favorite {i}", "isDefault": False}
                        for i in range(1, random.randint(1, 3))
                        if random.choice([True, False])
                    ],
                    "maxChargingCurrent": random.choice([16, 32, 40, 80]),
                    "offPeakChargingEnabled": random.choice([True, False])
                },
                "energyUsage": {
                    "lifetimeEfficiency": round(random.uniform(14.0, 22.0), 1),  # kWh/100km
                    "lifetimeEnergyUsed": round(random.uniform(1000, 15000), 1),  # kWh
                    "lifetimeDistance": random.randint(10000, 100000),  # km
                    "lifetimeRegeneration": round(random.uniform(150, 3000), 1),  # kWh
                    "recentTrips": [
                        {
                            "date": (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d"),
                            "distance": round(random.uniform(5, 80), 1),
                            "energyUsed": round(random.uniform(1, 16), 1),
                            "efficiency": round(random.uniform(14.0, 22.0), 1),
                            "regeneration": round(random.uniform(0.1, 3.0), 1)
                        }
                        for i in range(1, random.randint(5, 10))
                    ],
                    "efficiencyFactors": {
                        factor: round(random.uniform(0.8, 1.2), 2)
                        for factor in random.sample(ENERGY_EFFICIENCY_FACTORS, 3)
                    }
                },
                "chargingHistory": [
                    {
                        "date": (datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d"),
                        "startTime": session["start_time"],
                        "duration": session["duration_minutes"],
                        "energyDelivered": session["energy_delivered_kwh"],
                        "cost": session["cost"],
                        "location": session["location_type"],
                        "startBatteryLevel": max(5, min(95, random.randint(10, 60))),
                        "endBatteryLevel": random.randint(60, 100),
                        "chargingSpeed": session["charging_speed_kw"],
                        "provider": random.choice(CHARGING_NETWORK_PROVIDERS) if session["location_type"] != "Home" else "Home"
                    }
                    for i, session in enumerate(random.sample(CHARGING_SESSIONS, min(len(CHARGING_SESSIONS), random.randint(3, 5))))
                ],
                "preferredChargingNetworks": random.sample(CHARGING_NETWORK_PROVIDERS, random.randint(1, 3))
            }
        
        # Add information services data for information_services_agent.py
        information_services_data = {
            "weatherPreferences": {
                "temperatureUnit": random.choice(["Celsius", "Fahrenheit"]),
                "showPrecipitationChance": random.choice([True, False]),
                "showWindSpeed": random.choice([True, False]),
                "showHumidity": random.choice([True, False]),
                "showAlerts": random.choice([True, False]),
                "defaultLocation": random.choice(["Vehicle Location", "Home", "Work"])
            },
            "trafficPreferences": {
                "avoidHighways": random.choice([True, False]),
                "avoidTolls": random.choice([True, False]),
                "avoidFerries": random.choice([True, False]),
                "preferFuelEfficient": is_electric or random.choice([True, False]),
                "receiveAlerts": random.choice([True, False]),
                "alertThreshold": random.choice(["Light", "Moderate", "Heavy"])
            },
            "navigationHistory": [
                {
                    "destination": f"Destination {i}",
                    "address": f"{random.randint(100, 999)} Example St, City, State",
                    "coordinates": {
                        "latitude": round(random.uniform(25.0, 49.0), 6),
                        "longitude": round(random.uniform(-125.0, -70.0), 6)
                    },
                    "category": random.choice(POI_CATEGORIES),
                    "visitCount": random.randint(1, 10),
                    "lastVisited": (datetime.now(timezone.utc) - timedelta(days=random.randint(1, 60))).isoformat(),
                    "isFavorite": random.choice([True, False])
                }
                for i in range(1, random.randint(5, 15))
            ],
            "favoriteDestinations": [
                {"name": "Home", "type": "Home"},
                {"name": "Work", "type": "Work"}
            ] + [
                {
                    "name": f"Favorite {random.choice(POI_CATEGORIES)}",
                    "type": random.choice(POI_CATEGORIES)
                }
                for _ in range(random.randint(1, 5))
            ],
            "navigationPreferences": {
                "preferredRouteType": random.choice(NAVIGATION_ROUTE_OPTIONS),
                "avoidTraffic": random.choice([True, False]),
                "showParking": random.choice([True, False]),
                "showGasStations": not is_electric and random.choice([True, False]),
                "showChargingStations": is_electric and random.choice([True, False]),
                "voice": random.choice(["None", "Voice 1", "Voice 2", "Voice 3"]),
                "voiceVolume": random.randint(1, 10),
                "mapView": random.choice(["2D", "3D", "Satellite"])
            }
        }
        
        # Create enhanced vehicle object
        vehicle = {
            "id": str(uuid.uuid4()),
            "VehicleId": vehicle_id,
            "Brand": make,
            "VehicleModel": model,
            "Year": year,
            "Type": random.choice(VEHICLE_TYPES),
            "Color": random.choice(VEHICLE_COLORS),
            "VIN": f"1HGCM82633A{random.randint(100000, 999999)}",
            "LicensePlate": f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(100, 999)}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}",
            "Status": random.choice(VEHICLE_STATUS),
            "Mileage": random.randint(1000, 100000),
            "FuelLevel": 0 if is_electric else random.randint(1, 100),
            "BatteryLevel": random.randint(30, 100) if is_electric else 100,
            "LastUpdated": datetime.now(timezone.utc).isoformat(),
            "LastLocation": {
                "Latitude": round(random.uniform(25.0, 49.0), 6),
                "Longitude": round(random.uniform(-125.0, -70.0), 6)
            },
            "OwnerId": str(uuid.uuid4()),
            "Features": {
                "HasAutoPilot": is_electric or random.choice([True, False]),
                "HasHeatedSeats": random.choice([True, False]),
                "HasRemoteStart": random.choice([True, False]),
                "HasNavigation": random.choice([True, False]),
                "IsElectric": is_electric
            },
            "Region": random.choice(["North America", "Europe", "Asia"]),
            "CurrentTelemetry": telemetry,
            "DiagnosticHistory": diagnostic_history,
            "BatteryData": battery_data,
            "SecurityFeatures": security_features,
            "SafetySystems": safety_systems,
            # New fields for various agents
            "FeatureSettings": feature_control_settings,
            "ChargingEnergyData": charging_energy_data,
            "InformationServicesData": information_services_data
        }
        
        return vehicle
    
    def generate_service(self, vehicle_id, is_electric=False):
        """Generate sample service data"""
        service_types = SERVICE_TYPES.copy()
        if is_electric:
            # Remove oil change for electric vehicles
            if "Oil Change" in service_types:
                service_types.remove("Oil Change")
                service_types.append("Battery Health Check")
        
        service_type = random.choice(service_types)
        service_date = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 180))
        next_service_date = service_date + timedelta(days=random.randint(90, 365))
        
        # Add more specific service types for the diagnostics agent
        additional_service_types = []
        if is_electric:
            additional_service_types = [
                "Battery Health Check", "Battery Coolant Service",
                "EV System Check", "Charging Port Maintenance",
                "Electric Drive Unit Service"
            ]
        else:
            additional_service_types = [
                "Fuel System Cleaning", "Transmission Fluid Change",
                "Spark Plug Replacement", "Engine Air Filter",
                "Timing Belt Service", "Coolant Flush"
            ]
        
        # Common services for all vehicles
        common_services = [
            "Brake Fluid Change", "Suspension Check", 
            "Steering System Service", "Wheel Alignment",
            "AC System Service", "Diagnostic System Update"
        ]
        
        all_service_types = SERVICE_TYPES.copy() + additional_service_types + common_services
        
        # Remove inappropriate services for electric vehicles
        if is_electric:
            all_service_types = [s for s in all_service_types if "Oil" not in s]
        
        service_type = random.choice(all_service_types)
        service_date = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 180))
        next_service_date = service_date + timedelta(days=random.randint(90, 365))
        
        # Add more realistic service data
        service_record = {
            "id": str(uuid.uuid4()),
            "ServiceCode": service_type.replace(" ", "_").upper(),
            "Description": f"{service_type} service",
            "StartDate": service_date.isoformat(),
            "EndDate": service_date.isoformat(),  # Same day for completion
            "NextServiceDate": next_service_date.isoformat(),
            "vehicleId": vehicle_id,
            "mileage": random.randint(1000, 100000),
            "nextServiceMileage": random.randint(1000, 100000) + random.choice([5000, 7500, 10000, 15000]),
            "cost": round(random.uniform(20.0, 500.0), 2),
            "location": f"Service Center {random.randint(1, 20)}",
            "technician": f"Technician {random.randint(1, 50)}",
            "notes": random.choice([
                "Regular maintenance completed",
                "All checks passed",
                "Replaced worn components",
                "Customer reported issues resolved",
                "Recommended additional maintenance in future"
            ]),
            "partsReplaced": [],
            "serviceAdvisories": [],
            "invoiceNumber": f"INV-{random.randint(10000, 99999)}",
            "serviceStatus": "Completed",
            "serviceType": random.choice(["Scheduled", "Repair", "Recall", "Customer Request"]),
            "customerRating": random.randint(1, 5) if random.random() > 0.7 else None
        }
        
        # Add replaced parts for more realistic service
        if random.random() > 0.3:  # 70% chance of parts being replaced
            num_parts = random.randint(1, 3)
            for _ in range(num_parts):
                if is_electric:
                    part_options = ["Cabin Air Filter", "Wiper Blades", "Brake Pads", "Coolant", "12V Battery"]
                else:
                    part_options = ["Oil Filter", "Air Filter", "Cabin Air Filter", "Wiper Blades", "Brake Pads", "Spark Plugs"]
                
                service_record["partsReplaced"].append({
                    "partName": random.choice(part_options),
                    "partNumber": f"P{random.randint(100000, 999999)}",
                    "cost": round(random.uniform(10.0, 150.0), 2),
                    "warranty": random.choice([30, 60, 90, 180, 365])  # days
                })
        
        # Add service advisories
        if random.random() > 0.7:  # 30% chance of service advisories
            num_advisories = random.randint(1, 2)
            for _ in range(num_advisories):
                if is_electric:
                    advisory_options = [
                        "Battery cooling system performance slightly reduced",
                        "Charging port shows minor wear",
                        "Regenerative braking calibration recommended",
                        "Battery management system update available"
                    ]
                else:
                    advisory_options = [
                        "Oil consumption slightly high",
                        "Minor coolant leak detected",
                        "Transmission fluid discoloration noted",
                        "Spark plugs show normal wear but replacement recommended within 10,000 miles"
                    ]
                
                service_record["serviceAdvisories"].append({
                    "description": random.choice(advisory_options),
                    "severity": random.choice(["Low", "Medium", "High"]),
                    "recommendedAction": random.choice([
                        "Monitor and check at next service",
                        "Schedule follow-up in 3 months",
                        "Address within 30 days",
                        "No immediate action required"
                    ])
                })
        
        return service_record
    
    def generate_command(self, vehicle_id):
        """Generate sample command data"""
        command_type = random.choice(COMMAND_TYPES)
        sent_time = datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 1440))
        executed_time = sent_time + timedelta(minutes=random.randint(1, 10))
        
        parameters = {}
        if command_type == "SetTemperature":
            parameters["temperature"] = random.randint(65, 85)
        
        # Enhanced command types for remote access agent
        enhanced_command_types = COMMAND_TYPES + [
            "SET_CLIMATE_TEMPERATURE", "SET_SEAT_HEATING", "OPEN_TRUNK", 
            "CLOSE_TRUNK", "OPEN_FRUNK", "CLOSE_FRUNK", "ACTIVATE_VALET_MODE",
            "DEACTIVATE_VALET_MODE", "UPDATE_FIRMWARE", "SET_CHARGING_LIMIT"
        ]
        
        command_type = random.choice(enhanced_command_types)
        sent_time = datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 1440))
        executed_time = sent_time + timedelta(minutes=random.randint(1, 10))
        
        parameters = {}
        if command_type == "SET_TEMPERATURE" or command_type == "SET_CLIMATE_TEMPERATURE":
            parameters["temperature"] = random.randint(16, 28)
            parameters["fanSpeed"] = random.choice(["low", "medium", "high"])
            parameters["isAirConditioningOn"] = random.choice([True, False])
        elif command_type == "SET_SEAT_HEATING":
            parameters["seat"] = random.choice(["driver", "passenger", "rear_left", "rear_right", "all"])
            parameters["level"] = random.randint(0, 3)
        elif command_type == "SET_CHARGING_LIMIT":
            parameters["limit"] = random.choice([70, 80, 90, 100])
        elif command_type == "LOCK_DOORS" or command_type == "UNLOCK_DOORS":
            parameters["doors"] = random.choice(["all", "driver", "passenger", "rear"])
        
        command = {
            "id": str(uuid.uuid4()),
            "commandId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "commandType": command_type,
            "parameters": parameters,
            "status": random.choice(COMMAND_STATUS),
            "timestamp": sent_time.isoformat(),
            "executedTime": executed_time.isoformat() if random.random() > 0.3 else None,
            "initiatedBy": f"User{random.randint(1, 10)}",
            "responseCode": random.choice([200, 201, 400, 404, 500]) if random.random() > 0.7 else None,
            "responseMessage": "Command executed successfully" if random.random() > 0.2 else "Command failed",
            "priority": random.choice(["Low", "Normal", "High"]),
            "deviceType": random.choice(["Mobile App", "Web Portal", "In-car System", "Voice Assistant"]),
            "ipAddress": f"192.168.1.{random.randint(1, 254)}",
            "authenticationType": random.choice(["Password", "Biometric", "PIN", "OAuth"]),
            "commandOrigin": random.choice(["Local", "Remote"]),
            "retryCount": random.randint(0, 3) if random.random() > 0.8 else 0
        }
        
        return command
    
    def generate_notification(self, vehicle_id):
        """Generate sample notification data"""
        notification_type = random.choice(NOTIFICATION_TYPES)
        created_time = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 168))
        
        # Generate message and parameters based on notification type
        message = ""
        parameters = {}
        
        # Handle safety and emergency notifications
        if notification_type == "emergency_call_initiated":
            message = "Emergency call has been initiated. Help is on the way."
            parameters = {"call_id": f"call-{random.randint(1000, 9999)}"}
        elif notification_type == "airbag_deployed":
            message = "Airbag deployment detected. Emergency services have been notified."
            parameters = {"airbags": ["driver", "passenger"]}
        elif notification_type == "accident_detected":
            message = "Accident detected. Emergency services contacted."
            parameters = {"impact_severity": random.choice(["Low", "Medium", "High"])}
        elif notification_type == "vehicle_stolen_alert":
            message = "Vehicle movement detected while locked. Security alert triggered."
            parameters = {"alert_id": f"security-{random.randint(1000, 9999)}"}
        
        # Handle standard notifications from existing code
        # ...existing code for other notification types...
        
        # Generic handler for standard notification types
        elif notification_type in NOTIFICATION_TYPES:
            if notification_type == "speed_alert":
                speed_limit = random.randint(80, 130)
                message_template = random.choice(ALERT_MESSAGES["speed_alert"])
                message = message_template.format(value=speed_limit)
                parameters = {"speed_limit": speed_limit}
            
            elif notification_type == "low_battery_alert":
                battery_level = random.randint(5, 20)
                message_template = random.choice(ALERT_MESSAGES["low_battery_alert"])
                message = message_template.format(value=battery_level)
                parameters = {"threshold": battery_level}
            
            elif notification_type == "curfew_alert":
                start_time = "22:00"
                end_time = "06:00"
                message_template = random.choice(ALERT_MESSAGES["curfew_alert"])
                message = message_template.format(start_time=start_time, end_time=end_time)
                parameters = {"start_time": start_time, "end_time": end_time}
            
            elif notification_type == "geofence_alert":
                message = random.choice(ALERT_MESSAGES["geofence_alert"])
                parameters = {"latitude": 37.7749, "longitude": -122.4194, "radius": 5.0}
            
            elif notification_type == "security_alert":
                message = random.choice(ALERT_MESSAGES["security_alert"])
            
            elif notification_type == "service_reminder":
                service = random.choice(SERVICE_TYPES)
                message = f"Reminder: {service} service is due soon"
                parameters = {"service_type": service.lower().replace(" ", "_")}
            
            elif notification_type == "system_update":
                message = "System update available for your vehicle"
                parameters = {"version": f"v{random.randint(1, 9)}.{random.randint(0, 9)}.{random.randint(0, 9)}"}
            
            elif notification_type == "low_fuel_alert":
                fuel_level = random.randint(5, 15)
                message = f"Fuel level is low: {fuel_level}%"
                parameters = {"fuel_level": fuel_level}
        
        # Create enhanced notification document
        notification = {
            "id": str(uuid.uuid4()),
            "notificationId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": notification_type,
            "message": message,
            "timestamp": created_time.isoformat(),
            "readTime": (created_time + timedelta(hours=random.randint(1, 24))).isoformat() if random.random() > 0.3 else None,
            "read": random.choice([True, False]),
            "severity": random.choice(NOTIFICATION_PRIORITY),
            "source": random.choice(["Vehicle", "System", "Service", "Emergency", "Security"]),
            "actionRequired": notification_type.endswith("_alert") or "emergency" in notification_type or "accident" in notification_type,
            "actionUrl": "/vehicles/actions/123" if random.random() > 0.5 else None,
            "parameters": parameters,
            "location": {
                "latitude": round(random.uniform(25.0, 49.0), 6),
                "longitude": round(random.uniform(-125.0, -70.0), 6)
            } if random.random() > 0.5 else None,
            "relatedCommands": [f"cmd-{random.randint(1000, 9999)}"] if random.random() > 0.7 else [],
            "targetUsers": [f"User{random.randint(1, 5)}"],
            "phoneNumber": f"+1{random.randint(2000000000, 9999999999)}" if "emergency" in notification_type else None,
            "isTestNotification": random.random() < 0.05  # 5% are test notifications
        }
        
        return notification
    
    def generate_vehicle_status(self, vehicle_id, is_electric=False):
        """Generate sample vehicle status data"""
        battery_level = random.randint(20, 100) if is_electric else random.randint(80, 100)
        
        # Enhanced status for diagnostic and battery agent
        coolant_level = random.randint(60, 100) if not is_electric else None
        oil_temp = random.randint(80, 110) if not is_electric else None
        transmission_temp = random.randint(70, 100) if not is_electric else None
        
        # Enhanced EV-specific data
        ev_specific_data = {}
        if is_electric:
            ev_specific_data = {
                "batteryTemperature": random.randint(15, 40),
                "chargingStatus": random.choice(["Not Charging", "Charging", "Fast Charging"]),
                "chargingPower": random.randint(0, 150) if random.choice(["Charging", "Fast Charging"]) else 0,
                "timeToFullCharge": random.randint(0, 300) if random.choice(["Charging", "Fast Charging"]) else None,
                "chargerType": random.choice(["Home", "Public", "Supercharger", "None"]),
                "batteryHealth": random.randint(80, 100),
                "regenerativeBrakingLevel": random.choice([0, 1, 2, 3]),
                "estimatedRange": random.randint(50, 400)
            }
        
        # Enhanced safety systems status for safety agent
        safety_systems_status = {
            "airbagStatus": random.choice(["OK", "Warning", "Error"]) if random.random() > 0.9 else "OK",
            "absStatus": random.choice(["OK", "Warning", "Error"]) if random.random() > 0.9 else "OK",
            "tractionControlStatus": random.choice(["OK", "Warning", "Error", "Disabled"]) if random.random() > 0.9 else "OK",
            "stabilityControlStatus": random.choice(["OK", "Warning", "Error", "Disabled"]) if random.random() > 0.9 else "OK",
            "emergencyCallStatus": random.choice(["Ready", "Not Ready", "Error"]) if random.random() > 0.9 else "Ready",
            "brakeSystemStatus": random.choice(["OK", "Warning", "Error"]) if random.random() > 0.9 else "OK",
            "tireMonitoringStatus": random.choice(["OK", "Warning", "Error"]) if random.random() > 0.9 else "OK",
            "collisionWarningStatus": random.choice(["OK", "Warning", "Error", "Disabled"]) if random.random() > 0.9 else "OK"
        }
        
        # Enhanced status data with diagnostic information
        return {
            "id": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "batteryLevel": battery_level,
            "temperature": random.randint(18, 32),
            "speed": random.randint(0, 120) if random.random() > 0.3 else 0,
            "oilLevel": 0 if is_electric else random.randint(20, 100),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "location": {
                "latitude": round(random.uniform(25.0, 49.0), 6),
                "longitude": round(random.uniform(-125.0, -70.0), 6)
            },
            "engineStatus": random.choice(["on", "off"]),
            "doorStatus": {
                "driver": random.choice(["locked", "unlocked"]),
                "passenger": random.choice(["locked", "unlocked"]),
                "rearLeft": random.choice(["locked", "unlocked"]),
                "rearRight": random.choice(["locked", "unlocked"])
            },
            "climateSettings": {
                "temperature": random.randint(16, 28),
                "fanSpeed": random.choice(["low", "medium", "high"]),
                "isAirConditioningOn": random.choice([True, False]),
                "isHeatingOn": random.choice([True, False])
            },
            # Enhanced diagnostic data elements
            "coolantTemperature": random.randint(70, 110) if not is_electric else None,
            "coolantLevel": coolant_level,
            "oilTemperature": oil_temp,
            "transmissionTemperature": transmission_temp,
            "brakePadWear": {
                "frontLeft": random.randint(0, 100),
                "frontRight": random.randint(0, 100),
                "rearLeft": random.randint(0, 100),
                "rearRight": random.randint(0, 100)
            },
            "tirePressure": {
                "frontLeft": random.randint(28, 36),
                "frontRight": random.randint(28, 36),
                "rearLeft": random.randint(28, 36),
                "rearRight": random.randint(28, 36)
            },
            "odometer": random.randint(1000, 100000),
            "fuelEconomy": random.randint(15, 40) if not is_electric else None,
            "batteryVoltage": round(random.uniform(12.0, 14.2), 1),
            # EV specific data
            **ev_specific_data,
            # Safety systems status
            "safetySystemsStatus": safety_systems_status,
            # Remote access status
            "remoteAccessStatus": {
                "isConnected": random.choice([True, False]),
                "lastConnectionTime": (datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 60))).isoformat(),
                "signalStrength": random.randint(1, 5)
            },
            # Check engine light and other warning lights
            "warningLights": {
                "checkEngine": random.choice([True, False]) if random.random() < 0.1 else False,
                "oilPressure": random.choice([True, False]) if random.random() < 0.05 else False,
                "batteryWarning": random.choice([True, False]) if random.random() < 0.08 else False,
                "brakeSystem": random.choice([True, False]) if random.random() < 0.03 else False,
                "coolantTemperature": random.choice([True, False]) if random.random() < 0.04 else False
            }
        }
        
    @distributed_trace
    async def create_item_with_retry(self, container, item):
        """Create an item in Cosmos DB with retry logic"""
        retry_count = 0
        while retry_count < self.max_retry_attempts:
            try:
                return await container.create_item(body=item)
            except CosmosHttpResponseError as e:
                if e.status_code == 429:  # Too Many Requests
                    retry_count += 1
                    # Calculate exponential backoff with jitter
                    delay = self.retry_base_delay * (2 ** (retry_count - 1)) + random.uniform(0, 1)
                    logger.warning(f"Rate limited - retry {retry_count}. Waiting {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
                elif e.status_code >= 500:  # Server error
                    retry_count += 1
                    delay = self.retry_base_delay * (2 ** (retry_count - 1)) + random.uniform(0, 1)
                    logger.warning(f"Server error {e.status_code} - retry {retry_count}. Waiting {delay:.2f} seconds...")
                    await asyncio.sleep(delay)
                else:
                    # Other errors we won't retry
                    logger.error(f"Cosmos DB error creating item: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error creating item: {e}")
                raise
                
        # If we get here, we've exhausted retries
        logger.error(f"Max retry attempts reached. Failed to create item.")
        raise Exception("Failed to create item after maximum retry attempts")
    
    @distributed_trace
    async def bulk_create_items(self, container, items, batch_size=100):
        """Create items in batches to optimize throughput"""
        created_count = 0
        error_count = 0
        
        # Process in batches
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            tasks = []
            
            # Create tasks for each item in the batch
            for item in batch:
                tasks.append(self.create_item_with_retry(container, item))
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Count successes and errors
            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                else:
                    created_count += 1
                    
            if i + batch_size < len(items):
                # Add a small delay between batches to avoid rate limiting
                await asyncio.sleep(0.5)
                
        return created_count, error_count
        
    @distributed_trace
    async def generate_status_updates(self, vehicle_id, count, is_electric=False):
        """Generate a series of vehicle status updates over time"""
        # Initial status
        status = self.generate_vehicle_status(vehicle_id, is_electric)
        await self.create_item_with_retry(self.status_container, status)
        
        # Generate status updates with slight changes
        status_updates = []
        battery_level = status["batteryLevel"]
        temperature = status["temperature"]
        speed = status["speed"]
        oil_level = status["oilLevel"]
        
        for i in range(count - 1):
            # Adjust values slightly to simulate changes over time
            battery_level = max(1, min(100, battery_level + random.randint(-5, 3)))
            temperature = max(1, min(40, temperature + random.randint(-2, 2)))
            speed = max(0, min(130, speed + random.randint(-20, 20)))
            oil_level = max(0, min(100, oil_level - random.randint(0, 1)))
            
            status = self.generate_vehicle_status(vehicle_id, is_electric)
            status["batteryLevel"] = battery_level
            status["temperature"] = temperature
            status["speed"] = speed
            status["oilLevel"] = oil_level
            status["timestamp"] = (datetime.now(timezone.utc) + timedelta(minutes=i*5)).isoformat()
            
            status_updates.append(status)
        
        # Bulk insert the status updates
        created_count, error_count = await self.bulk_create_items(self.status_container, status_updates)
        logger.info(f"Generated {created_count} status updates for vehicle {vehicle_id} (errors: {error_count})")
    
    @distributed_trace
    async def generate_and_insert_data(self, num_vehicles, services_per_vehicle, commands_per_vehicle, 
                                      notifications_per_vehicle, status_updates_per_vehicle):
        """Generate and insert sample data"""
        start_time = time.time()
        logger.info(f"Generating data for {num_vehicles} vehicles...")
        
        # Connect to Cosmos DB
        await self.connect()
        
        # Generate vehicles
        vehicles = []
        vehicle_ids = []
        electric_vehicles = set()
        
        for i in range(num_vehicles):
            vehicle = self.generate_vehicle()
            vehicle_id = vehicle["VehicleId"]
            vehicle_ids.append(vehicle_id)
            vehicles.append(vehicle)
            
            # Track which vehicles are electric
            if vehicle["Features"]["IsElectric"]:
                electric_vehicles.add(vehicle_id)
        
        # Bulk insert vehicles
        logger.info(f"Inserting {len(vehicles)} vehicles...")
        created_count, error_count = await self.bulk_create_items(self.vehicles_container, vehicles)
        logger.info(f"Created {created_count} vehicles (errors: {error_count})")
        
        # Store the vehicle IDs for later use
        self.vehicle_ids = vehicle_ids
        
        # Generate services, commands, and notifications for each vehicle
        for vehicle_id in vehicle_ids:
            is_electric = vehicle_id in electric_vehicles
            
            # Generate services
            services = [self.generate_service(vehicle_id, is_electric) for _ in range(services_per_vehicle)]
            if services:
                logger.info(f"Inserting {len(services)} services for vehicle {vehicle_id}...")
                created_count, error_count = await self.bulk_create_items(self.services_container, services)
                logger.debug(f"Created {created_count} services (errors: {error_count})")
            
            # Generate commands
            commands = [self.generate_command(vehicle_id) for _ in range(commands_per_vehicle)]
            if commands:
                logger.info(f"Inserting {len(commands)} commands for vehicle {vehicle_id}...")
                created_count, error_count = await self.bulk_create_items(self.commands_container, commands)
                logger.debug(f"Created {created_count} commands (errors: {error_count})")
            
            # Generate notifications
            notifications = [ self.generate_notification(vehicle_id) for _ in range(notifications_per_vehicle)]
            if notifications:
                logger.info(f"Inserting {len(notifications)} notifications for vehicle {vehicle_id}...")
                created_count, error_count = await self.bulk_create_items(self.notifications_container, notifications)
                logger.debug(f"Created {created_count} notifications (errors: {error_count})")
            
            # Generate status updates
            await self.generate_status_updates(vehicle_id, status_updates_per_vehicle, is_electric)
            
            logger.info(f"Completed data generation for vehicle: {vehicle_id}")
            
        # Generate POIs
        logger.info("Generating points of interest...")
        pois = [self.generate_poi(poi_data) for poi_data in POINTS_OF_INTEREST]
        if pois:
            created_count, error_count = await self.bulk_create_items(self.pois_container, pois)
            logger.info(f"Created {created_count} POIs (errors: {error_count})")
                
        # Generate charging stations
        logger.info("Generating charging stations...")
        stations = [self.generate_charging_station(station_data) for station_data in CHARGING_STATIONS]
        if stations:
            created_count, error_count = await self.bulk_create_items(self.charging_stations_container, stations)
            logger.info(f"Created {created_count} charging stations (errors: {error_count})")
        
        # Add diagnostic reports generation
        logger.info("Generating diagnostic reports...")
        for vehicle_id in vehicle_ids:
            is_electric = vehicle_id in electric_vehicles
            
            # Generate 0-3 diagnostic reports per vehicle
            num_reports = random.randint(0, 3)
            if num_reports > 0:
                reports = [self.generate_diagnostic_report(vehicle_id, is_electric) for _ in range(num_reports)]
                
                # Create a diagnostic_reports container if it doesn't exist yet
                container_id = "diagnostic_reports"
                try:
                    container = self.database.get_container_client(container_id)
                    await container.read()
                except CosmosResourceNotFoundError:
                    logger.info(f"Creating container: {container_id}")
                    try:
                        # Create container without specifying throughput for serverless accounts
                        await self.database.create_container(
                            id=container_id,
                            partition_key=PartitionKey(path="/vehicleId")
                        )
                        logger.info(f"Created diagnostic_reports container")
                    except Exception as e:
                        logger.error(f"Failed to create diagnostic_reports container: {e}")
                        continue
                    container = self.database.get_container_client(container_id)
                    
                # Insert the reports
                for report in reports:
                    try:
                        await container.create_item(body=report)
                        logger.debug(f"Created diagnostic report {report['reportId']} for vehicle {vehicle_id}")
                    except Exception as e:
                        logger.error(f"Error creating diagnostic report: {e}")
                
                logger.info(f"Generated {len(reports)} diagnostic reports for vehicle {vehicle_id}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"Sample data generation complete in {elapsed_time:.2f} seconds!")
        
        # Generate summary report
        summary = {
            "vehicles": len(vehicle_ids),
            "electric_vehicles": len(electric_vehicles),
            "services": services_per_vehicle * len(vehicle_ids),
            "commands": commands_per_vehicle * len(vehicle_ids),
            "notifications": notifications_per_vehicle * len(vehicle_ids),
            "status_updates": status_updates_per_vehicle * len(vehicle_ids),
            "pois": len(POINTS_OF_INTEREST),
            "charging_stations": len(CHARGING_STATIONS),
            "total_documents": (
                len(vehicle_ids) + 
                (services_per_vehicle * len(vehicle_ids)) + 
                (commands_per_vehicle * len(vehicle_ids)) + 
                (notifications_per_vehicle * len(vehicle_ids)) + 
                (status_updates_per_vehicle * len(vehicle_ids)) + 
                len(POINTS_OF_INTEREST) + 
                len(CHARGING_STATIONS)
            ),
            "elapsed_seconds": elapsed_time
        }
        
        logger.info(f"Generation summary: {json.dumps(summary, indent=2)}")
        await self.close()
        
    @distributed_trace
    async def generate_live_data(self, duration_minutes=60, update_interval_seconds=30):
        """Generate live data updates for a specified duration with improved reliability"""
        start_time = time.time()
        logger.info(f"Generating live data updates for {duration_minutes} minutes...")
        
        # Connect to Cosmos DB
        await self.connect()
        
        # Make sure we have vehicle IDs
        if not self.vehicle_ids:
            try:
                # Get vehicles from DB with retry
                for retry in range(self.max_retry_attempts):
                    try:
                        query = "SELECT c.VehicleId FROM c"
                        items = self.vehicles_container.query_items(query=query, enable_cross_partition_query=True)
                        
                        async for vehicle in items:
                            self.vehicle_ids.append(vehicle["VehicleId"])
                        
                        if not self.vehicle_ids:
                            logger.error("No vehicles found in database!")
                            return
                        
                        break  # Exit retry loop if successful
                    except Exception as e:
                        if retry == self.max_retry_attempts - 1:
                            logger.error(f"Failed to get vehicles after {self.max_retry_attempts} attempts: {str(e)}")
                            return
                        delay = self.retry_base_delay * (2 ** retry) + random.uniform(0, 1)
                        logger.warning(f"Failed to get vehicles (attempt {retry+1}): {str(e)}. Retrying in {delay:.2f}s...")
                        await asyncio.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Failed to get vehicles: {str(e)}")
                return
                
        # Get electric vehicle status
        electric_vehicles = set()
        try:
            query = "SELECT c.VehicleId FROM c WHERE c.Features.IsElectric = true"
            items = self.vehicles_container.query_items(query=query, enable_cross_partition_query=True)
            
            async for vehicle in items:
                electric_vehicles.add(vehicle["VehicleId"])
                
        except Exception as e:
            logger.error(f"Failed to get electric vehicles: {str(e)}")
        
        # Calculate how many updates to generate
        total_updates = (duration_minutes * 60) // update_interval_seconds
        
        # Get the current statuses for all vehicles
        vehicle_statuses = {}
        for vehicle_id in self.vehicle_ids:
            try:
                query = f"SELECT TOP 1 * FROM c WHERE c.vehicleId = '{vehicle_id}' ORDER BY c.timestamp DESC"
                items = self.status_container.query_items(query=query, enable_cross_partition_query=True)
                
                async for item in items:
                    vehicle_statuses[vehicle_id] = {
                        "batteryLevel": item.get("batteryLevel", random.randint(20, 100)),
                        "temperature": item.get("temperature", random.randint(18, 32)),
                        "speed": item.get("speed", 0),
                        "oilLevel": item.get("oilLevel", random.randint(20, 100)),
                        "engineStatus": item.get("engineStatus", "off"),
                        "is_electric": vehicle_id in electric_vehicles
                    }
                    break
            except Exception as e:
                logger.error(f"Failed to get status for vehicle {vehicle_id}: {str(e)}")
                # Create default status
                vehicle_statuses[vehicle_id] = {
                    "batteryLevel": random.randint(20, 100),
                    "temperature": random.randint(18, 32),
                    "speed": 0,
                    "oilLevel": random.randint(20, 100) if vehicle_id not in electric_vehicles else 0,
                    "engineStatus": "off",
                    "is_electric": vehicle_id in electric_vehicles
                }
        
        # Generate and insert status updates in real-time
        end_time = start_time + (duration_minutes * 60)
        
        # Status counters for monitoring
        update_count = 0
        error_count = 0
        batch_size = min(len(self.vehicle_ids), 10)  # Process 10 vehicles at a time
        
        try:
            while time.time() < end_time:
                batch_start = time.time()
                batch_updates = []
                
                # For each vehicle, generate a new status update
                for vehicle_id in self.vehicle_ids:
                    status_data = vehicle_statuses[vehicle_id]
                    is_electric = status_data["is_electric"]
                    
                    # Decide if the vehicle is active
                    is_active = random.random() > 0.6  # 40% chance of being active
                   
                    if is_active:
                        # If the engine is off, start it sometimes
                        if status_data["engineStatus"] == "off" and random.random() > 0.7:
                            status_data["engineStatus"] = "on"
                            status_data["speed"] = random.randint(5, 30)
                        
                        # If the engine is on, update speed
                        if status_data["engineStatus"] == "on":
                            # Sometimes change speed significantly
                            if random.random() > 0.8:
                                status_data["speed"] = max(0, min(130, status_data["speed"] + random.randint(-30, 30)))
                            else:
                                # Small speed adjustments
                                status_data["speed"] = max(0, min(130, status_data["speed"] + random.randint(-10, 10)))
                                
                            # Sometimes stop the vehicle
                            if random.random() > 0.9:
                                status_data["speed"] = 0
                                if random.random() > 0.5:
                                    status_data["engineStatus"] = "off"
                    
                    # Update battery level
                    if is_electric:
                        # Electric vehicles drain battery while driving
                        if status_data["engineStatus"] == "on" and status_data["speed"] > 0:
                            status_data["batteryLevel"] = max(1, status_data["batteryLevel"] - random.randint(0, 2))
                        # Sometimes they charge
                        elif random.random() > 0.8:
                            status_data["batteryLevel"] = min(100, status_data["batteryLevel"] + random.randint(1, 3))
                    else:
                        # Regular vehicles drain oil while driving
                        if status_data["engineStatus"] == "on" and status_data["speed"] > 0:
                            status_data["oilLevel"] = max(0, status_data["oilLevel"] - random.uniform(0, 0.3))
                
                # Update temperature
                status_data["temperature"] = max(10, min(40, status_data["temperature"] + random.randint(-1, 1)))
                
                # Create new status document
                status = {
                    "id": str(uuid.uuid4()),
                    "vehicleId": vehicle_id,
                    "batteryLevel": round(status_data["batteryLevel"]),
                    "temperature": status_data["temperature"],
                    "speed": status_data["speed"],
                    "oilLevel": round(status_data["oilLevel"]) if not is_electric else 0,
                    "engineStatus": status_data["engineStatus"],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "location": {
                        "latitude": round(random.uniform(25.0, 49.0), 6),
                        "longitude": round(random.uniform(-125.0, -70.0), 6)
                    },
                    "doorStatus": {
                        "driver": random.choice(["locked", "unlocked"]),
                        "passenger": random.choice(["locked", "unlocked"]),
                        "rearLeft": random.choice(["locked", "unlocked"]),
                        "rearRight": random.choice(["locked", "unlocked"])
                    },
                    "climateSettings": {
                        "temperature": random.randint(16, 28),
                        "fanSpeed": random.choice(["low", "medium", "high"]),
                        "isAirConditioningOn": random.choice([True, False]),
                        "isHeatingOn": random.choice([True, False])
                    }
                }
                
                batch_updates.append(status)
                
                # Process batch updates with retries
                if batch_updates:
                    created, failed = await self.bulk_create_items(
                        self.status_container, 
                        batch_updates, 
                        batch_size=batch_size
                    )
                    update_count += created
                    error_count += failed
                
                # Report status periodically
                if update_count % 100 == 0 and update_count > 0:
                    elapsed = time.time() - start_time
                    rate = update_count / elapsed if elapsed > 0 else 0
                    remaining = end_time - time.time()
                    logger.info(
                        f"Generated {update_count} status updates "
                        f"({error_count} errors, {rate:.1f} updates/sec, "
                        f"{remaining:.1f} seconds remaining)"
                    )
                
                # Calculate sleep time to maintain the update interval
                batch_duration = time.time() - batch_start
                sleep_time = max(0, update_interval_seconds - batch_duration)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
        
        except KeyboardInterrupt:
            logger.info("Live data generation interrupted by user")
        except Exception as e:
            logger.error(f"Error during live data generation: {e}")
        finally:
            total_time = time.time() - start_time
            logger.info(
                f"Live data generation complete! "
                f"Generated {update_count} updates over {total_time:.1f} seconds "
                f"({error_count} errors)"
            )
            await self.close()

    def generate_poi(self, poi_data):
        """Generate a Point of Interest document from the sample data"""
        return {
            "id": str(uuid.uuid4()),
            "poiId": str(uuid.uuid4()),
            "name": poi_data["name"],
            "category": poi_data["category"],
            "rating": poi_data["rating"],
            "location": {
                "latitude": round(random.uniform(25.0, 49.0), 6),
                "longitude": round(random.uniform(-125.0, -70.0), 6)
            },
            "address": f"{random.randint(100, 999)} Example St, City, State",
            "description": f"Description for {poi_data['name']}",
            "openingHours": f"{random.randint(7, 10)}:00 - {random.randint(17, 22)}:00",
            "amenities": random.sample(["Parking", "WiFi", "Restrooms", "Food", "Shopping"], random.randint(1, 4)),
            "photos": [f"photo{i}.jpg" for i in range(1, random.randint(2, 6))],
            "contact": {
                "phone": f"+1{random.randint(2000000000, 9999999999)}",
                "email": f"info@{poi_data['name'].lower().replace(' ', '')}.example.com",
                "website": f"https://www.{poi_data['name'].lower().replace(' ', '')}.example.com"
            },
            "priceLevel": random.randint(1, 4),
            "tags": random.sample(["family-friendly", "outdoor", "indoor", "historic", "modern", "quiet", "lively"], random.randint(1, 4)),
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }

    def generate_charging_station(self, station_data):
        """Generate a Charging Station document from the sample data"""
        regions = ["North America", "Europe", "Asia", "South America", "Australia"]
        
        # Calculate number of charging points based on ports
        charging_points = []
        for i in range(station_data["ports"]):
            status = random.choice(["Available", "In Use", "Out of Order", "Reserved"])
            charging_points.append({
                "pointId": f"point-{random.randint(1000, 9999)}",
                "connectorType": random.choice(["CCS", "CHAdeMO", "Type 2", "Tesla"]),
                "status": status,
                "power": random.choice([7.4, 11, 22, 50, 150, 350]),
                "lastStatusUpdate": datetime.now(timezone.utc).isoformat()
            })
        
        return {
            "id": str(uuid.uuid4()),
            "stationId": str(uuid.uuid4()),
            "name": station_data["name"],
            "powerLevel": station_data["power_level"],
            "region": random.choice(regions),
            "location": {
                "latitude": round(random.uniform(25.0, 49.0), 6),
                "longitude": round(random.uniform(-125.0, -70.0), 6),
                "address": f"{random.randint(100, 999)} Example St, City, State"
            },
            "provider": random.choice(CHARGING_NETWORK_PROVIDERS),
            "totalPorts": station_data["ports"],
            "availablePorts": sum(1 for point in charging_points if point["status"] == "Available"),
            "chargingPoints": charging_points,
            "amenities": random.sample(CHARGING_STATION_AMENITIES, random.randint(1, 5)),
            "paymentOptions": random.sample(["Credit Card", "Mobile App", "RFID Card", "Contactless"], random.randint(1, 3)),
            "openingHours": random.choice(["24/7", "6:00 - 22:00", "7:00 - 23:00"]),
            "pricing": {
                "perKwh": round(random.uniform(0.25, 0.60), 2),
                "perMinute": round(random.uniform(0.10, 0.30), 2),
                "connectionFee": round(random.uniform(0, 2.0), 2)
            },
            "userRating": round(random.uniform(2.5, 5.0), 1),
            "status": random.choice(["Operational", "Partial Service", "Under Maintenance"]),
            "lastUpdated": datetime.now(timezone.utc).isoformat()
        }

    def generate_diagnostic_report(self, vehicle_id, is_electric=False):
        """Generate a diagnostic report for a vehicle"""
        report_timestamp = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90))
        
        # Define general diagnostic status fields
        general_diagnostics = {
            "overallStatus": random.choice(["Good", "Fair", "Poor", "Critical"]),
            "mileage": random.randint(1000, 100000),
            "reportGeneratedBy": random.choice(["Onboard System", "Service Center", "Mobile Technician"]),
            "nextServiceDue": (report_timestamp + timedelta(days=random.randint(30, 365))).isoformat(),
            "recallsOutstanding": random.choice([True, False]),
            "dtcCodes": []  # Diagnostic Trouble Codes
        }
        
        # Add some DTCs if appropriate
        if general_diagnostics["overallStatus"] in ["Fair", "Poor", "Critical"]:
            dtc_count = random.randint(1, 5 if general_diagnostics["overallStatus"] == "Critical" else 3)
            dtc_prefixes = ["P0", "P1", "C0", "B0", "U0"]
            
            for _ in range(dtc_count):
                code = f"{random.choice(dtc_prefixes)}{random.randint(100, 999)}"
                description = f"Issue detected in {random.choice(['engine', 'transmission', 'brakes', 'electrical', 'emissions', 'body', 'chassis'])} system"
                severity = "High" if general_diagnostics["overallStatus"] == "Critical" else random.choice(["Low", "Medium", "High"])
                
                general_diagnostics["dtcCodes"].append({
                    "code": code,
                    "description": description,
                    "severity": severity,
                    "firstDetected": (report_timestamp - timedelta(days=random.randint(1, 30))).isoformat(),
                    "status": random.choice(["Active", "Pending", "History"])
                })
        
        # Create type-specific diagnostics based on vehicle type
        if is_electric:
            type_specific_diagnostics = {
                "batteryHealth": random.randint(70, 100),
                "estimatedRange": random.randint(150, 400),
                "batteryCapacity": random.randint(80, 100),
                "chargingSystemStatus": random.choice(["Good", "Fair", "Poor"]),
                "regenerativeBrakingEfficiency": random.randint(85, 100),
                "highVoltageSystemStatus": random.choice(["Normal", "Warning", "Fault"]),
                "insulationResistance": random.randint(1, 10) * 100,  # kOhm
                "batteryTemperature": random.randint(15, 40),
                "thermalManagementSystem": random.choice(["Normal", "Degraded", "Fault"]),
                "cellBalanceStatus": random.choice(["Balanced", "Unbalanced", "Severely Unbalanced"])
            }
        else:
            type_specific_diagnostics = {
                "engineHealth": random.randint(70, 100),
                "compressionTest": random.choice(["Pass", "Warn", "Fail", "Not Tested"]),
                "fuelSystemStatus": random.choice(["Good", "Fair", "Poor"]),
                "emissionsStatus": random.choice(["Pass", "Fail"]),
                "exhaustGasRecirculation": random.choice(["Normal", "Restricted", "Fault"]),
                "oilQuality": random.randint(60, 100),
                "transmissionFluidStatus": random.choice(["Good", "Fair", "Poor", "Not Checked"]),
                "ignitionSystemStatus": random.choice(["Normal", "Degraded", "Fault"]),
                "fuelEfficiency": random.randint(80, 100),  # percent of expected
                "airFuelRatio": random.choice(["Optimal", "Rich", "Lean"])
            }
        
        # Common systems for all vehicles
        common_systems = {
            "brakeSystem": {
                "frontBrakes": random.randint(60, 100),
                "rearBrakes": random.randint(60, 100),
                "brakeFluid": random.choice(["Normal", "Low", "Contaminated"]),
                "abs": random.choice(["Operational", "Fault"])
            },
            "steeringSystem": random.choice(["Normal", "Needs Attention", "Faulty"]),
            "suspension": random.choice(["Good", "Fair", "Poor"]),
            "cooling": random.choice(["Normal", "Overheating", "Leak Detected"]),
            "electricalSystem": {
                "12vBattery": random.randint(60, 100),
                "alternator": random.choice(["Normal", "Low Output", "Fault"]),
                "starterMotor": random.choice(["Normal", "Weak", "Fault"])
            },
            "tireCondition": {
                "frontLeft": random.randint(60, 100),
                "frontRight": random.randint(60, 100),
                "rearLeft": random.randint(60, 100),
                "rearRight": random.randint(60, 100),
                "spare": random.choice(["Good", "Fair", "Poor", "Not Applicable"])
            },
            "lightingSystem": random.choice(["All Functional", "Bulb Replacement Needed", "Electrical Issue"]),
            "fluidLevels": {
                "washerFluid": random.choice(["Full", "Low", "Empty"]),
                "coolant": random.choice(["Normal", "Low", "Empty"]),
                "powerSteering": random.choice(["Normal", "Low", "Not Applicable"])
            }
        }
        
        # Create recommended actions
        recommended_actions = []
        for _ in range(random.randint(0, 3)):
            action = {
                "action": random.choice([
                    "Schedule maintenance", 
                    "Replace part", 
                    "Software update",
                    "Monitor condition", 
                    "No action required"
                ]),
                "priority": random.choice(["Low", "Medium", "High", "Critical"]),
                "estimatedCost": round(random.uniform(0, 1000), 2) if random.random() > 0.3 else None
            }
            recommended_actions.append(action)
            
        # Technician notes
        technician_notes = random.choice([
            "All systems operating within normal parameters.",
            "Minor issues detected, monitor at next service.",
            "Several systems require attention soon.",
            "Immediate attention required for critical systems.",
            ""
        ]) if random.random() > 0.3 else ""
        
        # Combine all diagnostics into a single report
        return {
            "id": str(uuid.uuid4()),
            "reportId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "timestamp": report_timestamp.isoformat(),
            "isElectric": is_electric,
            "generalDiagnostics": general_diagnostics,
            "specificDiagnostics": type_specific_diagnostics,
            "commonSystems": common_systems,
            "recommendedActions": recommended_actions,
            "technicianNotes": technician_notes
        }
    
    async def create_container_if_not_exists(self, container_id, partition_key_path, ttl=-1):
        """Create a container if it doesn't exist yet"""
        try:
            container = self.database.get_container_client(container_id)
            await container.read()
            return container
        except CosmosResourceNotFoundError:
            logger.info(f"Creating container: {container_id}")
            try:
                # Create container without specifying throughput for serverless accounts
                await self.database.create_container(
                    id=container_id,
                    partition_key=PartitionKey(path=partition_key_path),
                    default_ttl=ttl
                )
                logger.info(f"Created {container_id} container")
                return self.database.get_container_client(container_id)
            except Exception as e:
                logger.error(f"Failed to create {container_id} container: {e}")
                raise

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Generate sample data for Connected Vehicle Platform')
    parser.add_argument('--vehicles', type=int, default=10,
                        help='Number of vehicles to generate (default: 10)')
    parser.add_argument('--services', type=int, default=5,
                        help='Number of services per vehicle (default: 5)')
    parser.add_argument('--commands', type=int, default=10,
                        help='Number of commands per vehicle (default: 10)')
    parser.add_argument('--notifications', type=int, default=10,
                        help='Number of notifications per vehicle (default: 10)')
    parser.add_argument('--status-updates', type=int, default=20,
                        help='Number of status updates per vehicle (default: 20)')
    parser.add_argument('--live', action='store_true',
                        help='Generate live data instead of static data')
    parser.add_argument('--duration', type=int, default=60,
                        help='Duration in minutes for live data generation (default: 60)')
    parser.add_argument('--interval', type=int, default=30,
                        help='Update interval in seconds for live data generation (default: 30)')
    parser.add_argument('--env-file', type=str, default='.env',
                        help='Path to .env file (default: .env)')

    return parser.parse_args()

async def main():
    """Main entry point for the script"""
    args = parse_args()
    
    # Load environment variables
    load_dotenv(override=True)
    
    # Validate required environment variables
    required_vars = ["COSMOS_DB_ENDPOINT", "COSMOS_DB_DATABASE"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set them in your .env file or environment")
        sys.exit(1)
    
    # Create data generator
    generator = CosmosDataGenerator()
    
    try:
        if args.live:
            logger.info(f"Generating live data for {args.duration} minutes with {args.interval}s interval")
            await generator.generate_live_data(args.duration, args.interval)
        else:
            logger.info(f"Generating static data for {args.vehicles} vehicles")
            logger.info(f"Services per vehicle: {args.services}")
            logger.info(f"Commands per vehicle: {args.commands}")
            logger.info(f"Notifications per vehicle: {args.notifications}")
            logger.info(f"Status updates per vehicle: {args.status_updates}")
            
            await generator.generate_and_insert_data(
                args.vehicles,
                args.services,
                args.commands,
                args.notifications,
                args.status_updates
            )
    except KeyboardInterrupt:
        logger.info("Data generation interrupted by user")
    except Exception as e:
        logger.error(f"Error during data generation: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Make sure we properly close the connection
        await generator.close()

if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main())
