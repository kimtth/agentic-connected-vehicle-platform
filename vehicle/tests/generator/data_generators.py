"""
Consolidated data generators for different entity types with enhanced agent scenario support.
"""

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from dataclasses import asdict

from .base_generator import BaseGenerator, COMMON_REGIONS, COMMON_PRIORITIES, COMMON_DEVICE_TYPES
from .data_models import (
    Vehicle, ServiceRecord, Command, Notification, VehicleStatus,
    PointOfInterest, ChargingStation, Location, VehicleFeatures, TelemetryData
)
from .data_config import (
    VEHICLE_MAKES, VEHICLE_MODELS, VEHICLE_TYPES, VEHICLE_COLORS, VEHICLE_STATUS,
    SERVICE_TYPES, COMMAND_TYPES, COMMAND_STATUS, NOTIFICATION_TYPES, NOTIFICATION_PRIORITY,
    ALERT_MESSAGES, CHARGING_NETWORK_PROVIDERS, CHARGING_STATION_AMENITIES
)


class VehicleDataGenerator(BaseGenerator):
    """Generates vehicle-related data"""
    
    @staticmethod
    def generate_location() -> Location:
        """Generate a random location"""
        return Location(
            latitude=round(random.uniform(25.0, 49.0), 6),
            longitude=round(random.uniform(-125.0, -70.0), 6),
            address=f"{random.randint(100, 999)} Example St, City, State"
        )
    
    def generate(self, **kwargs) -> Dict[str, Any]:
        """Generate a complete vehicle with all agent-specific data"""
        vehicle_id = kwargs.get('vehicle_id', self.generate_id())
        make = random.choice(VEHICLE_MAKES)
        model = random.choice(VEHICLE_MODELS[make])
        current_year = datetime.now().year
        year = random.randint(current_year - 8, current_year)
        
        # Determine if the vehicle is electric
        is_electric = (
            make in ["Tesla"] or 
            model in ["i4", "iX", "e-tron", "Taycan", "Mach-E", "Bolt", "EQS"] or
            random.random() < 0.3
        )
        
        features = VehicleFeatures(
            has_autopilot=is_electric or random.choice([True, False]),
            has_heated_seats=random.choice([True, False]),
            has_remote_start=random.choice([True, False]),
            has_navigation=random.choice([True, False]),
            is_electric=is_electric
        )
        
        telemetry = TelemetryData(
            speed=random.randint(0, 80),
            engine_temp=random.randint(170, 220) if not is_electric else 0,
            oil_level=random.randint(30, 100) if not is_electric else 0,
            tire_pressure={
                "FrontLeft": random.randint(32, 36),
                "FrontRight": random.randint(32, 36),
                "RearLeft": random.randint(32, 36),
                "RearRight": random.randint(32, 36)
            },
            fuel_economy=random.randint(15, 40) if not is_electric else 0,
            odometer=random.randint(1000, 100000),
            battery_voltage=round(random.uniform(12.0, 14.2), 1),
            charging_status=random.choice(["Not Charging", "Charging", "Fast Charging"]) if is_electric else "N/A",
            estimated_range=random.randint(150, 400) if is_electric else random.randint(300, 600)
        )
        
        location = self.generate_location()
        
        vehicle = Vehicle(
            vehicle_id=vehicle_id,
            brand=make,
            vehicle_model=model,
            year=year,
            type=random.choice(VEHICLE_TYPES),
            color=random.choice(VEHICLE_COLORS),
            vin=f"1HGCM82633A{random.randint(100000, 999999)}",
            license_plate=f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}{random.randint(100, 999)}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}",
            status=random.choice(VEHICLE_STATUS),
            mileage=random.randint(1000, 100000),
            fuel_level=0 if is_electric else random.randint(1, 100),
            battery_level=random.randint(30, 100) if is_electric else 100,
            last_location=location,
            features=features,
            region=random.choice(COMMON_REGIONS),
            current_telemetry=telemetry
        )
        
        # Convert to dictionary and adjust field names for Cosmos DB compatibility
        vehicle_dict = asdict(vehicle)
        vehicle_dict["VehicleId"] = vehicle_dict.pop("vehicle_id")
        vehicle_dict["Brand"] = vehicle_dict.pop("brand")
        vehicle_dict["VehicleModel"] = vehicle_dict.pop("vehicle_model")
        vehicle_dict["Year"] = vehicle_dict.pop("year")
        vehicle_dict["Type"] = vehicle_dict.pop("type")
        vehicle_dict["Color"] = vehicle_dict.pop("color")
        vehicle_dict["VIN"] = vehicle_dict.pop("vin")
        vehicle_dict["LicensePlate"] = vehicle_dict.pop("license_plate")
        vehicle_dict["Status"] = vehicle_dict.pop("status")
        vehicle_dict["Mileage"] = vehicle_dict.pop("mileage")
        vehicle_dict["FuelLevel"] = vehicle_dict.pop("fuel_level")
        vehicle_dict["BatteryLevel"] = vehicle_dict.pop("battery_level")
        vehicle_dict["LastUpdated"] = vehicle_dict.pop("last_updated")
        vehicle_dict["LastLocation"] = {
            "Latitude": vehicle_dict["last_location"]["latitude"],
            "Longitude": vehicle_dict["last_location"]["longitude"]
        }
        vehicle_dict.pop("last_location")
        vehicle_dict["OwnerId"] = vehicle_dict.pop("owner_id")
        vehicle_dict["Features"] = {
            "HasAutoPilot": vehicle_dict["features"]["has_autopilot"],
            "HasHeatedSeats": vehicle_dict["features"]["has_heated_seats"],
            "HasRemoteStart": vehicle_dict["features"]["has_remote_start"],
            "HasNavigation": vehicle_dict["features"]["has_navigation"],
            "IsElectric": vehicle_dict["features"]["is_electric"]
        }
        vehicle_dict.pop("features")
        vehicle_dict["Region"] = vehicle_dict.pop("region")
        vehicle_dict["CurrentTelemetry"] = {
            "Speed": vehicle_dict["current_telemetry"]["speed"],
            "EngineTemp": vehicle_dict["current_telemetry"]["engine_temp"],
            "OilLevel": vehicle_dict["current_telemetry"]["oil_level"],
            "TirePressure": vehicle_dict["current_telemetry"]["tire_pressure"],
            "FuelEconomy": vehicle_dict["current_telemetry"]["fuel_economy"],
            "Odometer": vehicle_dict["current_telemetry"]["odometer"],
            "BatteryVoltage": vehicle_dict["current_telemetry"]["battery_voltage"],
            "ChargingStatus": vehicle_dict["current_telemetry"]["charging_status"],
            "EstimatedRange": vehicle_dict["current_telemetry"]["estimated_range"]
        }
        vehicle_dict.pop("current_telemetry")
        
        return vehicle_dict


