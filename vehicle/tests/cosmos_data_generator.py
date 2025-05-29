"""
Refactored Cosmos DB data generator with improved structure and maintainability.
"""

import os
import sys
import argparse
import random
import asyncio
import time
import json
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from azure.cosmos.aio import CosmosClient
from azure.core.exceptions import AzureError, ServiceRequestError, ServiceResponseError
from azure.identity.aio import DefaultAzureCredential
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError
from azure.cosmos import PartitionKey
from azure.core.tracing.decorator import distributed_trace

from logging_config import get_logger
from generator.data_generators import (
    VehicleDataGenerator, ServiceDataGenerator, CommandDataGenerator, 
    NotificationDataGenerator, StatusDataGenerator, POIDataGenerator, 
    ChargingStationDataGenerator, VehicleFeatureStatusGenerator
)
from generator.data_config import POINTS_OF_INTEREST, CHARGING_STATIONS

logger = get_logger(__name__)


class CosmosConnectionManager:
    """Manages Cosmos DB connections and container operations"""
    
    def __init__(self):
        self.endpoint = os.getenv("COSMOS_DB_ENDPOINT")
        self.key = os.getenv("COSMOS_DB_KEY")
        self.database_name = os.getenv("COSMOS_DB_DATABASE")
        self.use_aad_auth = os.getenv("COSMOS_DB_USE_AAD", "false").lower() == "true"
        print(f"Using AAD auth: {self.use_aad_auth}")
        
        # Container configurations
        self.container_configs = {
            "vehicles": {"partition_key": "/vehicleId", "ttl": -1},
            "services": {"partition_key": "/vehicleId", "ttl": 60 * 60 * 24 * 90},
            "commands": {"partition_key": "/vehicleId", "ttl": 60 * 60 * 24 * 90},
            "notifications": {"partition_key": "/vehicleId", "ttl": 60 * 60 * 24 * 90},
            "VehicleStatus": {"partition_key": "/vehicleId", "ttl": 60 * 60 * 24 * 30},
            "PointsOfInterest": {"partition_key": "/category", "ttl": -1},
            "ChargingStations": {"partition_key": "/region", "ttl": -1},
        }
        
        self.client: Optional[CosmosClient] = None
        self.database = None
        self.containers: Dict[str, Any] = {}
        
        # Retry configuration
        self.max_retry_attempts = 5
        self.retry_base_delay = 1
    
    @distributed_trace
    async def connect(self) -> None:
        """Connect to Cosmos DB with retry logic"""
        if not all([self.endpoint, self.database_name]):
            logger.error("Cosmos DB connection information missing")
            sys.exit(1)

        retry_count = 0
        while retry_count < self.max_retry_attempts:
            try:
                await self._establish_connection()
                await self._ensure_containers_exist()
                logger.info("Successfully connected to Cosmos DB")
                break
                
            except (ServiceRequestError, ServiceResponseError) as e:
                retry_count += 1
                if retry_count >= self.max_retry_attempts:
                    logger.error(f"Max retry attempts reached: {e}")
                    sys.exit(1)
                    
                delay = self.retry_base_delay * (2 ** (retry_count - 1)) + random.uniform(0, 1)
                logger.warning(f"Connection attempt {retry_count} failed: {e}. Retrying in {delay:.2f}s...")
                await asyncio.sleep(delay)
            
            except Exception as e:
                logger.error(f"Failed to connect to Cosmos DB: {e}")
                sys.exit(1)
    
    async def _establish_connection(self) -> None:
        """Establish the initial connection"""
        if self.use_aad_auth:
            credential = DefaultAzureCredential()
            self.client = CosmosClient(self.endpoint, credential=credential)
        else:
            try:
                self.client = CosmosClient(self.endpoint, credential=self.key)
            except AzureError as e:
                if "authorization is disabled" in str(e).lower():
                    logger.warning("Master key auth disabled. Falling back to AAD auth.")
                    self.use_aad_auth = True
                    credential = DefaultAzureCredential()
                    self.client = CosmosClient(self.endpoint, credential=credential)
                else:
                    raise

        # Get or create database
        try:
            self.database = self.client.get_database_client(self.database_name)
            await self.database.read()
            logger.info(f"Using existing database: {self.database_name}")
        except CosmosResourceNotFoundError:
            logger.info(f"Creating database: {self.database_name}")
            self.database = await self.client.create_database(self.database_name)
    
    async def _ensure_containers_exist(self) -> None:
        """Ensure all containers exist"""
        for container_id, config in self.container_configs.items():
            try:
                container = self.database.get_container_client(container_id)
                await container.read()
                self.containers[container_id] = container
                logger.debug(f"Container {container_id} already exists")
            except CosmosResourceNotFoundError:
                logger.info(f"Creating container: {container_id}")
                try:
                    await self.database.create_container(
                        id=container_id,
                        partition_key=PartitionKey(path=config["partition_key"]),
                        default_ttl=config["ttl"]
                    )
                    self.containers[container_id] = self.database.get_container_client(container_id)
                    logger.info(f"Container {container_id} created successfully")
                except Exception as e:
                    logger.error(f"Failed to create container {container_id}: {e}")
                    raise
    
    async def close(self) -> None:
        """Close the connection"""
        if self.client:
            await self.client.close()
            logger.info("Cosmos DB connection closed")
    
    async def clear_all_containers(self) -> Dict[str, int]:
        """Clear all data from all containers"""
        logger.info("Starting to clear all containers...")
        cleared_counts = {}
        
        for container_id in self.container_configs.keys():
            try:
                container = self.containers[container_id]
                cleared_count = await self._clear_container(container, container_id)
                cleared_counts[container_id] = cleared_count
                logger.info(f"Cleared {cleared_count} items from container: {container_id}")
            except Exception as e:
                logger.error(f"Failed to clear container {container_id}: {e}")
                cleared_counts[container_id] = 0
        
        total_cleared = sum(cleared_counts.values())
        logger.info(f"Total items cleared: {total_cleared}")
        return cleared_counts
    
    async def _clear_container(self, container, container_id: str) -> int:
        """Clear all items from a specific container"""
        cleared_count = 0
        
        try:
            # Query all items to get their IDs and partition keys
            query = "SELECT c.id, c._partitionKey FROM c"
            items = []
            
            async for item in container.query_items(query=query, enable_cross_partition_query=True):
                items.append(item)
            
            logger.info(f"Found {len(items)} items to delete in container: {container_id}")
            
            # Delete items in batches
            batch_size = 100
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                tasks = []
                
                for item in batch:
                    # Use the partition key value from the item
                    partition_key = item.get('_partitionKey')
                    if partition_key:
                        tasks.append(self._delete_item_with_retry(container, item['id'], partition_key))
                
                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for result in results:
                        if not isinstance(result, Exception):
                            cleared_count += 1
                
                # Rate limiting between batches
                if i + batch_size < len(items):
                    await asyncio.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error clearing container {container_id}: {e}")
            raise
        
        return cleared_count
    
    async def _delete_item_with_retry(self, container, item_id: str, partition_key: str):
        """Delete an item with retry logic"""
        retry_count = 0
        while retry_count < self.max_retry_attempts:
            try:
                await container.delete_item(item=item_id, partition_key=partition_key)
                return True
            except CosmosHttpResponseError as e:
                if e.status_code == 429 or e.status_code >= 500:
                    retry_count += 1
                    delay = self.retry_base_delay * (2 ** (retry_count - 1)) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                elif e.status_code == 404:
                    # Item already deleted
                    return True
                else:
                    raise
            except Exception as e:
                logger.error(f"Unexpected error deleting item {item_id}: {e}")
                raise
        
        raise Exception(f"Failed to delete item {item_id} after maximum retry attempts")


