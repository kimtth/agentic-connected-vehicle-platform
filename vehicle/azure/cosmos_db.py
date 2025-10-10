"""
Azure Cosmos DB client for the Connected Car Platform.
Provides data access and change feed functionality.
"""

import os
import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
import uuid
from datetime import datetime, timedelta, timezone
import weakref
import atexit
from functools import lru_cache
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from azure.core.exceptions import AzureError, ClientAuthenticationError
from azure.identity.aio import (
    DefaultAzureCredential,
    ManagedIdentityCredential,
    AzureDeveloperCliCredential
)
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError
import traceback
from azure.cosmos import CosmosClient as SyncCosmosClient  # for fallback probe

from utils.logging_config import get_logger
from models.status import VehicleStatus
from models.vehicle_profile import VehicleProfile
from models.service import Service
from models.command import Command
from models.notification import Notification


# Get logger for this module
logger = get_logger(__name__)

# Global registry for tracking client instances
_client_registry = weakref.WeakSet()


async def _cleanup_all_clients():
    """Cleanup all registered clients on shutdown"""
    for client in list(_client_registry):
        try:
            await client.close()
        except Exception as e:
            logger.debug(f"Error during global cleanup: {str(e)}")


def _safe_atexit_cleanup():
    """Safe cleanup function for atexit that handles missing event loop"""
    try:
        # Check if there's a running event loop
        try:
            loop = asyncio.get_running_loop()
            # If we get here, there's a running loop, create a task
            asyncio.create_task(_cleanup_all_clients())
        except RuntimeError:
            # No running loop, try to get the event loop
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(_cleanup_all_clients())
                else:
                    # Loop exists but not running, run the cleanup
                    loop.run_until_complete(_cleanup_all_clients())
            except RuntimeError:
                # No event loop available, skip cleanup
                pass
    except Exception as e:
        # Silently ignore cleanup errors during shutdown
        pass


# Register cleanup function with improved error handling
atexit.register(_safe_atexit_cleanup)