class ServiceDataGenerator(BaseGenerator):
    """Generates service-related data"""
    
    def generate(self, vehicle_id: Optional[str] = None, is_electric: bool = False, **kwargs) -> Dict[str, Any]:
        """Generate a service record"""
        if vehicle_id is None:
            vehicle_id = self.generate_id()
            
        service_types = SERVICE_TYPES.copy()
        if is_electric:
            if "Oil Change" in service_types:
                service_types.remove("Oil Change")
                service_types.append("Battery Health Check")
        
        service_type = random.choice(service_types)
        service_date = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 180))
        next_service_date = service_date + timedelta(days=random.randint(90, 365))
        
        service_record = ServiceRecord(
            service_code=service_type.replace(" ", "_").upper(),
            description=f"{service_type} service",
            start_date=service_date.isoformat(),
            end_date=service_date.isoformat(),
            next_service_date=next_service_date.isoformat(),
            vehicle_id=vehicle_id,
            mileage=random.randint(1000, 100000),
            next_service_mileage=random.randint(1000, 100000) + random.choice([5000, 7500, 10000, 15000]),
            cost=round(random.uniform(20.0, 500.0), 2),
            location=f"Service Center {random.randint(1, 20)}",
            technician=f"Technician {random.randint(1, 50)}",
            notes=random.choice([
                "Regular maintenance completed",
                "All checks passed",
                "Replaced worn components",
                "Customer reported issues resolved",
                "Recommended additional maintenance in future"
            ]),
            invoice_number=f"INV-{random.randint(10000, 99999)}",
            service_status="Completed",
            service_type=random.choice(["Scheduled", "Repair", "Recall", "Customer Request"]),
            customer_rating=random.randint(1, 5) if random.random() > 0.7 else None
        )
        
        # Convert to dictionary and adjust field names for Cosmos DB compatibility
        service_dict = asdict(service_record)
        service_dict["ServiceCode"] = service_dict.pop("service_code")
        service_dict["Description"] = service_dict.pop("description")
        service_dict["StartDate"] = service_dict.pop("start_date")
        service_dict["EndDate"] = service_dict.pop("end_date")
        service_dict["NextServiceDate"] = service_dict.pop("next_service_date")
        service_dict["nextServiceMileage"] = service_dict.pop("next_service_mileage")
        service_dict["partsReplaced"] = service_dict.pop("parts_replaced")
        service_dict["serviceAdvisories"] = service_dict.pop("service_advisories")
        service_dict["invoiceNumber"] = service_dict.pop("invoice_number")
        service_dict["serviceStatus"] = service_dict.pop("service_status")
        service_dict["serviceType"] = service_dict.pop("service_type")
        service_dict["customerRating"] = service_dict.pop("customer_rating")
        
        return service_dict