class DataGenerationOrchestrator:
    """Orchestrates the data generation process"""
    
    def __init__(self, connection_manager: CosmosConnectionManager):
        self.connection_manager = connection_manager
        self.vehicle_generator = VehicleDataGenerator()
        self.service_generator = ServiceDataGenerator()
        self.command_generator = CommandDataGenerator()
        self.notification_generator = NotificationDataGenerator()
        self.status_generator = StatusDataGenerator()
        self.poi_generator = POIDataGenerator()
        self.charging_station_generator = ChargingStationDataGenerator()
        self.feature_status_generator = VehicleFeatureStatusGenerator()
        
        self.vehicle_ids: List[str] = []
        self.electric_vehicles: set = set()
    
    @distributed_trace
    async def generate_static_data(self, num_vehicles: int, services_per_vehicle: int,
                                 commands_per_vehicle: int, notifications_per_vehicle: int,
                                 status_updates_per_vehicle: int) -> Dict[str, Any]:
        """Generate and insert static sample data"""
        start_time = time.time()
        logger.info(f"Generating data for {num_vehicles} vehicles...")
        
        await self.connection_manager.connect()
        
        # Generate vehicles
        vehicles = await self._generate_vehicles(num_vehicles)
        
        # Generate related data for each vehicle
        await self._generate_vehicle_related_data(
            services_per_vehicle, commands_per_vehicle,
            notifications_per_vehicle, status_updates_per_vehicle
        )
        
        # Generate POIs and charging stations
        await self._generate_pois_and_stations()
        
        elapsed_time = time.time() - start_time
        logger.info(f"Sample data generation complete in {elapsed_time:.2f} seconds!")
        
        return self._generate_summary_report(
            num_vehicles, services_per_vehicle, commands_per_vehicle,
            notifications_per_vehicle, status_updates_per_vehicle, elapsed_time
        )
    
    async def _generate_vehicles(self, num_vehicles: int) -> List[Dict[str, Any]]:
        """Generate vehicles and track electric ones"""
        vehicles = []
        
        for i in range(num_vehicles):
            vehicle = self.vehicle_generator.generate()
            vehicle_id = vehicle["VehicleId"]
            self.vehicle_ids.append(vehicle_id)
            vehicles.append(vehicle)
            
            if vehicle["Features"]["IsElectric"]:
                self.electric_vehicles.add(vehicle_id)
        
        # Bulk insert vehicles
        logger.info(f"Inserting {len(vehicles)} vehicles...")
        container = self.connection_manager.containers["vehicles"]
        created_count, error_count = await self._bulk_create_items(container, vehicles)
        logger.info(f"Created {created_count} vehicles (errors: {error_count})")
        
        return vehicles
    
    async def _generate_commands_for_vehicle(self, vehicle_id: str, count: int) -> None:
        """Generate enhanced commands for a vehicle"""
        commands = []
        is_electric = vehicle_id in self.electric_vehicles
        
        # Generate different types of commands
        for _ in range(count):
            command_type = random.choice([
                "vehicle_feature", "remote_access", "emergency", "charging" if is_electric else "general"
            ])
            
            if command_type == "vehicle_feature":
                commands.append(self.command_generator.generate_vehicle_feature_command(vehicle_id))
            elif command_type == "remote_access":
                commands.append(self.command_generator.generate_remote_access_command(vehicle_id))
            elif command_type == "emergency":
                commands.append(self.command_generator.generate_emergency_command(vehicle_id))
            elif command_type == "charging" and is_electric:
                commands.append(self.command_generator.generate_charging_command(vehicle_id))
            else:
                commands.append(self.command_generator.generate(vehicle_id))
        
        if commands:
            container = self.connection_manager.containers["commands"]
            created_count, error_count = await self._bulk_create_items(container, commands)
            logger.debug(f"Created {created_count} enhanced commands for vehicle {vehicle_id} (errors: {error_count})")
    
    async def _generate_notifications_for_vehicle(self, vehicle_id: str, count: int) -> None:
        """Generate enhanced notifications for a vehicle"""
        notifications = []
        
        # Generate different types of notifications
        for _ in range(count):
            notification_type = random.choice([
                "speed_alert", "curfew_alert", "battery_alert", "emergency", "general"
            ])
            
            if notification_type == "speed_alert":
                notifications.append(self.notification_generator.generate_speed_alert(vehicle_id))
            elif notification_type == "curfew_alert":
                notifications.append(self.notification_generator.generate_curfew_alert(vehicle_id))
            elif notification_type == "battery_alert":
                notifications.append(self.notification_generator.generate_battery_alert(vehicle_id))
            elif notification_type == "emergency":
                notifications.append(self.notification_generator.generate_emergency_notification(vehicle_id))
            else:
                notifications.append(self.notification_generator.generate(vehicle_id))
        
        if notifications:
            container = self.connection_manager.containers["notifications"]
            created_count, error_count = await self._bulk_create_items(container, notifications)
            logger.debug(f"Created {created_count} enhanced notifications for vehicle {vehicle_id} (errors: {error_count})")
    
    async def _generate_feature_status_for_vehicle(self, vehicle_id: str) -> None:
        """Generate vehicle feature status data"""
        feature_status = self.feature_status_generator.generate_feature_status(vehicle_id)
        
        # Add to vehicle status container
        container = self.connection_manager.containers["VehicleStatus"]
        try:
            await container.create_item(body=feature_status)
            logger.debug(f"Created feature status for vehicle {vehicle_id}")
        except Exception as e:
            logger.error(f"Failed to create feature status for vehicle {vehicle_id}: {e}")

    async def _generate_vehicle_related_data(self, services_per_vehicle: int,
                                           commands_per_vehicle: int, notifications_per_vehicle: int,
                                           status_updates_per_vehicle: int) -> None:
        """Generate services, commands, notifications, and status updates"""
        for vehicle_id in self.vehicle_ids:
            is_electric = vehicle_id in self.electric_vehicles
            
            # Generate and insert each data type
            await self._generate_services_for_vehicle(vehicle_id, services_per_vehicle, is_electric)
            await self._generate_commands_for_vehicle(vehicle_id, commands_per_vehicle)
            await self._generate_notifications_for_vehicle(vehicle_id, notifications_per_vehicle)
            await self._generate_status_updates_for_vehicle(vehicle_id, status_updates_per_vehicle, is_electric)
            await self._generate_feature_status_for_vehicle(vehicle_id)
            
            logger.info(f"Completed enhanced data generation for vehicle: {vehicle_id}")
    
    async def _generate_services_for_vehicle(self, vehicle_id: str, count: int, is_electric: bool) -> None:
        """Generate services for a vehicle"""
        services = [self.service_generator.generate(vehicle_id, is_electric) for _ in range(count)]
        if services:
            container = self.connection_manager.containers["services"]
            created_count, error_count = await self._bulk_create_items(container, services)
            logger.debug(f"Created {created_count} services for vehicle {vehicle_id} (errors: {error_count})")
    
    async def _generate_status_updates_for_vehicle(self, vehicle_id: str, count: int, is_electric: bool) -> None:
        """Generate status updates for a vehicle"""
        status_updates = [self.status_generator.generate(vehicle_id, is_electric) for _ in range(count)]
        if status_updates:
            container = self.connection_manager.containers["VehicleStatus"]
            created_count, error_count = await self._bulk_create_items(container, status_updates)
            logger.debug(f"Created {created_count} status updates for vehicle {vehicle_id} (errors: {error_count})")
    
    async def _generate_pois_and_stations(self) -> None:
        """Generate POIs and charging stations"""
        # Generate POIs
        logger.info("Generating points of interest...")
        pois = [self.poi_generator.generate(poi_data) for poi_data in POINTS_OF_INTEREST]
        if pois:
            container = self.connection_manager.containers["PointsOfInterest"]
            created_count, error_count = await self._bulk_create_items(container, pois)
            logger.info(f"Created {created_count} POIs (errors: {error_count})")
        
        # Generate charging stations
        logger.info("Generating charging stations...")
        stations = [self.charging_station_generator.generate(station_data) for station_data in CHARGING_STATIONS]
        if stations:
            container = self.connection_manager.containers["ChargingStations"]
            created_count, error_count = await self._bulk_create_items(container, stations)
            logger.info(f"Created {created_count} charging stations (errors: {error_count})")
    
    @distributed_trace
    async def _bulk_create_items(self, container, items: List[Dict[str, Any]], batch_size: int = 100) -> tuple[int, int]:
        """Create items in batches with retry logic"""
        created_count = 0
        error_count = 0
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            tasks = [self._create_item_with_retry(container, item) for item in batch]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                else:
                    created_count += 1
                    
            if i + batch_size < len(items):
                await asyncio.sleep(0.5)  # Rate limiting
                
        return created_count, error_count
    
    async def _create_item_with_retry(self, container, item: Dict[str, Any]):
        """Create an item with retry logic"""
        retry_count = 0
        while retry_count < self.connection_manager.max_retry_attempts:
            try:
                return await container.create_item(body=item)
            except CosmosHttpResponseError as e:
                if e.status_code == 429 or e.status_code >= 500:
                    retry_count += 1
                    delay = self.connection_manager.retry_base_delay * (2 ** (retry_count - 1)) + random.uniform(0, 1)
                    await asyncio.sleep(delay)
                else:
                    raise
            except Exception as e:
                logger.error(f"Unexpected error creating item: {e}")
                raise
                
        raise Exception("Failed to create item after maximum retry attempts")
    
    def _generate_summary_report(self, num_vehicles: int, services_per_vehicle: int,
                               commands_per_vehicle: int, notifications_per_vehicle: int,
                               status_updates_per_vehicle: int, elapsed_time: float) -> Dict[str, Any]:
        """Generate a summary report"""
        return {
            "vehicles": len(self.vehicle_ids),
            "electric_vehicles": len(self.electric_vehicles),
            "services": services_per_vehicle * len(self.vehicle_ids),
            "commands": commands_per_vehicle * len(self.vehicle_ids),
            "notifications": notifications_per_vehicle * len(self.vehicle_ids),
            "status_updates": status_updates_per_vehicle * len(self.vehicle_ids),
            "pois": len(POINTS_OF_INTEREST),
            "charging_stations": len(CHARGING_STATIONS),
            "elapsed_seconds": elapsed_time
        }


