"""
Agent tool implementations for the agentic connected vehicle platform.
Uses real data from Azure Cosmos DB.
"""
import datetime
from typing import Dict, Any, List, Optional

# Configure logging
from utils.logging_config import get_logger
logger = get_logger(__name__)

# Service recommendation parameters (business logic)
SERVICE_RECOMMENDATIONS = {
    "oil_change": {"interval_months": 6, "interval_miles": 5000},
    "tire_rotation": {"interval_months": 6, "interval_miles": 6000},
    "brake_inspection": {"interval_months": 12, "interval_miles": 12000},
    "battery_check": {"interval_months": 3, "interval_miles": 3000},
}

async def get_vehicles_from_cosmos() -> List[Dict[str, Any]]:
    """
    Get vehicle data from Azure Cosmos DB
    
    Returns:
        List of vehicles from Cosmos DB
    """
    from azure.cosmos_db import cosmos_client
    
    # Ensure connection before fetching data
    await cosmos_client.ensure_connected()
    
    try:
        # Get vehicles from Cosmos DB
        vehicles = await cosmos_client.list_vehicles()
        
        # Map to the format expected by the tools
        formatted_vehicles = []
        for vehicle in vehicles:
            formatted_vehicles.append({
                "brand": vehicle.get("brand", ""),
                "model": vehicle.get("model", ""),
                "year": vehicle.get("year", 0),
                "region": vehicle.get("region", "North America"),
                "vehicleId": vehicle.get("vehicleId", ""),
                "mileage": vehicle.get("mileage", 0),
                "status": vehicle.get("status", "active"),
                "isElectric": vehicle.get("features", {}).get("isElectric", False),
                "fuelLevel": vehicle.get("fuelLevel", 0),
                "batteryLevel": vehicle.get("batteryLevel", 0),
                "lastLocation": vehicle.get("lastLocation", {})
            })
        
        return formatted_vehicles
    except Exception as e:
        logger.error(f"Failed to get vehicles from Cosmos DB: {str(e)}")
        return []

