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
from datetime import datetime, timedelta, timezone
import asyncio
from dotenv import load_dotenv
import logging
import time
from azure.cosmos.aio import CosmosClient
from azure.core.exceptions import ResourceExistsError, AzureError
from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.cosmos import PartitionKey

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
NOTIFICATION_TYPES = ["ServiceDue", "LowFuel", "LowBattery", "SecurityAlert", "SystemUpdate"]
NOTIFICATION_PRIORITY = ["Low", "Medium", "High", "Critical"]

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
        
        logger.info("Cosmos DB data generator initialized")
    
    async def connect(self):
        """Connect to Cosmos DB"""
        if not all([self.endpoint, self.database_name]):
            logger.error("Cosmos DB connection information missing. Please check environment variables.")
            sys.exit(1)

        try:
            # choose auth method
            if self.use_aad_auth:
                credential = DefaultAzureCredential()
                self.client = CosmosClient(self.endpoint, credential=credential)
            else:
                try:
                    self.client = CosmosClient(self.endpoint, credential=self.key)
                except AzureError as e:
                    # detect disabled local auth
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
        except Exception as e:
            logger.error(f"Failed to connect to Cosmos DB: {e}")
            sys.exit(1)
    
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
            except CosmosResourceNotFoundError:
                logger.info(f"Creating container: {container_id}")
                await self.database.create_container(
                    id=container_id,
                    partition_key=PartitionKey(path=pk)
                )
        # re-initialize container references
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
        
        return {
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
            "CurrentTelemetry": {
                "Speed": random.randint(0, 80),
                "EngineTemp": random.randint(170, 220) if not is_electric else 0,
                "OilLevel": random.randint(30, 100) if not is_electric else 0,
                "TirePressure": {
                    "FrontLeft": random.randint(32, 36),
                    "FrontRight": random.randint(32, 36),
                    "RearLeft": random.randint(32, 36),
                    "RearRight": random.randint(32, 36)
                }
            }
        }
    
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
        
        return {
            "id": str(uuid.uuid4()),
            "ServiceCode": service_type.replace(" ", "_").upper(),
            "Description": f"{service_type} service",
            "StartDate": service_date.isoformat(),
            "EndDate": next_service_date.isoformat(),
            "vehicleId": vehicle_id,
            "mileage": random.randint(1000, 100000),
            "cost": round(random.uniform(20.0, 500.0), 2),
            "location": f"Service Center {random.randint(1, 20)}",
            "technician": f"Technician {random.randint(1, 50)}",
            "notes": "Regular maintenance completed",
            "invoiceNumber": f"INV-{random.randint(10000, 99999)}"
        }
    
    def generate_command(self, vehicle_id):
        """Generate sample command data"""
        command_type = random.choice(COMMAND_TYPES)
        sent_time = datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 1440))
        executed_time = sent_time + timedelta(minutes=random.randint(1, 10))
        
        parameters = {}
        if command_type == "SetTemperature":
            parameters["temperature"] = random.randint(65, 85)
        
        return {
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
            "priority": random.choice(["Low", "Normal", "High"])
        }
    
    def generate_notification(self, vehicle_id):
        """Generate sample notification data"""
        notification_type = random.choice(NOTIFICATION_TYPES)
        created_time = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 168))
        
        return {
            "id": str(uuid.uuid4()),
            "notificationId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": notification_type,
            "message": f"{notification_type} alert for your vehicle",
            "timestamp": created_time.isoformat(),
            "readTime": (created_time + timedelta(hours=random.randint(1, 24))).isoformat() if random.random() > 0.3 else None,
            "read": random.choice([True, False]),
            "severity": random.choice(NOTIFICATION_PRIORITY).lower(),
            "source": random.choice(["Vehicle", "System", "Service"]),
            "actionRequired": random.choice([True, False]),
            "actionUrl": "/vehicles/actions/123" if random.random() > 0.5 else None
        }
    
    def generate_vehicle_status(self, vehicle_id, is_electric=False):
        """Generate sample vehicle status data"""
        battery_level = random.randint(20, 100) if is_electric else random.randint(80, 100)
        
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
            }
        }
        
    def generate_poi(self, poi_data):
        """Generate a point of interest with location data"""
        latitude = round(random.uniform(25.0, 49.0), 6)
        longitude = round(random.uniform(-125.0, -70.0), 6)
        
        return {
            "id": str(uuid.uuid4()),
            "name": poi_data["name"],
            "category": poi_data["category"],
            "rating": poi_data["rating"],
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "address": f"{random.randint(100, 999)} Example St, City, State, ZIP",
            "hours": "9:00 AM - 9:00 PM",
            "phone": f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            "website": f"https://example.com/{poi_data['name'].lower().replace(' ', '-')}",
            "features": {
                "hasParking": random.choice([True, False]),
                "isAccessible": random.choice([True, False]),
                "acceptsReservations": random.choice([True, False])
            }
        }
        
    def generate_charging_station(self, station_data):
        """Generate a charging station with location data"""
        latitude = round(random.uniform(25.0, 49.0), 6)
        longitude = round(random.uniform(-125.0, -70.0), 6)
        
        return {
            "id": str(uuid.uuid4()),
            "name": station_data["name"],
            "power_level": station_data["power_level"],
            "location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "available_ports": random.randint(0, station_data["ports"]),
            "total_ports": station_data["ports"],
            "provider": random.choice(["ChargePoint", "Electrify America", "EVgo", "Tesla Supercharger", "Blink"]),
            "cost_per_kwh": round(random.uniform(0.20, 0.50), 2),
            "region": random.choice(["North America", "Europe", "Asia"]),
            "address": f"{random.randint(100, 999)} Charging St, City, State, ZIP",
            "access_hours": "24/7" if random.random() > 0.3 else "6:00 AM - 10:00 PM",
            "is_operational": random.random() > 0.1,  # 90% chance of being operational
            "connector_types": ["CCS", "CHAdeMO", "J1772"]
        }
        
    async def generate_status_updates(self, vehicle_id, count, is_electric=False):
        """Generate a series of vehicle status updates over time"""
        # Initial status
        status = self.generate_vehicle_status(vehicle_id, is_electric)
        await self.status_container.create_item(body=status)
        
        # Generate status updates with slight changes
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
            
            await self.status_container.create_item(body=status)
            
            # Add a small delay to avoid rate limiting
            await asyncio.sleep(0.05)
            
        logger.info(f"Generated {count} status updates for vehicle {vehicle_id}")
        
    async def generate_and_insert_data(self, num_vehicles, services_per_vehicle, commands_per_vehicle, 
                                      notifications_per_vehicle, status_updates_per_vehicle):
        """Generate and insert sample data"""
        logger.info(f"Generating data for {num_vehicles} vehicles...")
        
        # Connect to Cosmos DB
        await self.connect()
        
        # Generate and insert vehicles
        vehicle_ids = []
        electric_vehicles = set()
        
        for i in range(num_vehicles):
            vehicle = self.generate_vehicle()
            vehicle_id = vehicle["VehicleId"]
            vehicle_ids.append(vehicle_id)
            
            # Track which vehicles are electric
            if vehicle["Features"]["IsElectric"]:
                electric_vehicles.add(vehicle_id)
            
            try:
                await self.vehicles_container.create_item(body=vehicle)
                logger.info(f"Created vehicle {i+1}/{num_vehicles}: {vehicle_id}")
            except Exception as e:
                logger.error(f"Failed to create vehicle: {str(e)}")
        
        # Store the vehicle IDs for later use
        self.vehicle_ids = vehicle_ids
        
        # Generate and insert related data for each vehicle
        for vehicle_id in vehicle_ids:
            is_electric = vehicle_id in electric_vehicles
            
            # Services
            for i in range(services_per_vehicle):
                service = self.generate_service(vehicle_id, is_electric)
                try:
                    await self.services_container.create_item(body=service)
                except Exception as e:
                    logger.error(f"Failed to create service: {str(e)}")
            
            # Commands
            for i in range(commands_per_vehicle):
                command = self.generate_command(vehicle_id)
                try:
                    await self.commands_container.create_item(body=command)
                except Exception as e:
                    logger.error(f"Failed to create command: {str(e)}")
            
            # Notifications
            for i in range(notifications_per_vehicle):
                notification = self.generate_notification(vehicle_id)
                try:
                    await self.notifications_container.create_item(body=notification)
                except Exception as e:
                    logger.error(f"Failed to create notification: {str(e)}")
            
            # Status updates
            await self.generate_status_updates(vehicle_id, status_updates_per_vehicle, is_electric)
            
            logger.info(f"Created related data for vehicle: {vehicle_id}")
            
        # Generate POIs
        logger.info("Generating points of interest...")
        for poi_data in POINTS_OF_INTEREST:
            poi = self.generate_poi(poi_data)
            try:
                await self.pois_container.create_item(body=poi)
            except Exception as e:
                logger.error(f"Failed to create POI: {str(e)}")
                
        # Generate charging stations
        logger.info("Generating charging stations...")
        for station_data in CHARGING_STATIONS:
            station = self.generate_charging_station(station_data)
            try:
                await self.charging_stations_container.create_item(body=station)
            except Exception as e:
                logger.error(f"Failed to create charging station: {str(e)}")
        
        await self.close()
        logger.info("Sample data generation complete!")
        
    async def generate_live_data(self, duration_minutes=60, update_interval_seconds=30):
        """Generate live data updates for a specified duration"""
        logger.info(f"Generating live data updates for {duration_minutes} minutes...")
        
        # Connect to Cosmos DB
        await self.connect()
        
        # Make sure we have vehicle IDs
        if not self.vehicle_ids:
            try:
                # Get vehicles from DB
                query = "SELECT c.VehicleId FROM c"
                vehicles = self.vehicles_container.query_items(
                    query=query
                )
                
                async for vehicle in vehicles:
                    self.vehicle_ids.append(vehicle["VehicleId"])
                    
                if not self.vehicle_ids:
                    logger.error("No vehicles found in database!")
                    return
                    
            except Exception as e:
                logger.error(f"Failed to get vehicles: {str(e)}")
                return
                
        # Get electric vehicle status
        electric_vehicles = set()
        try:
            query = "SELECT c.VehicleId FROM c WHERE c.Features.IsElectric = true"
            vehicles = self.vehicles_container.query_items(
                query=query
            )
            
            async for vehicle in vehicles:
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
                items = self.status_container.query_items(
                    query=query
                )
                
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
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        update_count = 0
        while time.time() < end_time:
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
                
                try:
                    await self.status_container.create_item(body=status)
                    update_count += 1
                except Exception as e:
                    logger.error(f"Failed to create status update: {str(e)}")
            
            # Log progress periodically
            if update_count % 100 == 0:
                logger.info(f"Generated {update_count} status updates...")
                
            # Wait for the next update interval
            await asyncio.sleep(update_interval_seconds)
        
        total_time = time.time() - start_time
        logger.info(f"Live data generation complete! Generated {update_count} updates over {total_time:.1f} seconds")
        await self.close()

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Generate sample data for Cosmos DB')
    parser.add_argument('--vehicles', type=int, default=10, help='Number of vehicles to generate')
    parser.add_argument('--services', type=int, default=5, help='Number of services per vehicle')
    parser.add_argument('--commands', type=int, default=8, help='Number of commands per vehicle')
    parser.add_argument('--notifications', type=int, default=12, help='Number of notifications per vehicle')
    parser.add_argument('--status-updates', type=int, default=20, help='Number of status updates per vehicle')
    parser.add_argument('--live', action='store_true', help='Generate live data updates')
    parser.add_argument('--duration', type=int, default=60, help='Duration in minutes for live data generation')
    parser.add_argument('--interval', type=int, default=30, help='Update interval in seconds for live data')
    parser.add_argument('--use-aad', action='store_true', help='Use Azure AD authentication instead of master key')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv(override=True)
    endpoint = os.getenv("COSMOS_DB_ENDPOINT")
    print(f"Using Cosmos DB endpoint: {endpoint}")
    
    # Set AAD auth environment variable if requested
    if args.use_aad:
        os.environ["COSMOS_DB_USE_AAD"] = "true"
    
    generator = CosmosDataGenerator()
    
    if args.live:
        await generator.generate_live_data(args.duration, args.interval)
    else:
        await generator.generate_and_insert_data(
            args.vehicles,
            args.services,
            args.commands,
            args.notifications,
            args.status_updates
        )

if __name__ == "__main__":
    asyncio.run(main())
    # Example usage:
    # python cosmos_data_generator.py --vehicles 20 --services 3 --commands 5 --notifications 10 --status-updates 20
    # For live data:
    # python cosmos_data_generator.py --live --duration 60 --interval 30
