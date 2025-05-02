"""
Sample data generator for Cosmos DB.

This script generates and inserts sample data for the Connected Vehicle Platform:
- Vehicles
- Services
- Commands
- Notifications
"""

import os
import sys
import argparse
import random
import uuid
from datetime import datetime, timedelta
import asyncio
from dotenv import load_dotenv
import logging
from azure.cosmos.aio import CosmosClient
from azure.core.exceptions import ResourceExistsError

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

class CosmosDataGenerator:
    """Generator for Cosmos DB sample data"""
    
    def __init__(self):
        """Initialize the data generator"""
        self.endpoint = os.getenv("COSMOS_DB_ENDPOINT")
        self.key = os.getenv("COSMOS_DB_KEY")
        self.database_name = os.getenv("COSMOS_DB_DATABASE")
        
        # Container names
        self.vehicles_container_name = os.getenv("COSMOS_DB_CONTAINER_VEHICLES")
        self.services_container_name = os.getenv("COSMOS_DB_CONTAINER_SERVICES")
        self.commands_container_name = os.getenv("COSMOS_DB_CONTAINER_COMMANDS")
        self.notifications_container_name = os.getenv("COSMOS_DB_CONTAINER_NOTIFICATIONS")
        
        # Client will be initialized in the connect method
        self.client = None
        self.database = None
        self.vehicles_container = None
        self.services_container = None
        self.commands_container = None
        self.notifications_container = None
        
        logger.info("Cosmos DB data generator initialized")
    
    async def connect(self):
        """Connect to Cosmos DB"""
        if not all([self.endpoint, self.key, self.database_name]):
            logger.error("Cosmos DB connection information missing. Please check environment variables.")
            sys.exit(1)
            
        try:
            # Initialize client
            self.client = CosmosClient(self.endpoint, credential=self.key)
            self.database = self.client.get_database_client(self.database_name)
            
            # Get container clients
            self.vehicles_container = self.database.get_container_client(self.vehicles_container_name)
            self.services_container = self.database.get_container_client(self.services_container_name)
            self.commands_container = self.database.get_container_client(self.commands_container_name)
            self.notifications_container = self.database.get_container_client(self.notifications_container_name)
            
            logger.info("Successfully connected to Cosmos DB")
        except Exception as e:
            logger.error(f"Failed to connect to Cosmos DB: {str(e)}")
            sys.exit(1)
    
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
        
        return {
            "id": str(uuid.uuid4()),
            "VehicleId": vehicle_id,
            "Make": make,
            "Model": model,
            "Year": year,
            "Type": random.choice(VEHICLE_TYPES),
            "Color": random.choice(VEHICLE_COLORS),
            "VIN": f"1HGCM82633A{random.randint(100000, 999999)}",
            "LicensePlate": f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(100, 999)}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}",
            "Status": random.choice(VEHICLE_STATUS),
            "Mileage": random.randint(1000, 100000),
            "FuelLevel": random.randint(1, 100),
            "BatteryLevel": random.randint(1, 100),
            "LastUpdated": datetime.utcnow().isoformat(),
            "LastLocation": {
                "Latitude": round(random.uniform(25.0, 49.0), 6),
                "Longitude": round(random.uniform(-125.0, -70.0), 6)
            },
            "OwnerId": str(uuid.uuid4()),
            "Features": {
                "HasAutoPilot": random.choice([True, False]),
                "HasHeatedSeats": random.choice([True, False]),
                "HasRemoteStart": random.choice([True, False]),
                "HasNavigation": random.choice([True, False])
            },
            "CurrentTelemetry": {
                "Speed": random.randint(0, 80),
                "EngineTemp": random.randint(170, 220),
                "OilLife": random.randint(30, 100),
                "TirePressure": {
                    "FrontLeft": random.randint(32, 36),
                    "FrontRight": random.randint(32, 36),
                    "RearLeft": random.randint(32, 36),
                    "RearRight": random.randint(32, 36)
                }
            }
        }
    
    def generate_service(self, vehicle_id):
        """Generate sample service data"""
        service_type = random.choice(SERVICE_TYPES)
        service_date = datetime.utcnow() - timedelta(days=random.randint(1, 180))
        next_service_date = service_date + timedelta(days=random.randint(90, 365))
        
        return {
            "id": str(uuid.uuid4()),
            "serviceId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "serviceType": service_type,
            "serviceDate": service_date.isoformat(),
            "mileage": random.randint(1000, 100000),
            "description": f"{service_type} completed",
            "cost": round(random.uniform(20.0, 500.0), 2),
            "nextServiceDate": next_service_date.isoformat(),
            "nextServiceMileage": random.randint(1000, 100000),
            "location": f"Service Center {random.randint(1, 20)}",
            "technician": f"Technician {random.randint(1, 50)}",
            "notes": "Regular maintenance completed",
            "invoiceNumber": f"INV-{random.randint(10000, 99999)}"
        }
    
    def generate_command(self, vehicle_id):
        """Generate sample command data"""
        command_type = random.choice(COMMAND_TYPES)
        sent_time = datetime.utcnow() - timedelta(minutes=random.randint(1, 1440))
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
            "sentTime": sent_time.isoformat(),
            "executedTime": executed_time.isoformat() if random.random() > 0.3 else None,
            "initiatedBy": f"User{random.randint(1, 10)}",
            "responseCode": random.choice([200, 201, 400, 404, 500]) if random.random() > 0.7 else None,
            "responseMessage": "Command executed successfully" if random.random() > 0.2 else "Command failed",
            "priority": random.choice(["Low", "Normal", "High"])
        }
    
    def generate_notification(self, vehicle_id):
        """Generate sample notification data"""
        notification_type = random.choice(NOTIFICATION_TYPES)
        created_time = datetime.utcnow() - timedelta(hours=random.randint(1, 168))
        
        return {
            "id": str(uuid.uuid4()),
            "notificationId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "notificationType": notification_type,
            "message": f"{notification_type} alert for your vehicle",
            "createdTime": created_time.isoformat(),
            "readTime": (created_time + timedelta(hours=random.randint(1, 24))).isoformat() if random.random() > 0.3 else None,
            "isRead": random.choice([True, False]),
            "priority": random.choice(NOTIFICATION_PRIORITY),
            "source": random.choice(["Vehicle", "System", "Service"]),
            "actionRequired": random.choice([True, False]),
            "actionUrl": "/vehicles/actions/123" if random.random() > 0.5 else None
        }
        
    async def generate_and_insert_data(self, num_vehicles, services_per_vehicle, commands_per_vehicle, notifications_per_vehicle):
        """Generate and insert sample data"""
        logger.info(f"Generating data for {num_vehicles} vehicles...")
        
        # Connect to Cosmos DB
        await self.connect()
        
        # Generate and insert vehicles
        vehicle_ids = []
        for i in range(num_vehicles):
            vehicle = self.generate_vehicle()
            vehicle_id = vehicle["VehicleId"]
            vehicle_ids.append(vehicle_id)
            
            try:
                await self.vehicles_container.create_item(body=vehicle)
                logger.info(f"Created vehicle {i+1}/{num_vehicles}: {vehicle_id}")
            except Exception as e:
                logger.error(f"Failed to create vehicle: {str(e)}")
        
        # Generate and insert related data
        for vehicle_id in vehicle_ids:
            # Services
            for i in range(services_per_vehicle):
                service = self.generate_service(vehicle_id)
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
            
            logger.info(f"Created related data for vehicle: {vehicle_id}")
        
        await self.close()
        logger.info("Sample data generation complete!")

async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Generate sample data for Cosmos DB')
    parser.add_argument('--env-file', default='.env.azure', help='Path to load environment variables')
    parser.add_argument('--vehicles', type=int, default=10, help='Number of vehicles to generate')
    parser.add_argument('--services', type=int, default=5, help='Number of services per vehicle')
    parser.add_argument('--commands', type=int, default=8, help='Number of commands per vehicle')
    parser.add_argument('--notifications', type=int, default=12, help='Number of notifications per vehicle')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv(args.env_file)
    
    generator = CosmosDataGenerator()
    await generator.generate_and_insert_data(
        args.vehicles,
        args.services,
        args.commands,
        args.notifications
    )

if __name__ == "__main__":
    asyncio.run(main())
    # Example usage:
    # python cosmos_data_generator.py --vehicles 20 --services 3 --commands 5 --notifications 10