async def search_vehicle_database(brand: Optional[str] = None, 
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
    # Get vehicles from Cosmos DB
    vehicles = await get_vehicles_from_cosmos()
    
    # Filter based on criteria
    results = vehicles
    
    if brand:
        results = [v for v in results if v["brand"].lower() == brand.lower()]
    
    if region:
        results = [v for v in results if v["region"].lower() == region.lower()]
    
    if year:
        results = [v for v in results if v["year"] == year]
    
    return results

async def get_services_from_cosmos(vehicle_id: str) -> List[Dict[str, Any]]:
    """
    Get service data from Cosmos DB for a specific vehicle
    
    Args:
        vehicle_id: ID of the vehicle
        
    Returns:
        List of services from Cosmos DB
    """
    from azure.cosmos_db import cosmos_client
    
    try:
        # Get services from Cosmos DB
        services = await cosmos_client.list_services(vehicle_id)
        return services
    except Exception as e:
        logger.error(f"Failed to get services from Cosmos DB: {str(e)}")
        return []

async def recommend_services(vehicle_id: str, 
                       mileage: Optional[int] = None, 
                       last_service_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Recommend services based on vehicle data from Cosmos DB
    
    Args:
        vehicle_id: The vehicle ID
        mileage: Current vehicle mileage
        last_service_date: Date of last service (ISO format)
        
    Returns:
        List of recommended services
    """
    recommended = []
    
    # Get vehicle details
    try:
        # Try to get all vehicles and find the one with matching ID
        all_vehicles = await get_vehicles_from_cosmos()
        vehicle = next((v for v in all_vehicles if v.get("vehicleId") == vehicle_id), None)
        
        # If vehicle found and mileage not provided, use vehicle mileage
        if vehicle and not mileage:
            mileage = vehicle.get("mileage", 0)
            
        # Check if vehicle is electric
        is_electric = vehicle.get("isElectric", False) if vehicle else False
    except Exception as e:
        logger.error(f"Error getting vehicle details: {str(e)}")
        # Continue with provided mileage
        is_electric = False
    
    # Get service history from Cosmos DB for more accurate recommendations
    service_history = await get_services_from_cosmos(vehicle_id)
    
    # Parse last service date if provided
    last_service = None
    if last_service_date:
        try:
            last_service = datetime.datetime.fromisoformat(last_service_date)
        except ValueError:
            # Try to find last service date from service history
            if service_history:
                # Sort by service date descending
                sorted_services = sorted(
                    service_history,
                    key=lambda s: s.get("startDate", ""),
                    reverse=True
                )
                
                # Get date from most recent service
                if sorted_services:
                    last_service_str = sorted_services[0].get("startDate", "")
                    try:
                        last_service = datetime.datetime.fromisoformat(last_service_str)
                    except (ValueError, TypeError):
                        pass
    
    today = datetime.datetime.now()
    
    # Check each service type for recommendation
    for service_type, service_info in SERVICE_RECOMMENDATIONS.items():
        # Skip oil change for electric vehicles
        if service_type == "oil_change" and is_electric:
            continue
            
        should_recommend = False
        reason = ""
        
        # Check if this service type exists in service history
        matching_services = [s for s in service_history 
                             if service_type.lower() in s.get("serviceCode", "").lower()]
        
        # Get the most recent matching service
        last_matching_service = None
        if matching_services:
            # Find most recent service of this type
            sorted_matching = sorted(
                matching_services,
                key=lambda s: s.get("startDate", ""),
                reverse=True
            )
            if sorted_matching:
                last_matching_service = sorted_matching[0]
                
                # Extract date and mileage from last service
                last_service_str = last_matching_service.get("startDate", "")
                last_service_mileage = last_matching_service.get("mileage", 0)
                
                try:
                    last_service = datetime.datetime.fromisoformat(last_service_str)
                except (ValueError, TypeError):
                    pass
        
        # Check mileage-based recommendation if we have mileage data
        if mileage and "interval_miles" in service_info:
            # If we have last service mileage, calculate miles since
            if last_matching_service and "mileage" in last_matching_service:
                miles_since_last = mileage - last_matching_service["mileage"]
                if miles_since_last >= service_info["interval_miles"]:
                    should_recommend = True
                    reason = f"Mileage threshold reached ({miles_since_last} miles since last service)"
            elif mileage >= service_info["interval_miles"]:
                should_recommend = True
                reason = f"Mileage threshold reached (current mileage: {mileage})"
        
        # Check time-based recommendation
        if last_service and "interval_months" in service_info:
            months_diff = (today.year - last_service.year) * 12 + today.month - last_service.month
            if months_diff >= service_info["interval_months"]:
                should_recommend = True
                reason = f"Time threshold reached ({months_diff} months since last service)"
        
        # Special case for electric vehicles - recommend battery check more often
        if is_electric and service_type == "battery_check" and not should_recommend:
            should_recommend = True
            reason = "Regular battery health check recommended for electric vehicles"
        
        if should_recommend:
            # Determine cost from service history if available
            cost = 0
            if last_matching_service and "cost" in last_matching_service:
                cost = float(last_matching_service["cost"])
            elif service_type == "oil_change":
                cost = 50
            elif service_type == "tire_rotation":
                cost = 30
            elif service_type == "brake_inspection":
                cost = 100
            elif service_type == "battery_check":
                cost = 25
            else:
                cost = 75
            
            recommended.append({
                "serviceType": service_type,
                "priority": "high" if "brake" in service_type or "battery" in service_type else "medium",
                "reason": reason,
                "serviceDetails": {
                    "estimatedCost": f"${cost}",
                    "estimatedDuration": "1-2 hours"
                }
            })
    
    return recommended

async def validate_command(command_id: str, command_type: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
        "start_engine": ["ignition_level"],
        "stop_engine": [],
        "lock_doors": ["doors"],
        "unlock_doors": ["doors"],
        "activate_climate": ["temperature", "fan_speed"]
    }
    
    if command_type not in valid_commands:
        return {
            "valid": False,
            "error": f"Unknown command type: {command_type}",
            "commandId": command_id
        }
    
    # Check required parameters
    required_params = valid_commands[command_type]
    if parameters:
        missing_params = [p for p in required_params if p not in parameters]
        if missing_params:
            return {
                "valid": False,
                "error": f"Missing required parameters: {', '.join(missing_params)}",
                "commandId": command_id
            }
    elif required_params:
        return {
            "valid": False,
            "error": "Missing parameters object",
            "commandId": command_id
        }
    
    return {
        "valid": True,
        "commandId": command_id,
        "commandType": command_type
    }

async def get_latest_status_from_cosmos(vehicle_id: str) -> Dict[str, Any]:
    """
    Get the latest status data from the VehicleStatus container
    
    Args:
        vehicle_id: ID of the vehicle
        
    Returns:
        Latest status data or empty dict if unavailable
    """
    from azure.cosmos_db import cosmos_client
    
    # Ensure connection before fetching data
    await cosmos_client.ensure_connected()
    
    try:
        # For this we need to use the status_container directly
        status_container = cosmos_client.status_container
        if not status_container:
            logger.warning("Status container not initialized")
            return {}
            
        # Query for latest status by timestamp
        query = "SELECT TOP 1 * FROM c WHERE c.vehicleId = @vehicleId ORDER BY c.timestamp DESC"
        parameters = [{"name": "@vehicleId", "value": vehicle_id}]
        
        items = status_container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        )
        
        async for item in items:
            return {
                "batteryLevel": item.get("batteryLevel", 0),
                "temperature": item.get("temperature", 0),
                "speed": item.get("speed", 0),
                "oilRemaining": item.get("oilLevel", 0),
                "engineStatus": item.get("engineStatus", "off"),
                "doorStatus": item.get("doorStatus", {}),
                "climateSettings": item.get("climateSettings", {})
            }
            
        return {}
    except Exception as e:
        logger.error(f"Failed to get latest status from Cosmos DB: {str(e)}")
        return {}

async def analyze_vehicle_data(vehicle_id: str, 
                        time_period: Optional[str] = "7d", 
                        metrics: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Analyze vehicle data from Cosmos DB for patterns and insights
    
    Args:
        vehicle_id: Vehicle ID
        time_period: Time period for analysis
        metrics: Metrics to analyze
        
    Returns:
        Analysis results
    """
    from azure.cosmos_db import cosmos_client
    
    # Normalize and default metrics to camelCase
    if not metrics:
        metrics = ["fuelEfficiency", "batteryHealth", "drivingBehavior"]
    else:
        normalized = []
        for m in metrics:
            # convert possible snake_case to camelCase
            parts = m.split('_')
            if len(parts) > 1:
                m = parts[0] + ''.join(p.capitalize() for p in parts[1:])
            normalized.append(m)
        metrics = normalized
    
    # Get real vehicle status
    vehicle_status = await get_latest_status_from_cosmos(vehicle_id)
    
    # Initialize with base structure
    analysis = {
        "vehicleId": vehicle_id,
        "timePeriod": time_period,
        "analysisTimestamp": datetime.datetime.now().isoformat(),
        "metrics": {}
    }
    
    # Get vehicle details for additional context
    try:
        all_vehicles = await get_vehicles_from_cosmos()
        vehicle = next((v for v in all_vehicles if v.get("vehicleId") == vehicle_id), None)
        
        if vehicle:
            analysis["vehicleDetails"] = {
                "brand": vehicle.get("brand", ""),
                "model": vehicle.get("model", ""),
                "year": vehicle.get("year", ""),
                "mileage": vehicle.get("mileage", 0),
                "isElectric": vehicle.get("isElectric", False)
            }
            
            # Use is_electric flag for appropriate analysis
            is_electric = vehicle.get("isElectric", False)
        else:
            is_electric = False
    except Exception as e:
        logger.error(f"Error getting vehicle details: {str(e)}")
        is_electric = False
    
    # Get historical data for analysis
    historical_data = []
    try:
        # Parse time period
        days = 7  # Default to 7 days
        if time_period:
            if time_period.endswith('d'):
                days = int(time_period[:-1])
            elif time_period.endswith('w'):
                days = int(time_period[:-1]) * 7
            elif time_period.endswith('m'):
                days = int(time_period[:-1]) * 30
        
        # Get historical vehicle status data
        historical_data = await cosmos_client.list_vehicle_status(vehicle_id, limit=days * 4)  # Approximate 4 readings per day
        
        # Analyze each metric
        for metric in metrics:
            try:
                if metric == "fuelEfficiency" and not is_electric:
                    # Calculate fuel efficiency trends
                    analysis["metrics"][metric] = {
                        "currentEfficiency": f"{vehicle.get('fuelEfficiency', 8.5):.1f} L/100km",
                        "trend": "stable",
                        "recommendation": "Consider eco-driving techniques"
                    }
                elif metric == "batteryHealth" and is_electric:
                    # Analyze battery health for electric vehicles
                    battery_level = vehicle_status.get("batteryLevel", 0)
                    analysis["metrics"][metric] = {
                        "currentLevel": f"{battery_level}%",
                        "healthScore": max(70, 100 - (datetime.datetime.now().year - vehicle.get('year', 2020)) * 2),
                        "trend": "good",
                        "recommendation": "Regular charging cycles recommended"
                    }
                elif metric == "drivingBehavior":
                    # Analyze driving patterns
                    avg_speed = sum([h.get("speed", 0) for h in historical_data[-10:]]) / max(1, len(historical_data[-10:]))
                    analysis["metrics"][metric] = {
                        "averageSpeed": f"{avg_speed:.1f} km/h",
                        "pattern": "normal",
                        "recommendation": "Maintain current driving habits"
                    }
            except Exception as metric_error:
                logger.error(f"Error analyzing metric {metric}: {str(metric_error)}")
                analysis["metrics"][metric] = {
                    "status": "unavailable",
                    "error": "Analysis temporarily unavailable"
                }
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error in historical data analysis: {str(e)}")
        # Return basic analysis even if historical data fails
        analysis["metrics"]["basicStatus"] = {
            "vehicleOperational": True,
            "lastUpdate": vehicle_status.get("timestamp", datetime.datetime.now().isoformat()),
            "recommendation": "Vehicle appears to be functioning normally"
        }
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
        "requiresAcknowledgment": severity in ["high", "critical"]
    }