class CommandDataGenerator(BaseGenerator):
    """Enhanced command generator that covers all agent scenarios"""
    
    def __init__(self):
        super().__init__()
        self.vehicle_feature_commands = [
            "LIGHTS_ON", "LIGHTS_OFF", "CLIMATE_CONTROL", "WINDOWS_UP", "WINDOWS_DOWN"
        ]
        self.remote_access_commands = [
            "LOCK_DOORS", "UNLOCK_DOORS", "START_ENGINE", "STOP_ENGINE", "HORN_LIGHTS"
        ]
        self.emergency_commands = [
            "EMERGENCY_CALL", "COLLISION_ALERT", "THEFT_NOTIFICATION", "SOS_REQUEST"
        ]
        self.charging_commands = [
            "START_CHARGING", "STOP_CHARGING", "SET_CHARGING_SCHEDULE"
        ]
    
    def generate(self, vehicle_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate a vehicle command"""
        if vehicle_id is None:
            vehicle_id = self.generate_id()
            
        command_type = random.choice(COMMAND_TYPES)
        sent_time = datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 1440))
        executed_time = sent_time + timedelta(minutes=random.randint(1, 10))
        
        parameters = {}
        if command_type == "SetTemperature":
            parameters["temperature"] = random.randint(65, 85)
        
        command = Command(
            vehicle_id=vehicle_id,
            command_type=command_type,
            parameters=parameters,
            status=random.choice(COMMAND_STATUS),
            timestamp=sent_time.isoformat(),
            executed_time=executed_time.isoformat() if random.random() > 0.3 else None,
            initiated_by=f"User{random.randint(1, 10)}",
            response_code=random.choice([200, 201, 400, 404, 500]) if random.random() > 0.7 else None,
            response_message="Command executed successfully" if random.random() > 0.2 else "Command failed",
            priority=random.choice(COMMON_PRIORITIES),
            device_type=random.choice(COMMON_DEVICE_TYPES),
            ip_address=f"192.168.1.{random.randint(1, 254)}",
            authentication_type=random.choice(["Password", "Biometric", "PIN", "OAuth"]),
            command_origin=random.choice(["Local", "Remote"]),
            retry_count=random.randint(0, 3) if random.random() > 0.8 else 0
        )
        
        # Convert to dictionary and adjust field names for Cosmos DB compatibility
        command_dict = asdict(command)
        command_dict["commandId"] = command_dict.pop("command_id")
        command_dict["vehicleId"] = command_dict.pop("vehicle_id")
        command_dict["commandType"] = command_dict.pop("command_type")
        command_dict["executedTime"] = command_dict.pop("executed_time")
        command_dict["initiatedBy"] = command_dict.pop("initiated_by")
        command_dict["responseCode"] = command_dict.pop("response_code")
        command_dict["responseMessage"] = command_dict.pop("response_message")
        command_dict["deviceType"] = command_dict.pop("device_type")
        command_dict["ipAddress"] = command_dict.pop("ip_address")
        command_dict["authenticationType"] = command_dict.pop("authentication_type")
        command_dict["commandOrigin"] = command_dict.pop("command_origin")
        command_dict["retryCount"] = command_dict.pop("retry_count")
        
        return command_dict
    
    def generate_vehicle_feature_command(self, vehicle_id: str) -> Dict[str, Any]:
        """Generate vehicle feature control commands"""
        command_type = random.choice(self.vehicle_feature_commands)
        
        parameters = {}
        if command_type in ["LIGHTS_ON", "LIGHTS_OFF"]:
            parameters = {
                "light_type": random.choice(["headlights", "interior_lights", "hazard_lights"])
            }
        elif command_type == "CLIMATE_CONTROL":
            parameters = {
                "temperature": random.randint(16, 30),
                "action": random.choice(["heating", "cooling", "set_temperature"]),
                "auto": random.choice([True, False])
            }
        elif command_type in ["WINDOWS_UP", "WINDOWS_DOWN"]:
            parameters = {
                "windows": random.choice(["all", "driver", "passenger"])
            }
        
        return self._create_command_base(vehicle_id, command_type, parameters)
    
    def generate_remote_access_command(self, vehicle_id: str) -> Dict[str, Any]:
        """Generate remote access commands"""
        command_type = random.choice(self.remote_access_commands)
        
        parameters = {}
        if command_type in ["LOCK_DOORS", "UNLOCK_DOORS"]:
            parameters = {"doors": "all"}
        elif command_type in ["START_ENGINE", "STOP_ENGINE"]:
            parameters = {"remote": True}
        elif command_type == "HORN_LIGHTS":
            parameters = {"duration": random.randint(5, 15)}
        
        return self._create_command_base(vehicle_id, command_type, parameters)
    
    def generate_emergency_command(self, vehicle_id: str) -> Dict[str, Any]:
        """Generate emergency commands"""
        command_type = random.choice(self.emergency_commands)
        
        parameters = {
            "location": {
                "latitude": round(random.uniform(43.0, 44.0), 6),
                "longitude": round(random.uniform(-80.0, -79.0), 6)
            },
            "timestamp": datetime.now().isoformat()
        }
        
        if command_type == "EMERGENCY_CALL":
            parameters["call_type"] = random.choice(["manual", "automatic"])
        elif command_type == "COLLISION_ALERT":
            parameters["severity"] = random.choice(["minor", "major", "severe"])
        elif command_type == "THEFT_NOTIFICATION":
            parameters["reported_by"] = "owner"
        elif command_type == "SOS_REQUEST":
            parameters["priority"] = "critical"
        
        return self._create_command_base(vehicle_id, command_type, parameters, priority="Critical")
    
    def generate_charging_command(self, vehicle_id: str) -> Dict[str, Any]:
        """Generate charging-related commands"""
        command_type = random.choice(self.charging_commands)
        
        parameters = {}
        if command_type == "SET_CHARGING_SCHEDULE":
            parameters = {
                "schedule": {
                    "start_time": "22:00",
                    "end_time": "06:00",
                    "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
                }
            }
        
        return self._create_command_base(vehicle_id, command_type, parameters)
    
    def _create_command_base(self, vehicle_id: str, command_type: str, parameters: Dict[str, Any], priority: str = "Normal") -> Dict[str, Any]:
        """Create base command structure"""
        return {
            "id": str(uuid.uuid4()),
            "commandId": f"{command_type.lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}",
            "vehicleId": vehicle_id,
            "commandType": command_type,
            "parameters": parameters,
            "status": random.choice(["Sent", "Processing", "Completed", "Failed"]),
            "timestamp": (datetime.now() - timedelta(hours=random.randint(0, 72))).isoformat(),
            "priority": priority,
        }


class NotificationDataGenerator(BaseGenerator):
    """Enhanced notification generator covering all alert types"""
    
    def __init__(self):
        super().__init__()
        self.alert_types = [
            "speed_alert", "curfew_alert", "battery_alert", "maintenance_alert",
            "collision_alert", "theft_alert", "emergency_call", "sos_request",
            "charging_complete", "low_fuel", "service_due"
        ]
    
    def generate(self, vehicle_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate a notification"""
        if vehicle_id is None:
            vehicle_id = self.generate_id()
            
        notification_type = random.choice(NOTIFICATION_TYPES)
        created_time = datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 168))
        
        message = ""
        parameters = {}
        
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
        else:
            message = f"Notification: {notification_type.replace('_', ' ').title()}"
        
        notification = Notification(
            vehicle_id=vehicle_id,
            type=notification_type,
            message=message,
            timestamp=created_time.isoformat(),
            read_time=(created_time + timedelta(hours=random.randint(1, 24))).isoformat() if random.random() > 0.3 else None,
            read=random.choice([True, False]),
            severity=random.choice(NOTIFICATION_PRIORITY),
            source=random.choice(["Vehicle", "System", "Service", "Emergency", "Security"]),
            action_required=notification_type.endswith("_alert"),
            parameters=parameters,
            target_users=[f"User{random.randint(1, 5)}"],
            is_test_notification=random.random() < 0.05
        )
        
        # Convert to dictionary and adjust field names for Cosmos DB compatibility
        notification_dict = asdict(notification)
        notification_dict["notificationId"] = notification_dict.pop("notification_id")
        notification_dict["vehicleId"] = notification_dict.pop("vehicle_id")
        notification_dict["readTime"] = notification_dict.pop("read_time")
        notification_dict["actionRequired"] = notification_dict.pop("action_required")
        notification_dict["actionUrl"] = notification_dict.pop("action_url")
        notification_dict["relatedCommands"] = notification_dict.pop("related_commands")
        notification_dict["targetUsers"] = notification_dict.pop("target_users")
        notification_dict["phoneNumber"] = notification_dict.pop("phone_number")
        notification_dict["isTestNotification"] = notification_dict.pop("is_test_notification")
        # Remove location if None to avoid null values
        if notification_dict["location"] is None:
            notification_dict.pop("location")
        
        return notification_dict
    
    def generate_speed_alert(self, vehicle_id: str) -> Dict[str, Any]:
        """Generate speed limit alert"""
        speed_limit = random.choice([50, 60, 80, 100, 120])
        current_speed = speed_limit + random.randint(5, 30)
        
        return {
            "id": str(uuid.uuid4()),
            "notificationId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": "speed_alert",
            "message": f"Speed limit exceeded: {current_speed} km/h in {speed_limit} km/h zone",
            "timestamp": (datetime.now() - timedelta(minutes=random.randint(0, 1440))).isoformat(),
            "read": random.choice([True, False]),
            "severity": "medium",
            "source": "Vehicle",
            "actionRequired": True,
            "actionUrl": f"/alerts/speed/{vehicle_id}",
            "parameters": {
                "speed_limit": speed_limit,
                "current_speed": current_speed,
                "location": {
                    "latitude": round(random.uniform(43.0, 44.0), 6),
                    "longitude": round(random.uniform(-80.0, -79.0), 6)
                }
            }
        }
    
    def generate_curfew_alert(self, vehicle_id: str) -> Dict[str, Any]:
        """Generate curfew violation alert"""
        return {
            "id": str(uuid.uuid4()),
            "notificationId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": "curfew_alert",
            "message": "Vehicle used outside allowed hours (22:00 - 06:00)",
            "timestamp": (datetime.now() - timedelta(hours=random.randint(0, 48))).isoformat(),
            "read": random.choice([True, False]),
            "severity": "high",
            "source": "System",
            "actionRequired": True,
            "actionUrl": f"/alerts/curfew/{vehicle_id}",
            "parameters": {
                "curfew_start": "22:00",
                "curfew_end": "06:00",
                "violation_time": datetime.now().strftime("%H:%M")
            }
        }
    
    def generate_battery_alert(self, vehicle_id: str) -> Dict[str, Any]:
        """Generate low battery alert"""
        battery_level = random.randint(5, 20)
        
        return {
            "id": str(uuid.uuid4()),
            "notificationId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": "battery_alert",
            "message": f"Low battery warning: {battery_level}% remaining",
            "timestamp": (datetime.now() - timedelta(minutes=random.randint(0, 360))).isoformat(),
            "read": random.choice([True, False]),
            "severity": "high" if battery_level < 10 else "medium",
            "source": "Vehicle",
            "actionRequired": True,
            "actionUrl": f"/charging/{vehicle_id}",
            "parameters": {
                "battery_level": battery_level,
                "estimated_range": battery_level * 4,  # Rough estimate
                "threshold": 20
            }
        }
    
    def generate_emergency_notification(self, vehicle_id: str) -> Dict[str, Any]:
        """Generate emergency-related notifications"""
        emergency_types = ["collision_alert", "theft_alert", "emergency_call", "sos_request"]
        emergency_type = random.choice(emergency_types)
        
        messages = {
            "collision_alert": "Collision detected. Emergency services have been notified.",
            "theft_alert": "Potential vehicle theft detected. Authorities have been notified.",
            "emergency_call": "Emergency call initiated. Help is on the way.",
            "sos_request": "SOS request activated. Emergency services contacted."
        }
        
        return {
            "id": str(uuid.uuid4()),
            "notificationId": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "type": emergency_type,
            "message": messages[emergency_type],
            "timestamp": (datetime.now() - timedelta(minutes=random.randint(0, 60))).isoformat(),
            "read": random.choice([True, False]),
            "severity": "critical",
            "source": "System",
            "actionRequired": True,
            "actionUrl": f"/emergency/{emergency_type}/{vehicle_id}",
            "parameters": {
                "location": {
                    "latitude": round(random.uniform(43.0, 44.0), 6),
                    "longitude": round(random.uniform(-80.0, -79.0), 6)
                },
                "response_time": random.randint(5, 15)
            }
        }


