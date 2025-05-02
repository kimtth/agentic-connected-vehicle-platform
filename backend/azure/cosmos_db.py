"""
Azure Cosmos DB integration for the connected vehicle platform.
"""

import os
from azure.cosmos import CosmosClient, PartitionKey
from azure.core.exceptions import ResourceExistsError
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CosmosDBClient:
    """Client for interacting with Azure Cosmos DB"""
    
    def __init__(self):
        """Initialize the Cosmos DB client"""
        self.endpoint = os.getenv("COSMOS_DB_ENDPOINT")
        self.key = os.getenv("COSMOS_DB_KEY")
        self.database_name = os.getenv("COSMOS_DB_DATABASE")
        
        # Container names
        self.vehicles_container_name = os.getenv("COSMOS_DB_CONTAINER_VEHICLES")
        self.services_container_name = os.getenv("COSMOS_DB_CONTAINER_SERVICES")
        self.commands_container_name = os.getenv("COSMOS_DB_CONTAINER_COMMANDS")
        self.notifications_container_name = os.getenv("COSMOS_DB_CONTAINER_NOTIFICATIONS")
        
        # Initialize client
        self.client = CosmosClient(self.endpoint, credential=self.key)
        self.database = None
        self.vehicles_container = None
        self.services_container = None
        self.commands_container = None
        self.notifications_container = None
        
        # Initialize database and containers
        self._init_database()
        self._init_containers()
        
        logger.info("Cosmos DB client initialized successfully")
    
    def _init_database(self):
        """Initialize the database"""
        try:
            self.database = self.client.create_database(self.database_name)
            logger.info(f"Created database: {self.database_name}")
        except ResourceExistsError:
            self.database = self.client.get_database_client(self.database_name)
            logger.info(f"Using existing database: {self.database_name}")
    
    def _init_containers(self):
        """Initialize the containers"""
        # Vehicles container
        try:
            self.vehicles_container = self.database.create_container(
                id=self.vehicles_container_name,
                partition_key=PartitionKey(path="/VehicleId")
            )
            logger.info(f"Created container: {self.vehicles_container_name}")
        except ResourceExistsError:
            self.vehicles_container = self.database.get_container_client(self.vehicles_container_name)
            logger.info(f"Using existing container: {self.vehicles_container_name}")
        
        # Services container
        try:
            self.services_container = self.database.create_container(
                id=self.services_container_name,
                partition_key=PartitionKey(path="/vehicleId")
            )
            logger.info(f"Created container: {self.services_container_name}")
        except ResourceExistsError:
            self.services_container = self.database.get_container_client(self.services_container_name)
            logger.info(f"Using existing container: {self.services_container_name}")
        
        # Commands container
        try:
            self.commands_container = self.database.create_container(
                id=self.commands_container_name,
                partition_key=PartitionKey(path="/vehicleId")
            )
            logger.info(f"Created container: {self.commands_container_name}")
        except ResourceExistsError:
            self.commands_container = self.database.get_container_client(self.commands_container_name)
            logger.info(f"Using existing container: {self.commands_container_name}")
        
        # Notifications container
        try:
            self.notifications_container = self.database.create_container(
                id=self.notifications_container_name,
                partition_key=PartitionKey(path="/vehicleId")
            )
            logger.info(f"Created container: {self.notifications_container_name}")
        except ResourceExistsError:
            self.notifications_container = self.database.get_container_client(self.notifications_container_name)
            logger.info(f"Using existing container: {self.notifications_container_name}")
    
    # Vehicle operations
    async def create_vehicle(self, vehicle_data):
        """Create a new vehicle"""
        return self.vehicles_container.create_item(vehicle_data)
    
    async def get_vehicle(self, vehicle_id):
        """Get a vehicle by ID"""
        query = f"SELECT * FROM c WHERE c.VehicleId = '{vehicle_id}'"
        items = list(self.vehicles_container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
        return items[0] if items else None
    
    async def list_vehicles(self):
        """List all vehicles"""
        query = "SELECT * FROM c"
        return list(self.vehicles_container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
    
    # Service operations
    async def create_service(self, service_data):
        """Create a new service"""
        return self.services_container.create_item(service_data)
    
    async def list_services(self, vehicle_id):
        """List services for a vehicle"""
        query = f"SELECT * FROM c WHERE c.vehicleId = '{vehicle_id}'"
        return list(self.services_container.query_items(
            query=query,
            enable_cross_partition_query=False  # Using partition key
        ))
    
    # Command operations
    async def create_command(self, command_data):
        """Create a new command"""
        return self.commands_container.create_item(command_data)
    
    async def update_command(self, command_id, vehicle_id, updated_data):
        """Update a command"""
        # Get the existing command
        query = f"SELECT * FROM c WHERE c.commandId = '{command_id}' AND c.vehicleId = '{vehicle_id}'"
        items = list(self.commands_container.query_items(
            query=query,
            enable_cross_partition_query=False
        ))
        if not items:
            return None
        
        command = items[0]
        # Update the fields
        for key, value in updated_data.items():
            command[key] = value
        
        # Replace the item
        return self.commands_container.replace_item(item=command['id'], body=command)
    
    async def list_commands(self):
        """List all commands"""
        query = "SELECT * FROM c"
        return list(self.commands_container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))
    
    # Notification operations
    async def create_notification(self, notification_data):
        """Create a new notification"""
        return self.notifications_container.create_item(notification_data)
    
    async def list_notifications(self):
        """List all notifications"""
        query = "SELECT * FROM c"
        return list(self.notifications_container.query_items(
            query=query,
            enable_cross_partition_query=True
        ))

# Initialize the Cosmos DB client
cosmos_client = CosmosDBClient()
