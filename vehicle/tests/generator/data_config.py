"""
Configuration and sample data for the Cosmos DB data generator.
"""

from typing import Dict, List

# Vehicle data constants
VEHICLE_MAKES = ["Tesla", "BMW", "Mercedes", "Toyota", "Honda", "Ford", "Chevrolet", "Audi", "Porsche", "Lexus"]

VEHICLE_MODELS: Dict[str, List[str]] = {
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

# Service data constants
SERVICE_TYPES = ["Oil Change", "Tire Rotation", "Brake Service", "Battery Replacement", "Air Filter", "Transmission Service"]

# Command data constants
COMMAND_TYPES = ["LockDoors", "UnlockDoors", "StartEngine", "StopEngine", "HonkHorn", "FlashLights", "SetTemperature"]
COMMAND_STATUS = ["Pending", "Sent", "Delivered", "Executed", "Failed"]

# Notification data constants
NOTIFICATION_TYPES = ["service_reminder", "low_fuel_alert", "low_battery_alert", "security_alert", "system_update", "speed_alert", "curfew_alert", "geofence_alert"]
NOTIFICATION_PRIORITY = ["low", "medium", "high", "critical"]

# Points of interest data
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

# ...existing alert messages, diagnostic data, etc...
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
    # ...existing code...
}

# Battery diagnostics data
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

# Enhanced diagnostic and battery data
DIAGNOSTIC_ISSUE_TYPES = [
    "ENGINE_CHECK", "ABS_WARNING", "TIRE_PRESSURE_LOW", "BATTERY_LOW", 
    "OIL_PRESSURE_LOW", "TRANSMISSION_WARNING", "BRAKE_SYSTEM_WARNING",
    "AIRBAG_SYSTEM_WARNING", "COOLANT_TEMPERATURE_HIGH", "ELECTRICAL_SYSTEM_WARNING"
]

BRAKE_WEAR_LEVELS = ["Good", "Fair", "Poor", "Critical"]
ENGINE_HEALTH_LEVELS = ["Excellent", "Good", "Fair", "Poor", "Critical"]
TIRE_CONDITIONS = ["Excellent", "Good", "Fair", "Worn", "Needs Replacement"]

# Charging network providers
CHARGING_NETWORK_PROVIDERS = [
    "ChargePoint", "Electrify America", "EVgo", "Tesla Supercharger", "Blink", 
    "Shell Recharge", "Volta", "Ionity", "FastNed", "GreenWay"
]

CHARGING_STATION_AMENITIES = [
    "Restrooms", "Food", "WiFi", "Shopping", "Waiting Area", "24/7 Access", 
    "Covered Parking", "Security Cameras", "Lounge", "Restaurant"
]