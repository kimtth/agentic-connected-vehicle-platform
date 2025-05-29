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
from datetime import datetime, timedelta

from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey, ConsistencyLevel
from azure.core.exceptions import AzureError, ServiceRequestError, ServiceResponseError
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError

# Replace standard logging with loguru
from utils.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)

class CosmosDBClient:
    """Azure Cosmos DB client implementation for Connected Car Platform"""
    
    def __init__(self):
        """Initialize the client with environment variables"""        
        # Set Azure logging to WARNING level to reduce noise
        azure_logger = logging.getLogger("azure")
        azure_logger.setLevel(logging.WARNING)
        
        # Explicitly set HTTP logging policy to ERROR
        http_logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
        http_logger.setLevel(logging.ERROR)

        load_dotenv(override=True)
        
        # Core configuration - Handle both old and new endpoint formats for backward compatibility
        self.endpoint = os.getenv("COSMOS_DB_ENDPOINT")
        if self.endpoint:
            # Handle backward compatibility: remove :443 port if present
            if self.endpoint.endswith(":443/"):
                self.endpoint = self.endpoint.replace(":443/", "/")
            # Ensure endpoint ends with /
            elif not self.endpoint.endswith("/"):
                self.endpoint = self.endpoint + "/"
        
        self.key = os.getenv("COSMOS_DB_KEY")
        self.use_aad_auth = os.getenv("COSMOS_DB_USE_AAD", "false").lower() == "true"
        self.database_name = os.getenv("COSMOS_DB_DATABASE", "VehiclePlatformDB")
        
        # Container names with validation
        self.vehicles_container_name = os.getenv("COSMOS_DB_CONTAINER_VEHICLES", "vehicles")
        self.services_container_name = os.getenv("COSMOS_DB_CONTAINER_SERVICES", "services")
        self.commands_container_name = os.getenv("COSMOS_DB_CONTAINER_COMMANDS", "commands")
        self.notifications_container_name = os.getenv("COSMOS_DB_CONTAINER_NOTIFICATIONS", "notifications")
        self.status_container_name = os.getenv("COSMOS_DB_CONTAINER_STATUS", "VehicleStatus")
        
        # Connection configuration with Azure best practices - Simplified for compatibility
        self.connection_config = {
            'consistency_level': ConsistencyLevel.Session,
            'max_retry_attempts': int(os.getenv("COSMOS_DB_MAX_RETRY_ATTEMPTS", "5")),
            'retry_base_delay': int(os.getenv("COSMOS_DB_RETRY_DELAY", "1")),
        }
        
        # Client instances
        self.client = None
        self.database = None
        self.vehicles_container = None
        self.services_container = None
        self.commands_container = None
        self.notifications_container = None
        self.status_container = None
        
        # Connection state management
        self.is_connecting = False
        self.connected = False
        self.connection_error = None
        self.last_connection_attempt = None
        self.connection_retry_delay = 10  # Increased from 5 seconds
        
        # Health check configuration
        self.health_check_interval = 30  # seconds
        self.last_health_check = None
        
        # Validate configuration
        self._validate_configuration()
        
        logger.info("Cosmos DB client initialized with Azure best practices")
        
    def _parse_preferred_locations(self):
        """Parse preferred locations from environment variable"""
        locations_str = os.getenv("COSMOS_DB_PREFERRED_LOCATIONS", "")
        if locations_str:
            return [loc.strip() for loc in locations_str.split(",") if loc.strip()]
        return None
        
    def _validate_configuration(self):
        """Validate Cosmos DB configuration - Updated for backward compatibility"""
        if not self.endpoint:
            logger.warning("COSMOS_DB_ENDPOINT not configured - Cosmos DB will be disabled")
            return False
            
        if not self.use_aad_auth and not self.key:
            logger.warning("No authentication method configured for Cosmos DB")
            return False
            
        if not self.database_name:
            logger.error("COSMOS_DB_DATABASE name is required")
            return False
            
        # Validate endpoint format - Support both old and new formats
        if not self.endpoint.startswith("https://") or not ".documents.azure.com" in self.endpoint:
            logger.warning(f"Cosmos DB endpoint format may be invalid: {self.endpoint}")
            
        return True
        
    async def connect(self):
        """Connect to Cosmos DB with retry logic and proper error handling"""
        if not self.endpoint or not self.database_name:
            logger.warning("Cosmos DB configuration incomplete - skipping connection")
            return False
            
        if self.is_connecting:
            logger.debug("Connection attempt already in progress")
            return self.connected
            
        if self.connected and self._is_connection_healthy():
            logger.debug("Already connected and healthy")
            return True
            
        # Check if we should retry based on last attempt
        if (self.last_connection_attempt and 
            datetime.now() - self.last_connection_attempt < timedelta(seconds=self.connection_retry_delay)):
            logger.debug("Too soon to retry connection")
            return self.connected

        self.is_connecting = True
        self.connection_error = None
        self.last_connection_attempt = datetime.now()

        try:
            # Determine authentication method with fallback
            if self.use_aad_auth:
                success = await self._connect_with_aad()
            elif self.key:
                try:
                    success = await self._connect_with_master_key()
                except (AzureError, Exception) as e:
                    # Check if the error suggests AAD is required
                    error_str = str(e).lower()
                    if any(phrase in error_str for phrase in ["local authorization", "authentication", "forbidden"]):
                        logger.warning("Master key auth failed, attempting AAD fallback")
                        self.use_aad_auth = True
                        success = await self._connect_with_aad()
                    else:
                        raise
            else:
                logger.error("No valid authentication method available")
                return False
            
            if success:
                # Ensure containers exist
                await self._ensure_containers_exist()
                
                # Verify connection with a simple operation
                await self._verify_connection()
                
                self.connected = True
                self.connection_error = None
                logger.info(f"Successfully connected to Cosmos DB: {self.database_name}")
                return True
            else:
                return False
                
        except Exception as e:
            self.connection_error = str(e)
            self.connected = False
            logger.error(f"Failed to connect to Cosmos DB: {str(e)}")
            return False
        finally:
            self.is_connecting = False
            
    async def _connect_with_aad(self):
        """Connect using Azure AD authentication with proper configuration"""
        try:
            logger.info("Connecting to Cosmos DB with Azure AD authentication")
            credential = DefaultAzureCredential(
                exclude_interactive_browser_credential=True,
                exclude_visual_studio_code_credential=True,
                exclude_shared_token_cache_credential=True
            )
            
            # Create client with minimal configuration (following working pattern)
            self.client = CosmosClient(self.endpoint, credential=credential)
            
            # Test connection
            self.database = self.client.get_database_client(self.database_name)
            await self.database.read()
            
            self._initialize_containers()
            return True
        except Exception as e:
            logger.error(f"AAD authentication failed: {str(e)}")
            # Clean up on failure with proper session cleanup
            await self._cleanup_client()
            raise
        
    async def _connect_with_master_key(self):
        """Connect using master key authentication with proper configuration"""
        try:
            logger.info("Connecting to Cosmos DB with master key authentication")
            
            # Create client with minimal configuration (following working pattern)
            self.client = CosmosClient(self.endpoint, credential=self.key)
            
            # Test connection
            self.database = self.client.get_database_client(self.database_name)
            await self.database.read()
            
            self._initialize_containers()
            return True
        except AzureError as e:
            if "authorization is disabled" in str(e).lower():
                logger.warning("Master key auth disabled. Falling back to AAD auth.")
                self.use_aad_auth = True
                return await self._connect_with_aad()
            else:
                logger.error(f"Master key authentication failed: {str(e)}")
                await self._cleanup_client()
                raise
        except Exception as e:
            logger.error(f"Master key authentication failed: {str(e)}")
            await self._cleanup_client()
            raise
    
    def _initialize_containers(self):
        """Initialize container clients with proper configuration"""
        self.vehicles_container = self.database.get_container_client(self.vehicles_container_name)
        self.services_container = self.database.get_container_client(self.services_container_name)
        self.commands_container = self.database.get_container_client(self.commands_container_name)
        self.notifications_container = self.database.get_container_client(self.notifications_container_name)
        self.status_container = self.database.get_container_client(self.status_container_name)

    async def _ensure_containers_exist(self):
        """Ensure required containers exist with proper configuration"""
        container_configs = {
            self.vehicles_container_name: {
                "partition_key": "/vehicleId",
                "default_ttl": None,
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [{"path": "/*"}],
                    "excludedPaths": [{"path": "/\"_etag\"/?"}]
                }
            },
            self.services_container_name: {
                "partition_key": "/vehicleId",
                "default_ttl": None,
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [{"path": "/*"}],
                    "excludedPaths": [{"path": "/\"_etag\"/?"}]
                }
            },
            self.commands_container_name: {
                "partition_key": "/vehicleId",
                "default_ttl": 86400,  # 24 hours for commands
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [
                        {"path": "/vehicleId/?"},
                        {"path": "/commandId/?"},
                        {"path": "/status/?"},
                        {"path": "/_ts/?"}
                    ],
                    "excludedPaths": [{"path": "/*"}]
                }
            },
            self.notifications_container_name: {
                "partition_key": "/vehicleId",
                "default_ttl": 2592000,  # 30 days for notifications
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [
                        {"path": "/vehicleId/?"},
                        {"path": "/type/?"},
                        {"path": "/_ts/?"}
                    ],
                    "excludedPaths": [{"path": "/*"}]
                }
            },
            self.status_container_name: {
                "partition_key": "/vehicleId",
                "default_ttl": 604800,  # 7 days for status
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [
                        {"path": "/vehicleId/?"},
                        {"path": "/_ts/?"}
                    ],
                    "excludedPaths": [{"path": "/*"}]
                }
            }
        }
        
        for container_name, config in container_configs.items():
            try:
                container = self.database.get_container_client(container_name)
                await container.read()
                logger.debug(f"Container {container_name} exists")
            except CosmosResourceNotFoundError:
                try:
                    logger.info(f"Creating Cosmos DB container: {container_name}")
                    await self.database.create_container(
                        id=container_name,
                        partition_key=PartitionKey(path=config["partition_key"]),
                        default_ttl=config["default_ttl"],
                        indexing_policy=config["indexing_policy"]
                    )
                    logger.info(f"Successfully created container: {container_name}")
                except Exception as e:
                    logger.error(f"Failed to create container {container_name}: {str(e)}")
                    raise
        
        # Re-initialize container clients after ensuring they exist
        self._initialize_containers()

    async def _verify_connection(self):
        """Verify connection health with a simple read operation"""
        try:
            await self.database.read()
            self.last_health_check = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Connection verification failed: {str(e)}")
            self.connected = False
            raise

    def _is_connection_healthy(self):
        """Check if connection is healthy based on last health check"""
        if not self.last_health_check:
            return False
        return datetime.now() - self.last_health_check < timedelta(seconds=self.health_check_interval)

    async def ensure_connected(self):
        """Ensure we have a valid connection with automatic retry"""
        if self.connected and self._is_connection_healthy():
            return True
            
        if not self.is_connecting:
            return await self.connect()
            
        # Wait for existing connection attempt
        max_wait = 30  # seconds
        wait_time = 0
        while self.is_connecting and wait_time < max_wait:
            await asyncio.sleep(1)
            wait_time += 1
            
        return self.connected

    async def _cleanup_client(self):
        """Clean up client resources properly"""
        if self.client:
            try:
                await self.client.close()
            except Exception as e:
                logger.debug(f"Error during client cleanup: {str(e)}")
            finally:
                self.client = None
                self.database = None
                self.vehicles_container = None
                self.services_container = None
                self.commands_container = None
                self.notifications_container = None
                self.status_container = None

    async def close(self):
        """Close Cosmos DB client connection properly"""
        if self.client:
            try:
                await self.client.close()
                logger.info("Cosmos DB connection closed")
            except Exception as e:
                logger.error(f"Error closing Cosmos DB connection: {str(e)}")
            finally:
                self.client = None
                self.database = None
                self.vehicles_container = None
                self.services_container = None
                self.commands_container = None
                self.notifications_container = None
                self.status_container = None
                self.connected = False

    # Vehicle Status operations
    
    async def get_vehicle_status(self, vehicleId: str) -> Dict[str, Any]:
        """Get the latest status for a vehicle with proper error handling"""
        if not await self.ensure_connected() or not self.status_container:
            logger.warning("No Cosmos DB connection. Cannot get vehicle status.")
            return {}
            
        if not vehicleId or not isinstance(vehicleId, str):
            logger.error("Invalid vehicleId provided")
            return {}
            
        try:
            query = "SELECT * FROM c WHERE c.vehicleId = @vehicleId ORDER BY c._ts DESC OFFSET 0 LIMIT 1"
            parameters = [{"name": "@vehicleId", "value": vehicleId}]
            
            items = self.status_container.query_items(
                query=query,
                parameters=parameters,
                partition_key=vehicleId
            )
            
            async for item in items:
                return {
                    "Battery": item.get("batteryLevel", 0),
                    "Temperature": item.get("temperature", 0),
                    "Speed": item.get("speed", 0),
                    "OilRemaining": item.get("oilLevel", 0),
                    "timestamp": item.get("_ts")
                }
                
            logger.debug(f"No status found for vehicle {vehicleId}")
            return {}
        except Exception as e:
            logger.error(f"Error getting vehicle status for {vehicleId}: {str(e)}")
            return {}

    async def subscribe_to_vehicle_status(self, vehicleId: str) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Subscribe to status updates for a vehicle using Change Feed
        
        Args:
            vehicleId: ID of the vehicle
            
        Yields:
            Dictionary with updated vehicle status data
        """
        if not await self.ensure_connected() or not self.status_container:
            logger.warning("No Cosmos DB connection. Cannot subscribe to vehicle status.")
            return
            
        try:
            # Initialize with latest status
            latest_status = await self.get_vehicle_status(vehicleId)
            if latest_status:
                yield latest_status
            
            # Use a simpler polling approach instead of change feed for better compatibility
            last_timestamp = latest_status.get("timestamp", 0) if latest_status else 0
            
            while True:
                try:
                    # Query for newer status updates
                    query = "SELECT * FROM c WHERE c.vehicleId = @vehicleId AND c._ts > @lastTimestamp ORDER BY c._ts DESC"
                    parameters = [
                        {"name": "@vehicleId", "value": vehicleId},
                        {"name": "@lastTimestamp", "value": last_timestamp}
                    ]
                    
                    items = self.status_container.query_items(
                        query=query,
                        parameters=parameters,
                        partition_key=vehicleId
                    )
                    
                    has_updates = False
                    async for item in items:
                        updated_status = {
                            "Battery": item.get("batteryLevel", 0),
                            "Temperature": item.get("temperature", 0),
                            "Speed": item.get("speed", 0),
                            "OilRemaining": item.get("oilLevel", 0),
                            "timestamp": item.get("_ts")
                        }
                        yield updated_status
                        last_timestamp = max(last_timestamp, item.get("_ts", 0))
                        has_updates = True
                    
                    # If no updates, wait before checking again
                    if not has_updates:
                        await asyncio.sleep(5.0)  # Poll every 5 seconds
                    else:
                        await asyncio.sleep(1.0)  # Check more frequently if there are updates
                        
                except Exception as e:
                    logger.error(f"Error in status polling iteration: {str(e)}")
                    await asyncio.sleep(10.0)  # Wait longer on error before retrying
                    continue
                    
        except Exception as e:
            logger.error(f"Error in vehicle status subscription: {str(e)}")
            return

    async def update_vehicle_status(self, vehicleId: str, status_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update or create vehicle status record"""
        if not await self.ensure_connected() or not self.status_container:
            logger.warning("No Cosmos DB connection. Cannot update vehicle status.")
            return status_data
        
        try:
            # Check if status exists
            query = "SELECT * FROM c WHERE c.vehicleId = @vehicleId ORDER BY c._ts DESC OFFSET 0 LIMIT 1"
            parameters = [{"name": "@vehicleId", "value": vehicleId}]
            
            items = self.status_container.query_items(
                query=query,
                parameters=parameters
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
                
                logger.info(f"Updated status for vehicle {vehicleId}")
                return result
            else:
                # Create new status
                status_data["id"] = str(uuid.uuid4())
                status_data["vehicleId"] = vehicleId
                status_data["_ts"] = int(datetime.now().timestamp())
                
                result = await self.status_container.create_item(body=status_data)
                
                logger.info(f"Created status for vehicle {vehicleId}")
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
            logger.warning("No Cosmos DB connection. Cannot list vehicles.")
            return []
            
        try:
            query = "SELECT * FROM c"
            items = self.vehicles_container.query_items(query=query)
            
            result = []
            async for item in items:
                result.append(item)
                
            return result
        except Exception as e:
            logger.error(f"Error listing vehicles: {str(e)}")
            return []

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
            
    async def list_services(self, vehicleId: str) -> List[Dict[str, Any]]:
        """List all services for a vehicle"""
        if not await self.ensure_connected() or not self.services_container:
            logger.warning("No Cosmos DB connection. Cannot list services.")
            return []
            
        try:
            # Use parameters instead of string interpolation
            query = "SELECT * FROM c WHERE c.vehicleId = @vehicleId"
            parameters = [{"name": "@vehicleId", "value": vehicleId}]
            
            items = self.services_container.query_items(
                query=query,
                parameters=parameters,
                partition_key=vehicleId
            )
            
            result = []
            async for item in items:
                result.append(item)
                
            return result
        except Exception as e:
            logger.error(f"Error listing services: {str(e)}")
            return []

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
            
    async def update_command(self, command_id: str, vehicleId: str, updated_data: Dict[str, Any]) -> Dict[str, Any]:
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
                parameters=parameters
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
            
    async def list_commands(self, vehicleId: str = None) -> List[Dict[str, Any]]:
        """List all commands with optional filter by vehicle ID"""
        if not await self.ensure_connected() or not self.commands_container:
            logger.warning("No Cosmos DB connection. Cannot list commands.")
            return []
            
        try:
            if vehicleId:
                # Using parameters for security
                query = "SELECT * FROM c WHERE c.vehicleId = @vehicleId ORDER BY c._ts DESC"
                parameters = [{"name": "@vehicleId", "value": vehicleId}]
                
                items = self.commands_container.query_items(
                    query=query,
                    parameters=parameters,
                    partition_key=vehicleId
                )
            else:
                query = "SELECT * FROM c ORDER BY c._ts DESC"
                items = self.commands_container.query_items(query=query)
        
            result = []
            async for item in items:
                result.append(item)
                
            return result
        except Exception as e:
            logger.error(f"Error listing commands: {str(e)}")
            return []

    # Notifications operations
    
    async def create_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new notification"""
        if not await self.ensure_connected() or not self.notifications_container:
            logger.warning("No Cosmos DB connection. Cannot create notification.")
            return notification_data
            
        try:
            # Ensure we have an id
            if "id" not in notification_data:
                notification_data["id"] = str(uuid.uuid4())
                
            result = await self.notifications_container.create_item(body=notification_data)
            logger.info(f"Created notification with ID: {result.get('id')}")
            return result
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            return notification_data
            
    async def list_notifications(self, vehicleId: str = None) -> List[Dict[str, Any]]:
        """List all notifications with optional filter by vehicle ID"""
        if not await self.ensure_connected() or not self.notifications_container:
            logger.warning("No Cosmos DB connection. Cannot list notifications.")
            return []
            
        try:
            if vehicleId:
                # Using parameters for security
                query = "SELECT * FROM c WHERE c.vehicleId = @vehicleId ORDER BY c._ts DESC"
                parameters = [{"name": "@vehicleId", "value": vehicleId}]
                
                items = self.notifications_container.query_items(
                    query=query,
                    parameters=parameters,
                    partition_key=vehicleId
                )
            else:
                query = "SELECT * FROM c ORDER BY c._ts DESC"
                items = self.notifications_container.query_items(query=query)
        
            result = []
            async for item in items:
                result.append(item)
                
            return result
        except Exception as e:
            logger.error(f"Error listing notifications: {str(e)}")
            return []


# Create a singleton instance
cosmos_client = CosmosDBClient()