class CosmosDataGenerator:
    """Main data generator class - refactored for better organization"""
    
    def __init__(self):
        self.connection_manager = CosmosConnectionManager()
        self.orchestrator = DataGenerationOrchestrator(self.connection_manager)
    
    async def generate_and_insert_data(self, num_vehicles: int, services_per_vehicle: int,
                                     commands_per_vehicle: int, notifications_per_vehicle: int,
                                     status_updates_per_vehicle: int) -> Dict[str, Any]:
        """Generate and insert sample data"""
        try:
            summary = await self.orchestrator.generate_static_data(
                num_vehicles, services_per_vehicle, commands_per_vehicle,
                notifications_per_vehicle, status_updates_per_vehicle
            )
            logger.info(f"Generation summary: {json.dumps(summary, indent=2)}")
            return summary
        finally:
            await self.connection_manager.close()
    
    async def generate_live_data(self, duration_minutes: int = 60, update_interval_seconds: int = 30) -> None:
        """Generate live data updates"""
        # This method would need to be implemented similar to the original
        # but using the new structure
        logger.info("Live data generation not yet implemented in refactored version")
    
    async def clear_all_data(self) -> Dict[str, int]:
        """Clear all data from Cosmos DB containers"""
        try:
            await self.connection_manager.connect()
            cleared_counts = await self.connection_manager.clear_all_containers()
            logger.info("Database cleared successfully")
            return cleared_counts
        finally:
            await self.connection_manager.close()


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Generate sample data for Connected Vehicle Platform')
    parser.add_argument('--vehicles', type=int, default=20,
                        help='Number of vehicles to generate (default: 20)')
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
    parser.add_argument('--purge', action='store_true',
                        help='Clear all existing data from Cosmos DB containers before generating new data')
    return parser.parse_args()

async def main():
    """Main entry point for the script"""
    args = parse_args()
    
    load_dotenv(override=True)
    
    required_vars = ["COSMOS_DB_ENDPOINT", "COSMOS_DB_DATABASE"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    generator = CosmosDataGenerator()
    
    try:
        # Clear all data if purge flag is set
        if args.purge:
            logger.info("Purge flag detected - clearing all existing data...")
            cleared_counts = await generator.clear_all_data()
            logger.info(f"Cleared data summary: {json.dumps(cleared_counts, indent=2)}")
        
        if args.live:
            await generator.generate_live_data(args.duration, args.interval)
        else:
            await generator.generate_and_insert_data(
                args.vehicles, args.services, args.commands,
                args.notifications, args.status_updates
            )
    except KeyboardInterrupt:
        logger.info("Data generation interrupted by user")
    except Exception as e:
        logger.error(f"Error during data generation: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
    # Clear all data and generate new sample data
    # python cosmos_data_generator.py --purge --vehicles 50

    # Just clear all data without generating new data
    # python cosmos_data_generator.py --purge --vehicles 0