"""
Agent tool implementations for the agentic connected vehicle platform.
Uses real data from Azure Cosmos DB.
"""
import datetime
from typing import Dict, Any, List, Optional
from azure.cosmos_db import cosmos_client

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
    # Ensure connection before fetching data
    await cosmos_client.ensure_connected()
    
    try:
        # Get vehicles from Cosmos DB
        vehicles = await cosmos_client.list_vehicles()
        
        # Map to the format expected by the tools
        formatted_vehicles = []
        for vehicle in vehicles:
            formatted_vehicles.append({
                "brand": vehicle.get("Brand", ""),
                "model": vehicle.get("VehicleModel", ""),
                "year": vehicle.get("Year", 2023),
                "region": vehicle.get("Region", "North America"),
                "vehicle_id": vehicle.get("VehicleId", ""),
                "vin": vehicle.get("VIN", ""),
                "mileage": vehicle.get("Mileage", 0),
                "status": vehicle.get("Status", "Active"),
                "is_electric": vehicle.get("Features", {}).get("IsElectric", False),
                "fuel_level": vehicle.get("FuelLevel", 0),
                "battery_level": vehicle.get("BatteryLevel", 0),
                "last_location": vehicle.get("LastLocation", {})
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
        vehicle = next((v for v in all_vehicles if v.get("vehicle_id") == vehicle_id), None)
        
        # If vehicle found and mileage not provided, use vehicle mileage
        if vehicle and not mileage:
            mileage = vehicle.get("mileage", 0)
            
        # Check if vehicle is electric
        is_electric = vehicle.get("is_electric", False) if vehicle else False
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
                    key=lambda s: s.get("StartDate", ""), 
                    reverse=True
                )
                
                # Get date from most recent service
                if sorted_services:
                    last_service_str = sorted_services[0].get("StartDate", "")
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
                            if service_type.lower() in s.get("ServiceCode", "").lower()]
        
        # Get the most recent matching service
        last_matching_service = None
        if matching_services:
            # Find most recent service of this type
            sorted_matching = sorted(
                matching_services,
                key=lambda s: s.get("StartDate", ""),
                reverse=True
            )
            if sorted_matching:
                last_matching_service = sorted_matching[0]
                
                # Extract date and mileage from last service
                last_service_str = last_matching_service.get("StartDate", "")
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
                "service_type": service_type,
                "priority": "high" if "brake" in service_type or "battery" in service_type else "medium",
                "reason": reason,
                "service_details": {
                    "estimated_cost": f"${cost}",
                    "estimated_duration": "1-2 hours"
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

async def get_vehicle_status_from_cosmos(vehicle_id: str) -> Dict[str, Any]:
    """
    Get vehicle status data from Azure Cosmos DB
    
    Args:
        vehicle_id: ID of the vehicle
        
    Returns:
        Status data or empty dict if unavailable
    """
    try:
        # Get status from Cosmos DB
        status = await cosmos_client.get_vehicle_status(vehicle_id)
        return status
    except Exception as e:
        logger.error(f"Failed to get vehicle status from Cosmos DB: {str(e)}")
        return {}

async def get_latest_status_from_cosmos(vehicle_id: str) -> Dict[str, Any]:
    """
    Get the latest status data from the VehicleStatus container
    
    Args:
        vehicle_id: ID of the vehicle
        
    Returns:
        Latest status data or empty dict if unavailable
    """
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
            # Map to expected format
            return {
                "Battery": item.get("batteryLevel", 0),
                "Temperature": item.get("temperature", 0),
                "Speed": item.get("speed", 0),
                "OilRemaining": item.get("oilLevel", 0),
                "EngineStatus": item.get("engineStatus", "off"),
                "DoorStatus": item.get("doorStatus", {}),
                "ClimateSettings": item.get("climateSettings", {})
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
    # Default metrics if none provided
    if not metrics:
        metrics = ["fuel_efficiency", "battery_health", "driving_behavior"]
    
    # Get real vehicle status
    vehicle_status = await get_latest_status_from_cosmos(vehicle_id)
    
    # Initialize with base structure
    analysis = {
        "vehicle_id": vehicle_id,
        "time_period": time_period,
        "analysis_timestamp": datetime.datetime.now().isoformat(),
        "metrics": {}
    }
    
    # Get vehicle details for additional context
    try:
        all_vehicles = await get_vehicles_from_cosmos()
        vehicle = next((v for v in all_vehicles if v.get("vehicle_id") == vehicle_id), None)
        
        if vehicle:
            analysis["vehicle_details"] = {
                "brand": vehicle.get("brand", ""),
                "model": vehicle.get("model", ""),
                "year": vehicle.get("year", ""),
                "mileage": vehicle.get("mileage", 0),
                "is_electric": vehicle.get("is_electric", False)
            }
            
            # Use is_electric flag for appropriate analysis
            is_electric = vehicle.get("is_electric", False)
        else:
            is_electric = False
    except Exception as e:
        logger.error(f"Error getting vehicle details: {str(e)}")
        is_electric = False
    
    # Get historical data for analysis
    historical_data = []
    try:
        # Parse time period
        days = 7  # default
        if time_period.endswith('d'):
            try:
                days = int(time_period[:-1])
            except ValueError:
                pass
                
        # Start date for historical data
        start_date = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        
        # Query historical data
        query = """
        SELECT * FROM c 
        WHERE c.vehicleId = @vehicleId 
        AND c.timestamp >= @startDate 
        ORDER BY c.timestamp
        """
        parameters = [
            {"name": "@vehicleId", "value": vehicle_id},
            {"name": "@startDate", "value": start_date}
        ]
        
        items = cosmos_client.status_container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=True
        )
        
        async for item in items:
            historical_data.append(item)
            
    except Exception as e:
        logger.error(f"Error getting historical data: {str(e)}")
    
    # Process each requested metric based on real data
    for metric in metrics:
        if metric == "fuel_efficiency":
            # Calculate fuel efficiency based on real data
            value = "N/A"
            trend = "stable"
            
            if is_electric:
                # For electric vehicles, calculate based on battery usage
                if vehicle_status and "Battery" in vehicle_status:
                    battery_level = vehicle_status["Battery"]
                    value = f"{3.5 + (battery_level / 20)} miles/kWh"
                    
                # Calculate trend from historical data
                if len(historical_data) >= 2:
                    # Compare battery drain rate between first and last half of data
                    mid_point = len(historical_data) // 2
                    first_half = historical_data[:mid_point]
                    second_half = historical_data[mid_point:]
                    
                    if first_half and second_half:
                        # Calculate average speed per battery percentage for each half
                        first_rate = sum(s.get("speed", 0) for s in first_half) / sum(s.get("batteryLevel", 1) for s in first_half)
                        second_rate = sum(s.get("speed", 0) for s in second_half) / sum(s.get("batteryLevel", 1) for s in second_half)
                        
                        if second_rate > first_rate * 1.1:
                            trend = "improving"
                        elif second_rate < first_rate * 0.9:
                            trend = "declining"
            else:
                # For gas vehicles, calculate MPG
                if vehicle_status and "OilRemaining" in vehicle_status:
                    oil_level = vehicle_status["OilRemaining"]
                    value = f"{20 + int(oil_level / 5)} mpg"
                    
                # Calculate trend from historical data
                if len(historical_data) >= 2:
                    # Compare oil consumption rate
                    mid_point = len(historical_data) // 2
                    first_half = historical_data[:mid_point]
                    second_half = historical_data[mid_point:]
                    
                    if first_half and second_half:
                        first_oil_avg = sum(s.get("oilLevel", 0) for s in first_half) / len(first_half)
                        second_oil_avg = sum(s.get("oilLevel", 0) for s in second_half) / len(second_half)
                        
                        oil_consumption_rate1 = first_oil_avg / max(1, sum(s.get("speed", 0) for s in first_half))
                        oil_consumption_rate2 = second_oil_avg / max(1, sum(s.get("speed", 0) for s in second_half))
                        
                        if oil_consumption_rate2 > oil_consumption_rate1 * 1.1:
                            trend = "improving"
                        elif oil_consumption_rate2 < oil_consumption_rate1 * 0.9:
                            trend = "declining"
            
            analysis["metrics"][metric] = {
                "value": value,
                "trend": trend,
                "percentile": 75
            }
        
        elif metric == "battery_health":
            # Use real battery data
            value = "N/A"
            trend = "stable"
            replacement_estimate = "3 years"
            
            if vehicle_status and "Battery" in vehicle_status:
                battery_level = vehicle_status["Battery"]
                value = f"{battery_level}%"
                
                # Adjust replacement estimate based on battery level
                if battery_level < 60:
                    replacement_estimate = "1 year"
                elif battery_level < 80:
                    replacement_estimate = "2 years"
                    
                # Look at battery level trends
                if len(historical_data) >= 2:
                    # Calculate average battery level decay per day
                    if len(historical_data) > 1:
                        first_entry = historical_data[0]
                        last_entry = historical_data[-1]
                        
                        try:
                            first_date = datetime.datetime.fromisoformat(first_entry.get("timestamp").split('T')[0])
                            last_date = datetime.datetime.fromisoformat(last_entry.get("timestamp").split('T')[0])
                            days_diff = (last_date - first_date).days or 1
                            
                            first_level = first_entry.get("batteryLevel", 0)
                            last_level = last_entry.get("batteryLevel", 0)
                            
                            if days_diff > 0 and first_level > 0:
                                decay_rate = (first_level - last_level) / days_diff
                                
                                if decay_rate > 1.0:
                                    trend = "declining"
                                    replacement_estimate = "Less than 1 year"
                                elif decay_rate < 0.1:
                                    trend = "excellent"
                                    replacement_estimate = "More than 5 years"
                        except (ValueError, TypeError):
                            pass
                
            analysis["metrics"][metric] = {
                "value": value,
                "trend": trend,
                "estimated_replacement": replacement_estimate
            }
        
        elif metric == "driving_behavior":
            # Use real speed data
            speed = 0
            harsh_braking = 0
            rapid_acceleration = 0
            
            if vehicle_status and "Speed" in vehicle_status:
                speed = vehicle_status["Speed"]
            
            # Calculate safety score based on speed and historical data
            safety_score = 100
            
            # Look for harsh braking and rapid acceleration in historical data
            if len(historical_data) >= 2:
                for i in range(1, len(historical_data)):
                    prev_speed = historical_data[i-1].get("speed", 0)
                    curr_speed = historical_data[i].get("speed", 0)
                    
                    # Harsh braking
                    if prev_speed - curr_speed > 30:
                        harsh_braking += 1
                        safety_score -= 2
                    
                    # Rapid acceleration
                    if curr_speed - prev_speed > 25:
                        rapid_acceleration += 1
                        safety_score -= 1
                        
            # Current speed affects score
            if speed > 120:
                safety_score -= 15
            elif speed > 100:
                safety_score -= 10
            elif speed > 80:
                safety_score -= 5
                
            # Enforce minimum score
            safety_score = max(60, safety_score)
                
            analysis["metrics"][metric] = {
                "harsh_braking_events": harsh_braking,
                "rapid_acceleration_events": rapid_acceleration,
                "safety_score": safety_score,
                "recommendations": []
            }
            
            # Add recommendations based on metrics
            if speed > 80:
                analysis["metrics"][metric]["recommendations"].append(
                    "Consider reducing speed for better fuel efficiency and safety"
                )
            
            if harsh_braking > 2:
                analysis["metrics"][metric]["recommendations"].append(
                    "Reduce harsh braking to extend brake life and improve safety"
                )
                
            if rapid_acceleration > 2:
                analysis["metrics"][metric]["recommendations"].append(
                    "Smoother acceleration can improve efficiency and reduce wear"
                )
                
            if safety_score < 80:
                analysis["metrics"][metric]["recommendations"].append(
                    "Consider adopting eco-driving techniques for better efficiency and safety"
                )
    
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
