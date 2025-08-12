import json
import random
from pathlib import Path
from typing import Dict, Any, List

# Make package imports resilient when running as script
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parents[3] 

# Use package-relative imports (run as module: python -m vehicle.tests.generator.generate_sample_data)
from .data_generators import (
    VehicleDataGenerator, ServiceDataGenerator, CommandDataGenerator,
    NotificationDataGenerator, StatusDataGenerator, POIDataGenerator,
    ChargingStationDataGenerator
)


def write_json(path: Path, docs: List[Dict[str, Any]]) -> int:
    """Write a list of documents as a single JSON array."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
    return len(docs)


def generate_bulk(
    vehicles_count: int,
    commands_per_vehicle: int,
    notifications_per_vehicle: int,
    services_per_vehicle: int,
    statuses_per_vehicle: int,
    pois_count: int,
    stations_count: int,
    seed: int = 42
) -> Dict[str, List[Dict[str, Any]]]:
    random.seed(seed)

    vehicles_gen = VehicleDataGenerator()
    commands_gen = CommandDataGenerator()
    services_gen = ServiceDataGenerator()
    notifications_gen = NotificationDataGenerator()
    statuses_gen = StatusDataGenerator()
    poi_gen = POIDataGenerator()
    station_gen = ChargingStationDataGenerator()

    # Vehicles
    vehicles: List[Dict[str, Any]] = [vehicles_gen.generate() for _ in range(vehicles_count)]
    vehicle_ids = [v["VehicleId"] for v in vehicles]

    # Status, Services, Commands, Notifications per vehicle
    statuses: List[Dict[str, Any]] = []
    services: List[Dict[str, Any]] = []
    commands: List[Dict[str, Any]] = []
    notifications: List[Dict[str, Any]] = []

    for vid in vehicle_ids:
        # Status history
        for _ in range(statuses_per_vehicle):
            statuses.append(statuses_gen.generate(vehicle_id=vid, is_electric=False))

        # Service records
        for _ in range(services_per_vehicle):
            services.append(services_gen.generate(vehicle_id=vid, is_electric=False))

        # Commands (mix of types)
        for _ in range(commands_per_vehicle):
            choice = random.choice(["feature", "remote", "emergency", "charging", "generic"])
            if choice == "feature":
                commands.append(commands_gen.generate_vehicle_feature_command(vid))
            elif choice == "remote":
                commands.append(commands_gen.generate_remote_access_command(vid))
            elif choice == "emergency":
                commands.append(commands_gen.generate_emergency_command(vid))
            elif choice == "charging":
                commands.append(commands_gen.generate_charging_command(vid))
            else:
                commands.append(commands_gen.generate(vehicle_id=vid))

        # Notifications
        for _ in range(notifications_per_vehicle):
            notifications.append(notifications_gen.generate(vehicle_id=vid))

    # POIs and Charging Stations (global)
    pois: List[Dict[str, Any]] = [poi_gen.generate() for _ in range(pois_count)]
    stations: List[Dict[str, Any]] = [station_gen.generate() for _ in range(stations_count)]

    return {
        "vehicles": vehicles,
        "vehicle_status": statuses,
        "service_records": services,
        "commands": commands,
        "notifications": notifications,
        "pois": pois,
        "charging_stations": stations,
    }


def main():
    # Hard-coded configuration for bulk data generation
    VEHICLES = 25
    COMMANDS_PER_VEHICLE = 2
    NOTIFICATIONS_PER_VEHICLE = 2
    SERVICES_PER_VEHICLE = 1
    STATUSES_PER_VEHICLE = 1
    POIS = 20
    STATIONS = 10
    SEED = 42

    out_dir = Path(_PROJECT_ROOT / "seed_output")
    out_dir.mkdir(parents=True, exist_ok=True)

    data = generate_bulk(
        vehicles_count=VEHICLES,
        commands_per_vehicle=COMMANDS_PER_VEHICLE,
        notifications_per_vehicle=NOTIFICATIONS_PER_VEHICLE,
        services_per_vehicle=SERVICES_PER_VEHICLE,
        statuses_per_vehicle=STATUSES_PER_VEHICLE,
        pois_count=POIS,
        stations_count=STATIONS,
        seed=SEED
    )

    files_written = {
        "vehicles.json": write_json(out_dir / "vehicles.json", data["vehicles"]),
        "vehicle_status.json": write_json(out_dir / "vehicle_status.json", data["vehicle_status"]),
        "service_records.json": write_json(out_dir / "service_records.json", data["service_records"]),
        "commands.json": write_json(out_dir / "commands.json", data["commands"]),
        "notifications.json": write_json(out_dir / "notifications.json", data["notifications"]),
        "pois.json": write_json(out_dir / "pois.json", data["pois"]),
        "charging_stations.json": write_json(out_dir / "charging_stations.json", data["charging_stations"]),
    }

    summary = {
        "output_dir": str(out_dir),
        "counts": {name: count for name, count in files_written.items()}
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()