class CosmosDBClient:
    """Azure Cosmos DB client implementation for Connected Car Platform"""

    # Partition key strategy: use only /vehicleId (camelCase). No legacy snake_case duplication.

    def __init__(self):
        """Initialize the client with environment variables (only once)"""
        # Prevent multiple initialization of the same instance
        if hasattr(self, "_initialized") and self._initialized:
            return

        logger.info("Initializing Cosmos DB client configuration")

        # Set Azure logging to WARNING level to reduce noise
        azure_logger = logging.getLogger("azure")
        azure_logger.setLevel(logging.WARNING)

        # Explicitly set HTTP logging policy to ERROR
        http_logger = logging.getLogger(
            "azure.core.pipeline.policies.http_logging_policy"
        )
        http_logger.setLevel(logging.ERROR)

        # Also silence aiohttp client session warnings
        aiohttp_logger = logging.getLogger("aiohttp")
        aiohttp_logger.setLevel(logging.WARNING)

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
        self.vehicles_container_name = os.getenv(
            "COSMOS_DB_CONTAINER_VEHICLES", "vehicles"
        )
        self.services_container_name = os.getenv(
            "COSMOS_DB_CONTAINER_SERVICES", "services"
        )
        self.commands_container_name = os.getenv(
            "COSMOS_DB_CONTAINER_COMMANDS", "commands"
        )
        self.notifications_container_name = os.getenv(
            "COSMOS_DB_CONTAINER_NOTIFICATIONS", "notifications"
        )
        self.status_container_name = os.getenv(
            "COSMOS_DB_CONTAINER_STATUS", "vehiclestatus"
        )

        # Client instances
        self.client = None
        self.database = None
        self.vehicles_container = None
        self.services_container = None
        self.commands_container = None
        self.notifications_container = None
        self.status_container = None

        # Session/credential handle for proper cleanup
        self._credential = None

        # Connection state management
        self.is_connecting = False
        self.connected = False
        self.connection_error = None
        self.last_connection_attempt = None
        self.connection_retry_delay = 10  # Increased from 5 seconds

        # Health check configuration
        self.health_check_interval = 30  # seconds
        self.last_health_check = None

        # Session management
        self._cleanup_scheduled = False
        self._connection_lock = asyncio.Lock()

        # Register this instance for global cleanup
        _client_registry.add(self)

        # Validate configuration
        self._validate_configuration()

        # Mark as initialized
        self._initialized = True

        logger.info("Cosmos DB client configuration completed")
        self._closing = False

    def _validate_configuration(self):
        """Validate Cosmos DB configuration - Updated for backward compatibility"""
        if not self.endpoint:
            logger.warning(
                "COSMOS_DB_ENDPOINT not configured - Cosmos DB will be disabled"
            )
            return False

        if not self.use_aad_auth and not self.key:
            logger.warning("No authentication method configured for Cosmos DB")
            return False

        if not self.database_name:
            logger.error("COSMOS_DB_DATABASE name is required")
            return False

        # Validate endpoint format - Support both old and new formats
        if (
            not self.endpoint.startswith("https://")
            or ".documents.azure.com" not in self.endpoint
        ):
            logger.warning(f"Cosmos DB endpoint format may be invalid: {self.endpoint}")

        return True

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _ensure_timestamp(doc: Dict[str, Any]):
        """Inject ISO timestamp if missing but _ts present."""
        if doc and "timestamp" not in doc and "_ts" in doc:
            doc["timestamp"] = (
                datetime.fromtimestamp(doc["_ts"], tz=timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )
        return doc

    @staticmethod
    def _camel_case_key(key: str) -> str:
        if not isinstance(key, str) or key.startswith("_") or "_" not in key:
            return key
        parts = key.split("_")
        return parts[0] + "".join(p.capitalize() for p in parts[1:] if p)

    @classmethod
    def _to_camel(cls, obj):
        if isinstance(obj, dict):
            return {cls._camel_case_key(k): cls._to_camel(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [cls._to_camel(v) for v in obj]
        return obj

    async def _query_one(
        self,
        container,
        query: str,
        params: List[Dict[str, Any]],
        *,
        partition_key: Optional[str] = None,
        model_cls=None,
    ):
        """Generic single-item query + model mapping (now camelCase-normalized)."""
        if not container:
            return None
        try:
            items = container.query_items(
                query=query,
                parameters=params,
                partition_key=partition_key if partition_key is not None else None,
            )
            async for item in items:
                self._ensure_timestamp(item)
                item = self._to_camel(item)
                return model_cls(**item) if model_cls else item
            return None
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return None

    def _diagnostic_log(self, err: Exception, context: str):
        """Log enriched diagnostics for Cosmos errors."""
        try:
            base = f"[CosmosDiag] context={context} type={type(err).__name__}"
            if isinstance(err, CosmosHttpResponseError):
                status = getattr(err, "status_code", None) or getattr(err, "http_response", None)
                code = getattr(err, "sub_status", None)
                msg = str(err)
                logger.error(f"{base} status={status} sub_status={code} msg={msg}")
            elif isinstance(err, ClientAuthenticationError):
                logger.error(f"{base} auth_error={err}")
            else:
                logger.error(f"{base} msg={err}")
            logger.debug(f"{base} traceback=\n{traceback.format_exc()}")
        except Exception:
            pass

    async def _sync_probe(self) -> bool:
        """Run a quick sync client probe in a thread to differentiate transport vs credential issues."""
        if not self.endpoint:
            return False
        def _probe():
            try:
                cred = ManagedIdentityCredential()
                sc = SyncCosmosClient(self.endpoint, credential=cred)
                # lightweight call
                next(sc.list_databases(), None)
                return True
            except Exception as e:
                logger.debug(f"[CosmosDiag] sync probe failed: {e}")
                return False
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _probe)

    async def connect(self):
        """Connect to Cosmos DB with retry logic and proper error handling"""
        if not self.endpoint or not self.database_name:
            logger.warning("Cosmos DB configuration incomplete - skipping connection")
            return False

        async with self._connection_lock:
            if self.is_connecting:
                logger.debug("Connection attempt already in progress")
                return self.connected

            if self.connected and self._is_connection_healthy():
                logger.debug("Already connected and healthy")
                return True

            # Check if we should retry based on last attempt
            if (
                self.last_connection_attempt
                and datetime.now() - self.last_connection_attempt
                < timedelta(seconds=self.connection_retry_delay)
            ):
                logger.debug("Too soon to retry connection")
                return self.connected

            self.is_connecting = True
            self.connection_error = None
            self.last_connection_attempt = datetime.now()

            try:
                # Clean up any existing client first
                await self._cleanup_client()

                # Determine authentication method - prioritize managed identity in Azure
                if self._is_azure_environment() or self.use_aad_auth:
                    success = await self._connect_with_aad()
                elif self.key:
                    success = await self._connect_with_master_key()
                else:
                    logger.error("No valid authentication method available")
                    return False

                if success:
                    # Ensure containers exist
                    await self._ensure_containers_exist()
                    await self._verify_connection()
                    self.connected = True
                    self.connection_error = None
                    logger.info(f"Cosmos connected ({self.database_name})")
                    return True
                return False
            except Exception as e:
                self.connection_error = str(e)
                self.connected = False
                self._diagnostic_log(e, "connect")
                # Attempt sync probe (only if managed identity path)
                try:
                    if self.use_aad_auth or self._is_azure_environment():
                        sync_ok = await self._sync_probe()
                        logger.info(f"[CosmosDiag] sync_probe_success={sync_ok}")
                        if sync_ok:
                            logger.warning("[CosmosDiag] Sync probe succeeded while aio path failed -> possible aio transport / event loop / version mismatch")
                except Exception as sp:
                    logger.debug(f"[CosmosDiag] sync probe exception: {sp}")
                await self._cleanup_client()
                return False
            finally:
                self.is_connecting = False

    def _is_azure_environment(self) -> bool:
        """Check if running in an Azure environment that supports managed identity"""
        # Check for Azure App Service environment variables
        azure_env_vars = [
            "WEBSITE_SITE_NAME",  # Azure App Service
            "WEBSITE_INSTANCE_ID",  # Azure App Service
            "MSI_ENDPOINT",  # Managed Service Identity endpoint
            "IDENTITY_ENDPOINT",  # Managed Identity endpoint (newer)
            "AZURE_CLIENT_ID",  # Sometimes set in Azure environments
        ]
        found_vars = {var: os.getenv(var) for var in azure_env_vars if os.getenv(var)}
        is_azure = len(found_vars) > 0

        env_type = os.getenv("ENV_TYPE", "").lower()
        if env_type in ["dev", "development", "local"] and env_type != "":
            logger.info(f"Azure environment check: {is_azure} | env_type={env_type}")
            is_azure = False
        
        logger.info(f"Azure environment check: {is_azure}")
        logger.info(f"Found Azure environment variables: {found_vars}")
        
        return is_azure

    async def _connect_with_aad(self):
        """AAD authentication. In Azure: plain ManagedIdentityCredential().
        Local dev: AzureDeveloperCliCredential (tenant-aware) then fallback to DefaultAzureCredential."""
        try:
            if self._is_azure_environment():
                self._credential = ManagedIdentityCredential()
            else:
                tenant_id = os.getenv("AZURE_TENANT_ID") or os.getenv("AZD_TENANT_ID") or os.getenv("AZURE_AD_TENANT_ID")
                try:
                    self._credential = AzureDeveloperCliCredential(tenant_id=tenant_id)
                    await self._credential.get_token("https://management.azure.com/.default")
                except Exception as devcli_err:
                    logger.warning(f"DevCLI unavailable ({devcli_err}); fallback DefaultAzureCredential")
                    self._credential = DefaultAzureCredential(
                        exclude_developer_cli_credential=True,
                        exclude_interactive_browser_credential=True,
                    )
            self.client = CosmosClient(self.endpoint, credential=self._credential)
            self.database = self.client.get_database_client(self.database_name)
            self._initialize_containers()
            return True
        except Exception as e:
            self._diagnostic_log(e, "_connect_with_aad")
            await self._cleanup_client()
            raise

    async def _connect_with_master_key(self):
        """Connect using master key authentication with proper configuration"""
        try:
            logger.info("Connecting to Cosmos DB with master key authentication")

            # Create client with minimal configuration
            self.client = CosmosClient(self.endpoint, credential=self.key)

            # Test connection
            self.database = self.client.get_database_client(self.database_name)

            self._initialize_containers()
            logger.info("Successfully connected to Cosmos DB with master key")
            return True
        except AzureError as e:
            error_msg = str(e).lower()
            if "authorization is disabled" in error_msg or "forbidden" in error_msg:
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
        self.vehicles_container = self.database.get_container_client(
            self.vehicles_container_name
        )
        self.services_container = self.database.get_container_client(
            self.services_container_name
        )
        self.commands_container = self.database.get_container_client(
            self.commands_container_name
        )
        self.notifications_container = self.database.get_container_client(
            self.notifications_container_name
        )
        self.status_container = self.database.get_container_client(
            self.status_container_name
        )

    async def _ensure_containers_exist(self):
        """Ensure required containers exist (camelCase /vehicleId only)."""
        container_configs = {
            self.vehicles_container_name: {
                "partition_key": "/vehicleId",
                "default_ttl": None,
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [{"path": "/*"}],
                    "excludedPaths": [{"path": '/"_etag"/?'}],
                },
            },
            self.services_container_name: {
                "partition_key": "/vehicleId",
                "default_ttl": None,
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [{"path": "/*"}],
                    "excludedPaths": [{"path": '/"_etag"/?'}],
                },
            },
            self.commands_container_name: {
                "partition_key": "/vehicleId",
                "default_ttl": 86400,
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [
                        {"path": "/vehicleId/?"},
                        {"path": "/commandId/?"},
                        {"path": "/status/?"},
                        {"path": "/_ts/?"},
                    ],
                    "excludedPaths": [{"path": "/*"}],
                },
            },
            self.notifications_container_name: {
                "partition_key": "/vehicleId",
                "default_ttl": 2592000,
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [
                        {"path": "/vehicleId/?"},
                        {"path": "/type/?"},
                        {"path": "/_ts/?"},
                    ],
                    "excludedPaths": [{"path": "/*"}],
                },
            },
            self.status_container_name: {
                "partition_key": "/vehicleId",
                "default_ttl": 604800,
                "indexing_policy": {
                    "indexingMode": "consistent",
                    "automatic": True,
                    "includedPaths": [{"path": "/vehicleId/?"}, {"path": "/_ts/?"}],
                    "excludedPaths": [{"path": "/*"}],
                },
            },
        }

        for container_name, config in container_configs.items():
            try:
                await self.database.get_container_client(container_name).read()
            except CosmosResourceNotFoundError:
                try:
                    await self.database.create_container(
                        id=container_name,
                        partition_key=PartitionKey(path=config["partition_key"]),
                        default_ttl=config["default_ttl"],
                        indexing_policy=config["indexing_policy"],
                    )
                    logger.debug(f"Created container {container_name}")
                except Exception:
                    # Silently ignore cleanup errors during shutdown
                    pass
            except Exception as re:
                self._diagnostic_log(re, f"read_container:{container_name}")
                raise
        self._initialize_containers()

    async def _verify_connection(self):
        """Verify connection health with a simple read operation"""
        try:
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
        return datetime.now() - self.last_health_check < timedelta(
            seconds=self.health_check_interval
        )

    def _is_transport_closed_error(self, err: Exception) -> bool:
        """Return True when the underlying HTTP transport is already closed."""
        try:
            msg = str(err).lower()
            return (
                "http transport has already been closed" in msg
                or "transport has already been closed" in msg
            )
        except Exception:
            return False

    def is_active(self) -> bool:
        """True if client is connected and not closing."""
        return self.connected and not self._closing

    async def ensure_connected(self):
        """Ensure we have a valid connection with automatic retry"""
        if self._closing:  # new guard
            return False
        if self.connected and self._is_connection_healthy():
            return True

        if not self.is_connecting:
            return await self.connect()

        # Wait for existing connection attempt with timeout
        max_wait = 30  # seconds
        wait_time = 0
        while self.is_connecting and wait_time < max_wait:
            await asyncio.sleep(1)
            wait_time += 1

        return self.connected

    async def close(self):
        """Close Cosmos DB client connection properly with enhanced cleanup"""
        self._closing = True  # set flag early
        try:
            # Use the connection lock to prevent concurrent operations
            async with self._connection_lock:
                await self._cleanup_client()

            # Remove from registry
            try:
                _client_registry.discard(self)
            except Exception:
                pass  # Registry cleanup is not critical

            # logger.info("Cosmos DB connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing Cosmos DB connection: {str(e)}")

    async def _cleanup_client(self):
        """Clean up client resources properly with enhanced session management"""
        cleanup_tasks = []

        # Clean up containers first
        self.vehicles_container = None
        self.services_container = None
        self.commands_container = None
        self.notifications_container = None
        self.status_container = None
        self.database = None

        # Clean up the main client
        if self.client:
            try:
                # Schedule the close operation
                cleanup_tasks.append(self._safe_close_client(self.client))
                self.client = None
            except Exception as e:
                logger.debug(f"Error scheduling client cleanup: {str(e)}")
                self.client = None

        # Close retained credential (closes underlying aiohttp sessions)
        if self._credential:
            try:
                # DefaultAzureCredential has async close()
                cleanup_tasks.append(self._credential.close())
            except Exception as e:
                logger.debug(f"Error scheduling credential cleanup: {str(e)}")
            finally:
                self._credential = None

        # Execute cleanup tasks
        if cleanup_tasks:
            try:
                await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            except Exception as e:
                logger.debug(f"Error during cleanup execution: {str(e)}")

        # Reset connection state
        self.connected = False

    async def _safe_close_client(self, client):
        """Safely close a client with timeout and error handling"""
        try:
            # Use a timeout to prevent hanging
            await asyncio.wait_for(client.close(), timeout=10.0)
            logger.debug("Client closed successfully")
        except asyncio.TimeoutError:
            logger.warning("Client close operation timed out")
        except Exception as e:
            logger.debug(f"Error during client close: {str(e)}")

    # Context manager support for proper resource management
    async def __aenter__(self):
        """Async context manager entry"""
        await self.ensure_connected()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    def __del__(self):
        """Destructor to ensure cleanup"""
        if hasattr(self, "client") and self.client is not None:
            # Schedule cleanup if event loop is running
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running() and not self._cleanup_scheduled:
                    self._cleanup_scheduled = True
                    # Create a task for cleanup without waiting
                    asyncio.create_task(self._cleanup_client())
            except Exception:
                pass  # Ignore errors in destructor

    # Vehicle Status operations

    async def get_vehicle_status(self, vehicle_id: str) -> Optional[VehicleStatus]:
        if self._closing:
            return None
        if not await self.ensure_connected() or not self.status_container:
            logger.warning("No Cosmos DB connection. Cannot get vehicle status.")
            return None
        if not vehicle_id or not isinstance(vehicle_id, str):
            logger.error("Invalid vehicle_id provided")
            return None
        query = (
            "SELECT * FROM c WHERE c.vehicleId = @vehicleId "
            "ORDER BY c._ts DESC OFFSET 0 LIMIT 1"
        )
        return await self._query_one(
            self.status_container,
            query,
            [{"name": "@vehicleId", "value": vehicle_id}],
            partition_key=vehicle_id,
            model_cls=VehicleStatus,
        )

    async def list_vehicle_status(
        self, vehicle_id: str, limit: int = 10
    ) -> List[VehicleStatus]:
        if self._closing:
            return []
        if not await self.ensure_connected() or not self.status_container:
            logger.warning("No Cosmos DB connection. Cannot list vehicle status history.")
            return []
        query = (
            "SELECT TOP @limit * FROM c WHERE c.vehicleId = @vehicleId "
            "ORDER BY c._ts DESC"
        )
        parameters = [
            {"name": "@vehicleId", "value": vehicle_id},
            {"name": "@limit", "value": limit},
        ]
        try:
            items = self.status_container.query_items(
                query=query, parameters=parameters, partition_key=vehicle_id
            )
            result: List[VehicleStatus] = []
            async for item in items:
                self._ensure_timestamp(item)
                result.append(VehicleStatus(**item))
            return result
        except Exception as e:
            logger.error(f"Error listing vehicle status for {vehicle_id}: {e}")
            return []

    async def subscribe_to_vehicle_status(
        self, vehicle_id: str
    ) -> AsyncGenerator[VehicleStatus, None]:
        """
        Subscribe to status updates for a vehicle (polling).
        Yields VehicleStatus instances.
        """
        if self._closing:
            return
        try:
            latest_status = await self.get_vehicle_status(vehicle_id)
            last_timestamp_epoch = 0
            if latest_status:
                yield latest_status
                # Derive last timestamp from ISO string if available
                try:
                    if latest_status.timestamp:
                        last_timestamp_epoch = int(
                            datetime.fromisoformat(
                                latest_status.timestamp.replace("Z", "")
                            ).timestamp()
                        )
                except Exception:
                    pass

            idle_count = 0
            while True:
                if self._closing or not self.connected:
                    break
                # Only reconnect if not connected or status_container is missing
                if not self.connected or not self.status_container:
                    if self._closing or not await self.ensure_connected():
                        break
                try:
                    query = "SELECT * FROM c WHERE c.vehicleId = @vehicleId AND c._ts > @lastTs ORDER BY c._ts DESC"
                    parameters = [
                        {"name": "@vehicleId", "value": vehicle_id},
                        {"name": "@lastTs", "value": last_timestamp_epoch},
                    ]
                    items = self.status_container.query_items(
                        query=query, parameters=parameters, partition_key=vehicle_id
                    )
                    had_updates = False
                    async for item in items:
                        if "timestamp" not in item and "_ts" in item:
                            item["timestamp"] = (
                                datetime.fromtimestamp(item["_ts"], tz=timezone.utc)
                                .isoformat()
                                .replace("+00:00", "Z")
                            )
                        model = VehicleStatus(**item)
                        yield model
                        had_updates = True
                        last_timestamp_epoch = max(
                            last_timestamp_epoch, item.get("_ts", 0)
                        )
                    # Reduce logging in idle loops
                    if had_updates:
                        idle_count = 0
                        await asyncio.sleep(1.0)
                    else:
                        idle_count += 1
                        # Increase sleep time after several idle loops
                        sleep_time = 5.0 if idle_count < 6 else 15.0
                        await asyncio.sleep(sleep_time)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    if self._closing:
                        break
                    if self._is_transport_closed_error(e):
                        break
                    # Only log every 5th error to avoid log spam
                    if idle_count % 5 == 0:
                        logger.error(f"Error in status polling iteration: {str(e)}")
                    await asyncio.sleep(10.0)
                    continue
        except asyncio.CancelledError:
            return
        except Exception as e:
            logger.error(f"Error in vehicle status subscription: {str(e)}")
            return

    async def update_vehicle_status(
        self, vehicle_id: str, status_data: Dict[str, Any]
    ) -> VehicleStatus:
        if not await self.ensure_connected() or not self.status_container:
            logger.warning("No Cosmos DB connection. Cannot update vehicle status.")
            return VehicleStatus(vehicle_id=vehicle_id)
        try:
            if not isinstance(status_data, dict):
                logger.error("status_data must be a dict")
                return VehicleStatus(vehicle_id=vehicle_id)
            sanitized = status_data.copy()
            sanitized.pop("vehicleId", None)
            model = VehicleStatus(vehicle_id=vehicle_id, **sanitized)
            body = model.model_dump(by_alias=True, exclude_none=True)
            body["vehicleId"] = vehicle_id
            body["id"] = str(uuid.uuid4())
            body["timestamp"] = self._now_iso()
            created = await self.status_container.create_item(body=body)
            self._ensure_timestamp(created)
            return VehicleStatus(**created)
        except Exception as e:
            logger.error(f"Error updating vehicle status: {str(e)}")
            return VehicleStatus(vehicle_id=vehicle_id)

    # Vehicles operations

    async def create_vehicle(self, vehicle_data: Dict[str, Any]) -> VehicleProfile:
        """Create a new vehicle"""
        if not await self.ensure_connected() or not self.vehicles_container:
            logger.warning("No Cosmos DB connection. Cannot create vehicle.")
            return VehicleProfile(**vehicle_data)
        try:
            if not isinstance(vehicle_data, VehicleProfile):
                vehicle = VehicleProfile(**vehicle_data)
            else:
                vehicle = vehicle_data
            doc = vehicle.model_dump(by_alias=True, exclude_none=True)
            if "id" not in doc:
                doc["id"] = str(uuid.uuid4())
            if "vehicleId" not in doc:
                doc["vehicleId"] = doc.get("id")
            created = await self.vehicles_container.create_item(body=doc)
            return VehicleProfile(**created)
        except Exception as e:
            logger.error(f"Error creating vehicle: {e}")
            return VehicleProfile(**vehicle_data)

    async def list_vehicles(self) -> List[VehicleProfile]:
        """List all vehicles"""
        if not await self.ensure_connected() or not self.vehicles_container:
            logger.warning("No Cosmos DB connection. Cannot list vehicles.")
            return []
        try:
            query = "SELECT * FROM c"
            items = self.vehicles_container.query_items(query=query)
            result: List[VehicleProfile] = []
            async for item in items:
                result.append(VehicleProfile(**item))
            return result
        except Exception as e:
            logger.error(f"Error listing vehicles: {e}")
            return []

    async def get_vehicle(self, vehicle_id: str) -> Optional[VehicleProfile]:
        """Get a single vehicle by vehicle_id."""
        if not await self.ensure_connected() or not self.vehicles_container:
            logger.warning("No Cosmos DB connection. Cannot get vehicle.")
            return None
        query = "SELECT TOP 1 * FROM c WHERE c.vehicleId = @vehicleId"
        params = [{"name": "@vehicleId", "value": vehicle_id}]
        # First attempt with partition key
        result = await self._query_one(
            self.vehicles_container,
            query,
            params,
            partition_key=vehicle_id,
            model_cls=VehicleProfile,
        )
        if result:
            return result
        # Fallback cross-partition
        return await self._query_one(
            self.vehicles_container, query, params, model_cls=VehicleProfile
        )

    # Services operations

    async def create_service(self, service_data: Dict[str, Any]) -> Service:
        """Create a new service record"""
        if not await self.ensure_connected() or not self.services_container:
            logger.warning("No Cosmos DB connection. Cannot create service.")
            return Service(**service_data)
        try:
            service = (
                service_data
                if isinstance(service_data, Service)
                else Service(**service_data)
            )
            doc = service.model_dump(by_alias=True, exclude_none=True)
            if "id" not in doc:
                doc["id"] = str(uuid.uuid4())
            if "vehicleId" not in doc and service_data.get("vehicleId"):
                doc["vehicleId"] = service_data["vehicleId"]
            created = await self.services_container.create_item(body=doc)
            return Service(**created)
        except Exception as e:
            logger.error(f"Error creating service: {e}")
            return Service(**service_data)

    async def list_services(self, vehicle_id: str) -> List[Service]:
        """List all services for a vehicle"""
        if self._closing:
            return []
        if not await self.ensure_connected() or not self.services_container:
            logger.warning("No Cosmos DB connection. Cannot list services.")
            return []
        try:
            query = "SELECT * FROM c WHERE c.vehicleId = @vehicleId"
            params = [{"name": "@vehicleId", "value": vehicle_id}]
            items = self.services_container.query_items(
                query=query, parameters=params, partition_key=vehicle_id
            )
            result: List[Service] = []
            async for item in items:
                result.append(Service(**item))
            return result
        except Exception as e:
            logger.error(f"Error listing services: {e}")
            return []

    # Commands operations

    async def create_command(self, command_data: Dict[str, Any]) -> Command:
        """Create a new command"""
        if not await self.ensure_connected() or not self.commands_container:
            logger.warning("No Cosmos DB connection. Cannot create command.")
            return Command(**command_data)
        try:
            command = (
                command_data
                if isinstance(command_data, Command)
                else Command(**command_data)
            )
            doc = command.model_dump(by_alias=True, exclude_none=True)
            if "id" not in doc:
                doc["id"] = str(uuid.uuid4())
            if "vehicleId" not in doc and command_data.get("vehicleId"):
                doc["vehicleId"] = command_data["vehicleId"]
            created = await self.commands_container.create_item(body=doc)
            return Command(**created)
        except Exception as e:
            logger.error(f"Error creating command: {e}")
            return Command(**command_data)

    async def update_command(
        self, command_id: str, updated_data: Dict[str, Any]
    ) -> Optional[Command]:
        """Update an existing command"""
        if not await self.ensure_connected() or not self.commands_container:
            logger.warning("No Cosmos DB connection. Cannot update command.")
            return None
        try:
            query = "SELECT * FROM c WHERE c.commandId = @id OR c.command_id = @id OR c.id = @id"
            params = [{"name": "@id", "value": command_id}]
            items = self.commands_container.query_items(query=query, parameters=params)
            existing = None
            async for item in items:
                existing = item
                break
            if not existing:
                logger.warning(f"Command {command_id} not found")
                return None
            # Merge
            for k, v in updated_data.items():
                existing[k] = v
            # Normalize through model
            cmd_model = Command(**existing)
            doc = cmd_model.model_dump(by_alias=True, exclude_none=True)
            # Persist via upsert to avoid partition_key forwarding issues
            replaced = await self.commands_container.upsert_item(body=doc)
            return Command(**replaced)
        except Exception as e:
            logger.error(f"Error updating command {command_id}: {e}")
            return None

    async def list_commands(self, vehicle_id: str = None) -> List[Command]:
        """List all commands with optional filter by vehicle ID"""
        if self._closing:
            return []
        if not await self.ensure_connected() or not self.commands_container:
            logger.warning("No Cosmos DB connection. Cannot list commands.")
            return []
        try:
            if vehicle_id:
                query = (
                    "SELECT * FROM c WHERE c.vehicleId = @vehicleId ORDER BY c._ts DESC"
                )
                params = [{"name": "@vehicleId", "value": vehicle_id}]
                items = self.commands_container.query_items(
                    query=query, parameters=params, partition_key=vehicle_id
                )
            else:
                query = "SELECT * FROM c ORDER BY c._ts DESC"
                items = self.commands_container.query_items(query=query)
            result: List[Command] = []
            async for item in items:
                result.append(Command(**item))
            return result
        except Exception as e:
            logger.error(f"Error listing commands: {e}")
            return []

    async def create_notification(
        self, notification_data: Dict[str, Any]
    ) -> Notification:
        """Create a new notification"""
        if not await self.ensure_connected() or not self.notifications_container:
            logger.warning("No Cosmos DB connection. Cannot create notification.")
            return Notification(**notification_data)
        try:
            notification = (
                notification_data
                if isinstance(notification_data, Notification)
                else Notification(**notification_data)
            )
            doc = notification.model_dump(by_alias=True, exclude_none=True)
            if "id" not in doc:
                doc["id"] = str(uuid.uuid4())
            if "vehicleId" not in doc and notification_data.get("vehicleId"):
                doc["vehicleId"] = notification_data["vehicleId"]
            try:
                created = await self.notifications_container.create_item(body=doc)
            except Exception as e:
                # If HTTP transport closed, try reconnect once and retry
                if self._is_transport_closed_error(e):
                    logger.warning(
                        "HTTP transport closed during create_notification, attempting reconnect and retry"
                    )
                    try:
                        # Cleanup any stale client resources and reconnect
                        await self._cleanup_client()
                        await self.connect()
                        # ensure containers are initialized after reconnect
                        if not self.notifications_container:
                            self._initialize_containers()
                        created = await self.notifications_container.create_item(
                            body=doc
                        )
                    except Exception as retry_exc:
                        logger.error(
                            f"Retry create_notification also failed: {retry_exc}"
                        )
                        raise
                else:
                    raise
            return Notification(**created)
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return Notification(**notification_data)

    async def list_notifications(self, vehicle_id: str = None) -> List[Notification]:
        """List all notifications with optional filter by vehicle ID"""
        if not await self.ensure_connected() or not self.notifications_container:
            logger.warning("No Cosmos DB connection. Cannot list notifications.")
            return []
        try:
            if vehicle_id:
                query = (
                    "SELECT * FROM c WHERE c.vehicleId = @vehicleId ORDER BY c._ts DESC"
                )
                params = [{"name": "@vehicleId", "value": vehicle_id}]
                items = self.notifications_container.query_items(
                    query=query, parameters=params, partition_key=vehicle_id
                )
            else:
                query = "SELECT * FROM c ORDER BY c._ts DESC"
                items = self.notifications_container.query_items(query=query)
            result: List[Notification] = []
            async for item in items:
                result.append(Notification(**item))
            return result
        except Exception as e:
            logger.error(f"Error listing notifications: {e}")
            return []

    async def mark_notification_read(
        self, notificationId: str
    ) -> Optional[Notification]:
        if self._closing:
            return None
        if not await self.ensure_connected() or not self.notifications_container:
            logger.warning("No Cosmos DB connection. Cannot mark notification read.")
            return None
        try:
            query = "SELECT TOP 1 * FROM c WHERE c.id = @id"
            params = [{"name": "@id", "value": notificationId}]
            existing = await self._query_one(
                self.notifications_container, query, params
            )
            if not existing:
                logger.warning(f"Notification {notificationId} not found")
                return None
            existing["read"] = True
            model = Notification(**existing)
            doc = model.model_dump(by_alias=True, exclude_none=True)
            replaced = await self.notifications_container.upsert_item(body=doc)
            return Notification(**replaced)
        except Exception as e:
            logger.error(f"Error marking notification read: {e}")
            return None

    async def delete_notification(self, notificationId: str) -> bool:
        if self._closing:
            return False
        if not await self.ensure_connected() or not self.notifications_container:
            logger.warning("No Cosmos DB connection. Cannot delete notification.")
            return False
        try:
            query = "SELECT TOP 1 c.id, c.vehicleId FROM c WHERE c.id = @id"
            params = [{"name": "@id", "value": notificationId}]
            items = self.notifications_container.query_items(
                query=query, parameters=params
            )
            async for item in items:
                await self.notifications_container.delete_item(
                    item=notificationId, partition_key=item.get("vehicleId")
                )
                return True
            logger.warning(f"Notification {notificationId} not found")
            return False
        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            return False

    # Removed unused _to_camel helper (model-based conversion now)


@lru_cache(maxsize=1)
def get_cosmos_client():
    return CosmosDBClient()


async def get_cosmos_client_connected():
    client = get_cosmos_client()
    await client.ensure_connected()
    return client
