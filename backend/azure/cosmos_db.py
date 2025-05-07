"""
Azure Cosmos DB client for the Connected Car Platform.
Provides data access and change feed functionality.
"""

import os
import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
import uuid
from datetime import datetime

from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from azure.core.exceptions import AzureError
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

# Replace standard logging with loguru
from utils.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)

class CosmosDBClient:
    """Azure Cosmos DB client implementation for Connected Car Platform"""
    
    def __init__(self):
        """Initialize the client with environment variables"""
        # Load environment configuration
        load_dotenv()
        load_dotenv(".env.azure", override=True)
        
        # Set Azure logging to WARNING level
        azure_logger = logging.getLogger("azure")
        azure_logger.setLevel(logging.WARNING)
        
        # Explicitly set HTTP logging policy to ERROR
        http_logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
        http_logger.setLevel(logging.ERROR)
        
        self.endpoint = os.getenv("COSMOS_DB_ENDPOINT")
        self.key = os.getenv("COSMOS_DB_KEY")
        self.use_aad_auth = os.getenv("COSMOS_DB_USE_AAD", "false").lower() == "true"
        self.database_name = os.getenv("COSMOS_DB_DATABASE", "VehiclePlatformDB")
        
        # Container names
        self.vehicles_container_name = os.getenv("COSMOS_DB_CONTAINER_VEHICLES", "vehicles")
        self.services_container_name = os.getenv("COSMOS_DB_CONTAINER_SERVICES", "services")
        self.commands_container_name = os.getenv("COSMOS_DB_CONTAINER_COMMANDS", "commands")
        self.notifications_container_name = os.getenv("COSMOS_DB_CONTAINER_NOTIFICATIONS", "notifications")
        self.status_container_name = os.getenv("COSMOS_DB_CONTAINER_STATUS", "VehicleStatus")
        
        # Connection options - stored as separate properties
        self.connection_timeout = 15  # seconds
        self.request_timeout = 60  # seconds
        self.max_connection_pool_size = 100
        self.idle_timeout = 60 * 5  # 5 minutes
        
        # Client will be initialized in the connect method
        self.client = None
        self.database = None
        self.vehicles_container = None
        self.services_container = None
        self.commands_container = None
        self.notifications_container = None
        self.status_container = None
        
        # Connection state
        self.is_connecting = False
        self.connected = False
        self.connection_error = None
        
        # Don't create an asyncio task during initialization
        # This avoids the "no running event loop" error
        logger.info("Cosmos DB client initialized. Call ensure_connected() before first use.")
        
    async def connect(self):
        """Connect to Cosmos DB"""
        if not self.endpoint or not self.database_name:
            logger.warning("Cosmos DB endpoint or database name missing.")
            return
            
        if self.is_connecting:
            logger.debug("Connection attempt already in progress")
            return
            
        if self.connected:
            logger.debug("Already connected")
            return
            
        self.is_connecting = True
        self.connection_error = None

        try:
            # Initialize client - choose authentication method based on configuration
            if self.use_aad_auth:
                logger.info("Using Azure AD authentication for Cosmos DB")
                credential = DefaultAzureCredential()
                self.client = CosmosClient(
                    url=self.endpoint,
                    credential=credential,
                    connection_verify=True,
                    connection_timeout=self.connection_timeout
                )
            elif self.key:
                logger.info("Using master key authentication for Cosmos DB")
                self.client = CosmosClient(
                    url=self.endpoint,
                    credential=self.key,
                    connection_verify=True,
                    connection_timeout=self.connection_timeout
                )
            else:
                logger.warning("No authentication method configured for Cosmos DB")
                return
            
            self.database = self.client.get_database_client(self.database_name)
            
            # Get container clients
            self.vehicles_container = self.database.get_container_client(self.vehicles_container_name)
            self.services_container = self.database.get_container_client(self.services_container_name)
            self.commands_container = self.database.get_container_client(self.commands_container_name)
            self.notifications_container = self.database.get_container_client(self.notifications_container_name)
            self.status_container = self.database.get_container_client(self.status_container_name)
            
            # Test connection by getting database properties
            await self.database.read()
            
            self.connected = True
            logger.info(f"Successfully connected to Cosmos DB database: {self.database_name}")
        except AzureError as e:
            self.connection_error = str(e)
            logger.error(f"Azure error connecting to Cosmos DB: {str(e)}")
        except Exception as e:
            self.connection_error = str(e)
            logger.error(f"Failed to connect to Cosmos DB: {str(e)}")
        finally:
            self.is_connecting = False

    async def ensure_connected(self):
        """Ensure we have a valid connection, attempt reconnection if needed"""
        if self.connected:
            return True
            
        if not self.is_connecting:
            # Attempt to connect if not already connecting
            await self.connect()
            
        return self.connected

    async def close(self):
        """Close Cosmos DB client connection"""
        if self.client:
            await self.client.close()
            self.connected = False
            logger.info("Cosmos DB connection closed")
            
    # Vehicle Status operations
    
    async def get_vehicle_status(self, vehicle_id: str) -> Dict[str, Any]:
        """
        Get the latest status for a vehicle
        
        Args:
            vehicle_id: ID of the vehicle
            
        Returns:
            Dictionary with vehicle status data
        """
        if not await self.ensure_connected() or not self.status_container:
            logger.warning("No Cosmos DB connection. Returning mock data.")
            return self._mock_vehicle_status(vehicle_id)
            
        try:
            # Use parameters instead of string interpolation for security
            query = "SELECT * FROM c WHERE c.vehicleId = @vehicleId ORDER BY c._ts DESC OFFSET 0 LIMIT 1"
            parameters = [{"name": "@vehicleId", "value": vehicle_id}]
            
            items = self.status_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
            
            async for item in items:
                return {
                    "Battery": item.get("batteryLevel", 0),
                    "Temperature": item.get("temperature", 0),
                    "Speed": item.get("speed", 0),
                    "OilRemaining": item.get("oilLevel", 0)
                }
                
            # If no items found, return mock data
            logger.warning(f"No status found for vehicle {vehicle_id}. Returning mock data.")
            return self._mock_vehicle_status(vehicle_id)
            
        except Exception as e:
            logger.error(f"Error getting vehicle status: {str(e)}")
            return self._mock_vehicle_status(vehicle_id)
            
    async def subscribe_to_vehicle_status(self, vehicle_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Subscribe to status updates for a vehicle using Change Feed
        
        Args:
            vehicle_id: ID of the vehicle
            
        Yields:
            Dictionary with updated vehicle status data
        """
        if not await self.ensure_connected() or not self.status_container:
            logger.warning("No Cosmos DB connection. Using mock data feed.")
            async for status in self._mock_status_feed(vehicle_id):
                yield status
            return
            
        try:
            # Initialize with latest status
            latest_status = await self.get_vehicle_status(vehicle_id)
            yield latest_status
            
            # Get change feed iterator with continuation token support
            change_feed_options = {
                "start_from_beginning": False,
                "start_time": None  # Start from now
            }
            
            change_feed = self.status_container.query_items_change_feed(**change_feed_options)
            
            # Monitor change feed for updates
            async for changes in change_feed:
                for change in changes:
                    if change.get("vehicleId") == vehicle_id:
                        updated_status = {
                            "Battery": change.get("batteryLevel", 0),
                            "Temperature": change.get("temperature", 0),
                            "Speed": change.get("speed", 0),
                            "OilRemaining": change.get("oilLevel", 0)
                        }
                        yield updated_status
                        
                # Prevent tight loop - add a small delay
                await asyncio.sleep(0.5)
                
        except Exception as e:
            logger.error(f"Error in vehicle status subscription: {str(e)}")
            # Fall back to mock data on error
            async for status in self._mock_status_feed(vehicle_id):
                yield status
                
    async def update_vehicle_status(self, vehicle_id: str, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update or create vehicle status record"""
        if not await self.ensure_connected() or not self.status_container:
            logger.warning("No Cosmos DB connection. Cannot update vehicle status.")
            return status_data
        
        try:
            # Check if status exists
            query = "SELECT * FROM c WHERE c.vehicleId = @vehicleId ORDER BY c._ts DESC OFFSET 0 LIMIT 1"
            parameters = [{"name": "@vehicleId", "value": vehicle_id}]
            
            items = self.status_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
            
            existing_status = None
            async for item in items:
                existing_status = item
                break
                
            if existing_status:
                # Update existing status
                for key, value in status_data.items():
                    existing_status[key] = value
                    
                existing_status["_ts"] = int(datetime.now().timestamp())
                
                result = await self.status_container.replace_item(
                    item=existing_status["id"],
                    body=existing_status
                )
                
                logger.info(f"Updated status for vehicle {vehicle_id}")
                return result
            else:
                # Create new status
                status_data["id"] = str(uuid.uuid4())
                status_data["vehicleId"] = vehicle_id
                status_data["_ts"] = int(datetime.now().timestamp())
                
                result = await self.status_container.create_item(body=status_data)
                
                logger.info(f"Created status for vehicle {vehicle_id}")
                return result
        except Exception as e:
            logger.error(f"Error updating vehicle status: {str(e)}")
            return status_data
    
    # Vehicles operations
    
    async def create_vehicle(self, vehicle_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new vehicle"""
        if not await self.ensure_connected() or not self.vehicles_container:
            logger.warning("No Cosmos DB connection. Cannot create vehicle.")
            return vehicle_data
            
        try:
            # Ensure we have an id
            if "id" not in vehicle_data:
                vehicle_data["id"] = str(uuid.uuid4())
                
            result = await self.vehicles_container.create_item(body=vehicle_data)
            logger.info(f"Created vehicle with ID: {result.get('id')}")
            return result
        except Exception as e:
            logger.error(f"Error creating vehicle: {str(e)}")
            return vehicle_data
            
    async def list_vehicles(self) -> List[Dict[str, Any]]:
        """List all vehicles"""
        if not await self.ensure_connected() or not self.vehicles_container:
            logger.warning("No Cosmos DB connection. Returning mock data.")
            return self._mock_vehicles()
            
        try:
            query = "SELECT * FROM c"
            items = self.vehicles_container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
            
            result = []
            async for item in items:
                result.append(item)
                
            return result
        except Exception as e:
            logger.error(f"Error listing vehicles: {str(e)}")
            return self._mock_vehicles()
    
    # Services operations
    
    async def create_service(self, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new service record"""
        if not await self.ensure_connected() or not self.services_container:
            logger.warning("No Cosmos DB connection. Cannot create service.")
            return service_data
            
        try:
            result = await self.services_container.create_item(body=service_data)
            logger.info(f"Created service with ID: {result.get('id')}")
            return result
        except Exception as e:
            logger.error(f"Error creating service: {str(e)}")
            return service_data
            
    async def list_services(self, vehicle_id: str) -> List[Dict[str, Any]]:
        """List all services for a vehicle"""
        if not await self.ensure_connected() or not self.services_container:
            logger.warning("No Cosmos DB connection. Returning mock data.")
            return self._mock_services(vehicle_id)
            
        try:
            # Use parameters instead of string interpolation
            query = "SELECT * FROM c WHERE c.vehicleId = @vehicleId"
            parameters = [{"name": "@vehicleId", "value": vehicle_id}]
            
            items = self.services_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
            
            result = []
            async for item in items:
                result.append(item)
                
            return result
        except Exception as e:
            logger.error(f"Error listing services: {str(e)}")
            return self._mock_services(vehicle_id)
    
    # Commands operations
    
    async def create_command(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new command"""
        if not await self.ensure_connected() or not self.commands_container:
            logger.warning("No Cosmos DB connection. Cannot create command.")
            return command_data
            
        try:
            # Ensure we have an id
            if "id" not in command_data:
                command_data["id"] = str(uuid.uuid4())
                
            result = await self.commands_container.create_item(body=command_data)
            logger.info(f"Created command with ID: {result.get('commandId')}")
            return result
        except Exception as e:
            logger.error(f"Error creating command: {str(e)}")
            return command_data
            
    async def update_command(self, command_id: str, vehicle_id: str, updated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing command"""
        if not await self.ensure_connected() or not self.commands_container:
            logger.warning("No Cosmos DB connection. Cannot update command.")
            return updated_data
            
        try:
            # Use parameters for security
            query = "SELECT * FROM c WHERE c.commandId = @commandId"
            parameters = [{"name": "@commandId", "value": command_id}]
            
            items = self.commands_container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            )
            
            command = None
            async for item in items:
                command = item
                break
                
            if not command:
                logger.warning(f"Command {command_id} not found")
                return updated_data
                
            # Update the command
            for key, value in updated_data.items():
                command[key] = value
                
            result = await self.commands_container.replace_item(
                item=command["id"],
                body=command
            )
            
            logger.info(f"Updated command with ID: {command_id}")
            return result
        except Exception as e:
            logger.error(f"Error updating command: {str(e)}")
            return updated_data
            
    async def list_commands(self) -> List[Dict[str, Any]]:
        """List all commands"""
        if not await self.ensure_connected() or not self.commands_container:
            logger.warning("No Cosmos DB connection. Returning mock data.")
            return self._mock_commands()
            
        try:
            query = "SELECT * FROM c ORDER BY c._ts DESC"
            items = self.commands_container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
            
            result = []
            async for item in items:
                result.append(item)
                
            return result
        except Exception as e:
            logger.error(f"Error listing commands: {str(e)}")
            return self._mock_commands()
    
    # Notifications operations
    
    async def create_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new notification"""
        if not await self.ensure_connected() or not self.notifications_container:
            logger.warning("No Cosmos DB connection. Cannot create notification.")
            return notification_data
            
        try:
            result = await self.notifications_container.create_item(body=notification_data)
            logger.info(f"Created notification with ID: {result.get('id')}")
            return result
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            return notification_data
            
    async def list_notifications(self) -> List[Dict[str, Any]]:
        """List all notifications"""
        if not await self.ensure_connected() or not self.notifications_container:
            logger.warning("No Cosmos DB connection. Returning mock data.")
            return self._mock_notifications()
            
        try:
            query = "SELECT * FROM c ORDER BY c._ts DESC"
            items = self.notifications_container.query_items(
                query=query,
                enable_cross_partition_query=True
            )
            
            result = []
            async for item in items:
                result.append(item)
                
            return result
        except Exception as e:
            logger.error(f"Error listing notifications: {str(e)}")
            return self._mock_notifications()
    
    # Mock data methods (fallbacks when Cosmos DB is not available)
    
    def _mock_vehicle_status(self, vehicle_id: str) -> Dict[str, Any]:
        """Generate mock vehicle status"""
        import random
        return {
            "Battery": random.randint(10, 100),
            "Temperature": random.randint(18, 32),
            "Speed": random.randint(0, 120),
            "OilRemaining": random.randint(20, 100)
        }
        
    async def _mock_status_feed(self, vehicle_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate mock status feed for testing"""
        import random
        
        # Start with initial status
        status = self._mock_vehicle_status(vehicle_id)
        yield status
        
        # Simulate periodic updates
        while True:
            await asyncio.sleep(5)  # Update every 5 seconds
            
            # Randomly adjust values
            status["Battery"] = max(0, min(100, status["Battery"] + random.randint(-5, 3)))
            status["Temperature"] = max(0, min(100, status["Temperature"] + random.randint(-2, 2)))
            status["Speed"] = max(0, min(200, status["Speed"] + random.randint(-10, 10)))
            status["OilRemaining"] = max(0, min(100, status["OilRemaining"] - random.randint(0, 1)))
            
            yield status
            
    def _mock_vehicles(self) -> List[Dict[str, Any]]:
        """Generate mock vehicles"""
        return [
            {"VehicleId": "v001", "Brand": "Tesla", "VehicleModel": "Model S", "Year": 2022},
            {"VehicleId": "v002", "Brand": "BMW", "VehicleModel": "i4", "Year": 2023},
            {"VehicleId": "v003", "Brand": "Ford", "VehicleModel": "Mustang Mach-E", "Year": 2022}
        ]
        
    def _mock_services(self, vehicle_id: str) -> List[Dict[str, Any]]:
        """Generate mock services"""
        import datetime
        
        today = datetime.datetime.now()
        three_months = today + datetime.timedelta(days=90)
        
        return [
            {
                "ServiceCode": "OIL_CHANGE",
                "Description": "Regular oil change service",
                "StartDate": (today - datetime.timedelta(days=30)).isoformat(),
                "EndDate": ""
            },
            {
                "ServiceCode": "TIRE_ROTATION",
                "Description": "Tire rotation service",
                "StartDate": today.isoformat(),
                "EndDate": three_months.isoformat()
            }
        ]
        
    def _mock_commands(self) -> List[Dict[str, Any]]:
        """Generate mock commands"""
        import datetime
        
        today = datetime.datetime.now()
        
        return [
            {
                "commandId": "cmd001",
                "vehicleId": "v001",
                "commandType": "START_ENGINE",
                "status": "completed",
                "timestamp": (today - datetime.timedelta(hours=2)).isoformat()
            },
            {
                "commandId": "cmd002",
                "vehicleId": "v002",
                "commandType": "LOCK_DOORS",
                "status": "completed",
                "timestamp": (today - datetime.timedelta(hours=1)).isoformat()
            }
        ]
        
    def _mock_notifications(self) -> List[Dict[str, Any]]:
        """Generate mock notifications"""
        import datetime
        
        today = datetime.datetime.now()
        
        return [
            {
                "notificationId": "n001",
                "commandId": "cmd001",
                "vehicleId": "v001",
                "message": "Engine started successfully",
                "status": "info",
                "timestamp": (today - datetime.timedelta(hours=2)).isoformat()
            },
            {
                "notificationId": "n002",
                "commandId": "cmd002",
                "vehicleId": "v002",
                "message": "Doors locked successfully",
                "status": "info",
                "timestamp": (today - datetime.timedelta(hours=1)).isoformat()
            }
        ]

# Create a singleton instance - but don't connect immediately
cosmos_client = CosmosDBClient()