class StatusDataGenerator(BaseGenerator):
    """Generates status-related data"""
    
    def generate(self, vehicle_id: Optional[str] = None, is_electric: bool = False, **kwargs) -> Dict[str, Any]:
        """Generate vehicle status data"""
        if vehicle_id is None:
            vehicle_id = self.generate_id()
            
        battery_level = random.randint(20, 100) if is_electric else random.randint(80, 100)
        
        location = Location(
            latitude=round(random.uniform(25.0, 49.0), 6),
            longitude=round(random.uniform(-125.0, -70.0), 6)
        )
        
        status = VehicleStatus(
            vehicle_id=vehicle_id,
            battery_level=battery_level,
            temperature=random.randint(18, 32),
            speed=random.randint(0, 120) if random.random() > 0.3 else 0,
            oil_level=0 if is_electric else random.randint(20, 100),
            location=location,
            engine_status=random.choice(["on", "off"]),
            door_status={
                "driver": random.choice(["locked", "unlocked"]),
                "passenger": random.choice(["locked", "unlocked"]),
                "rearLeft": random.choice(["locked", "unlocked"]),
                "rearRight": random.choice(["locked", "unlocked"])
            },
            climate_settings={
                "temperature": random.randint(16, 28),
                "fanSpeed": random.choice(["low", "medium", "high"]),
                "isAirConditioningOn": random.choice([True, False]),
                "isHeatingOn": random.choice([True, False])
            }
        )
        
        # Convert to dictionary and adjust field names for Cosmos DB compatibility
        status_dict = asdict(status)
        status_dict["vehicleId"] = status_dict.pop("vehicle_id")
        status_dict["batteryLevel"] = status_dict.pop("battery_level")
        status_dict["oilLevel"] = status_dict.pop("oil_level")
        status_dict["engineStatus"] = status_dict.pop("engine_status")
        status_dict["doorStatus"] = status_dict.pop("door_status")
        status_dict["climateSettings"] = status_dict.pop("climate_settings")
        
        return status_dict


