"""
Agent tool implementations for the agentic connected vehicle platform.
"""

from typing import Dict, Any, List, Optional
import datetime
import random

# Mock vehicle database for demo purposes
MOCK_VEHICLES = [
    {"brand": "Tesla", "model": "Model S", "year": 2022, "region": "North America"},
    {"brand": "Toyota", "model": "Prius", "year": 2021, "region": "Asia"},
    {"brand": "BMW", "model": "i4", "year": 2023, "region": "Europe"},
    {"brand": "Ford", "model": "Mustang Mach-E", "year": 2022, "region": "North America"},
    {"brand": "Volkswagen", "model": "ID.4", "year": 2022, "region": "Europe"},
]

# Mock service recommendations
SERVICE_RECOMMENDATIONS = {
    "oil_change": {"interval_months": 6, "interval_miles": 5000},
    "tire_rotation": {"interval_months": 6, "interval_miles": 6000},
    "brake_inspection": {"interval_months": 12, "interval_miles": 12000},
    "battery_check": {"interval_months": 3, "interval_miles": 3000},
}

def search_vehicle_database(brand: Optional[str] = None, 
                           region: Optional[str] = None, 
                           year: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Search the vehicle database based on criteria
    
    Args:
        brand: Vehicle brand/manufacturer
        region: Geographic region
        year: Manufacturing year
        
    Returns:
        List of matching vehicles
    """
    results = MOCK_VEHICLES
    
    if brand:
        results = [v for v in results if v["brand"].lower() == brand.lower()]
    
    if region:
        results = [v for v in results if v["region"].lower() == region.lower()]
    
    if year:
        results = [v for v in results if v["year"] == year]
    
    return results

def recommend_services(vehicle_id: str, 
                       mileage: Optional[int] = None, 
                       last_service_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Recommend services based on vehicle data
    
    Args:
        vehicle_id: The vehicle ID
        mileage: Current vehicle mileage
        last_service_date: Date of last service (ISO format)
        
    Returns:
        List of recommended services
    """
    recommended = []
    
    # Parse last service date if provided
    last_service = None
    if last_service_date:
        try:
            last_service = datetime.datetime.fromisoformat(last_service_date)
        except ValueError:
            pass
    
    today = datetime.datetime.now()
    
    # Check each service
    for service_type, service_info in SERVICE_RECOMMENDATIONS.items():
        should_recommend = False
        reason = ""
        
        # Check mileage-based recommendation
        if mileage and "interval_miles" in service_info:
            # Simulate some randomness in the miles since last service
            miles_since_last = random.randint(service_info["interval_miles"] - 2000, 
                                             service_info["interval_miles"] + 2000)
            if miles_since_last >= service_info["interval_miles"]:
                should_recommend = True
                reason = f"Mileage threshold reached ({miles_since_last} miles since last service)"
        
        # Check time-based recommendation
        if last_service and "interval_months" in service_info:
            months_diff = (today.year - last_service.year) * 12 + today.month - last_service.month
            if months_diff >= service_info["interval_months"]:
                should_recommend = True
                reason = f"Time threshold reached ({months_diff} months since last service)"
        
        if should_recommend:
            recommended.append({
                "service_type": service_type,
                "priority": "high" if "brake" in service_type or "battery" in service_type else "medium",
                "reason": reason,
                "service_details": {
                    "estimated_cost": f"${random.randint(50, 300)}",
                    "estimated_duration": f"{random.randint(1, 4)} hours"
                }
            })
    
    return recommended

def validate_command(command_id: str, command_type: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Validate a command before execution
    
    Args:
        command_id: Command ID
        command_type: Type of command
        parameters: Command parameters
        
    Returns:
        Validation results
    """
    valid_commands = {
        "START_ENGINE": ["ignition_level"],
        "STOP_ENGINE": [],
        "LOCK_DOORS": ["doors"],
        "UNLOCK_DOORS": ["doors"],
        "ACTIVATE_CLIMATE": ["temperature", "fan_speed"]
    }
    
    if command_type not in valid_commands:
        return {
            "valid": False,
            "error": f"Unknown command type: {command_type}",
            "command_id": command_id
        }
    
    # Check required parameters
    required_params = valid_commands[command_type]
    if parameters:
        missing_params = [p for p in required_params if p not in parameters]
        if missing_params:
            return {
                "valid": False,
                "error": f"Missing required parameters: {', '.join(missing_params)}",
                "command_id": command_id
            }
    elif required_params:
        return {
            "valid": False,
            "error": "Missing parameters object",
            "command_id": command_id
        }
    
    return {
        "valid": True,
        "command_id": command_id,
        "command_type": command_type
    }

def analyze_vehicle_data(vehicle_id: str, 
                        time_period: Optional[str] = "7d", 
                        metrics: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Analyze vehicle data for patterns and insights
    
    Args:
        vehicle_id: Vehicle ID
        time_period: Time period for analysis
        metrics: Metrics to analyze
        
    Returns:
        Analysis results
    """
    # Default metrics if none provided
    if not metrics:
        metrics = ["fuel_efficiency", "battery_health", "driving_behavior"]
    
    # Mock analysis results
    analysis = {
        "vehicle_id": vehicle_id,
        "time_period": time_period,
        "analysis_timestamp": datetime.datetime.now().isoformat(),
        "metrics": {}
    }
    
    for metric in metrics:
        if metric == "fuel_efficiency":
            analysis["metrics"][metric] = {
                "value": f"{random.randint(20, 35)} mpg",
                "trend": random.choice(["improving", "declining", "stable"]),
                "percentile": random.randint(50, 95)
            }
        elif metric == "battery_health":
            analysis["metrics"][metric] = {
                "value": f"{random.randint(85, 99)}%",
                "trend": random.choice(["improving", "declining", "stable"]),
                "estimated_replacement": f"{random.randint(1, 5)} years"
            }
        elif metric == "driving_behavior":
            analysis["metrics"][metric] = {
                "harsh_braking_events": random.randint(0, 10),
                "rapid_acceleration_events": random.randint(0, 8),
                "safety_score": random.randint(70, 100),
                "recommendations": [
                    "Reduce harsh braking" if random.random() > 0.5 else None,
                    "Smoother acceleration can improve efficiency" if random.random() > 0.5 else None,
                    "Consider eco-driving techniques" if random.random() > 0.5 else None
                ]
            }
            # Clean up None values
            analysis["metrics"][metric]["recommendations"] = [r for r in analysis["metrics"][metric]["recommendations"] if r]
    
    return analysis

def format_notification(notification_type: str, 
                       message: str, 
                       severity: Optional[str] = "medium") -> Dict[str, Any]:
    """
    Format a notification for delivery
    
    Args:
        notification_type: Type of notification
        message: Notification message
        severity: Severity level
        
    Returns:
        Formatted notification
    """
    notification_templates = {
        "command_execution": {
            "title": "Command Execution Status",
            "icon": "command_icon"
        },
        "service_reminder": {
            "title": "Service Reminder",
            "icon": "service_icon"
        },
        "system_alert": {
            "title": "System Alert",
            "icon": "alert_icon"
        },
        "vehicle_status": {
            "title": "Vehicle Status Update",
            "icon": "status_icon"
        }
    }
    
    template = notification_templates.get(notification_type, {
        "title": "Notification",
        "icon": "default_icon"
    })
    
    # Format based on severity
    priority = 0
    if severity == "low":
        priority = 1
    elif severity == "medium":
        priority = 2
    elif severity == "high":
        priority = 3
    elif severity == "critical":
        priority = 4
    
    return {
        "title": template["title"],
        "message": message,
        "severity": severity,
        "priority": priority,
        "icon": template["icon"],
        "timestamp": datetime.datetime.now().isoformat(),
        "requires_acknowledgment": severity in ["high", "critical"]
    }