class POIDataGenerator(BaseGenerator):
    """Generates Points of Interest data"""
    
    def generate(self, poi_data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Generate a Point of Interest document"""
        if poi_data is None:
            poi_data = {
                "name": f"POI {random.randint(1, 1000)}",
                "category": random.choice(["Restaurant", "Gas Station", "Shopping", "Entertainment"]),
                "rating": round(random.uniform(1.0, 5.0), 1)
            }
        
        location = Location(
            latitude=round(random.uniform(25.0, 49.0), 6),
            longitude=round(random.uniform(-125.0, -70.0), 6),
            address=f"{random.randint(100, 999)} Example St, City, State"
        )
        
        poi = PointOfInterest(
            name=poi_data["name"],
            category=poi_data["category"],
            rating=poi_data["rating"],
            location=location,
            description=f"Description for {poi_data['name']}",
            opening_hours=f"{random.randint(7, 10)}:00 - {random.randint(17, 22)}:00",
            amenities=random.sample(["Parking", "WiFi", "Restrooms", "Food", "Shopping"], random.randint(1, 4))
        )
        
        # Convert to dictionary and adjust field names for Cosmos DB compatibility
        poi_dict = asdict(poi)
        poi_dict["poiId"] = poi_dict.pop("poi_id")
        poi_dict["openingHours"] = poi_dict.pop("opening_hours")
        poi_dict["lastUpdated"] = poi_dict.pop("last_updated")
        # Remove unused fields
        poi_dict.pop("photos", None)
        poi_dict.pop("contact", None)
        poi_dict.pop("price_level", None)
        poi_dict.pop("tags", None)
        
        return poi_dict


class ChargingStationDataGenerator(BaseGenerator):
    """Generates charging station data"""
    
    def generate(self, station_data: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """Generate a charging station document"""
        if station_data is None:
            station_data = {
                "name": f"Charging Station {random.randint(1, 1000)}",
                "power_level": random.choice(["Level 1", "Level 2", "DC Fast"]),
                "ports": random.randint(2, 12)
            }
        
        charging_points = []
        for i in range(station_data["ports"]):
            charging_points.append({
                "pointId": f"point-{random.randint(1000, 9999)}",
                "connectorType": random.choice(["CCS", "CHAdeMO", "Type 2", "Tesla"]),
                "status": random.choice(["Available", "In Use", "Out of Order", "Reserved"]),
                "power": random.choice([7.4, 11, 22, 50, 150, 350]),
                "lastStatusUpdate": self.get_current_timestamp()
            })
        
        location = Location(
            latitude=round(random.uniform(25.0, 49.0), 6),
            longitude=round(random.uniform(-125.0, -70.0), 6),
            address=f"{random.randint(100, 999)} Example St, City, State"
        )
        
        station = ChargingStation(
            name=station_data["name"],
            power_level=station_data["power_level"],
            region=random.choice(COMMON_REGIONS),
            location=location,
            provider=random.choice(CHARGING_NETWORK_PROVIDERS),
            total_ports=station_data["ports"],
            available_ports=sum(1 for point in charging_points if point["status"] == "Available"),
            charging_points=charging_points,
            amenities=random.sample(CHARGING_STATION_AMENITIES, random.randint(1, 5)),
            status=random.choice(["Operational", "Partial Service", "Under Maintenance"])
        )
        
        # Convert to dictionary and adjust field names for Cosmos DB compatibility
        station_dict = asdict(station)
        station_dict["stationId"] = station_dict.pop("station_id")
        station_dict["powerLevel"] = station_dict.pop("power_level")
        station_dict["totalPorts"] = station_dict.pop("total_ports")
        station_dict["availablePorts"] = station_dict.pop("available_ports")
        station_dict["chargingPoints"] = station_dict.pop("charging_points")
        station_dict["lastUpdated"] = station_dict.pop("last_updated")
        # Remove unused fields
        station_dict.pop("payment_options", None)
        station_dict.pop("opening_hours", None)
        station_dict.pop("pricing", None)
        station_dict.pop("user_rating", None)
        
        return station_dict


class VehicleFeatureStatusGenerator:
    """Generate vehicle feature status data"""
    
    @staticmethod
    def generate_feature_status(vehicle_id: str) -> Dict[str, Any]:
        """Generate current feature status"""
        return {
            "id": str(uuid.uuid4()),
            "vehicleId": vehicle_id,
            "timestamp": datetime.now().isoformat(),
            "features": {
                "lights": {
                    "headlights": random.choice(["on", "off", "auto"]),
                    "interior_lights": random.choice(["on", "off"]),
                    "hazard_lights": random.choice(["on", "off"])
                },
                "climate": {
                    "temperature": random.randint(18, 26),
                    "ac_status": random.choice(["on", "off"]),
                    "heating": random.choice(["on", "off"]),
                    "auto_mode": random.choice([True, False])
                },
                "windows": {
                    "driver": random.choice(["up", "down", "partial"]),
                    "passenger": random.choice(["up", "down", "partial"]),
                    "rear_left": random.choice(["up", "down", "partial"]),
                    "rear_right": random.choice(["up", "down", "partial"])
                },
                "doors": {
                    "locked": random.choice([True, False]),
                    "driver_door": random.choice(["open", "closed"]),
                    "passenger_door": random.choice(["open", "closed"]),
                    "rear_doors": random.choice(["open", "closed"])
                },
                "engine": {
                    "status": random.choice(["running", "off"]),
                    "remote_start_enabled": random.choice([True, False])
                }
            }
        }
