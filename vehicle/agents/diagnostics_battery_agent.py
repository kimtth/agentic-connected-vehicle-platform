"""
Diagnostics & Battery Agent for the Connected Car Platform.

This agent oversees vehicle diagnostics, battery status, and system health reports.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from azure.cosmos_db import cosmos_client
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from plugin.oai_service import create_chat_service
from utils.logging_config import get_logger

logger = get_logger(__name__)


class DiagnosticsBatteryAgent:
    """
    Diagnostics & Battery Agent for overseeing vehicle diagnostics and health.
    """

    def __init__(self):
        """Initialize the Diagnostics & Battery Agent."""
        service_factory = create_chat_service()
        self.agent = ChatCompletionAgent(
            service=service_factory,
            name="DiagnosticsBatteryAgent",
            instructions="You specialize in diagnostics and battery monitoring.",
            plugins=[DiagnosticsBatteryPlugin()],
        )


class DiagnosticsBatteryPlugin:
    @kernel_function(description="Run diagnostics on vehicle systems")
    async def _handle_diagnostics(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle a diagnostics request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to run diagnostics for.",
                success=False,
            )

        try:
            # Get vehicle data from Cosmos DB
            await cosmos_client.ensure_connected()

            # Get vehicle status from Cosmos DB
            vehicle_status = await cosmos_client.get_vehicle_status(vehicle_id)
            if not vehicle_status:
                return self._format_response(
                    "No recent vehicle status data is available for diagnostics.",
                    success=False,
                )

            # Get vehicle details to check specs
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next(
                (v for v in vehicles if v.get("VehicleId") == vehicle_id), None
            )
            if not vehicle:
                return self._format_response(
                    "Vehicle details are not available for diagnostics.", success=False
                )

            # Placeholder for diagnostics data analysis
            diagnostics_data = {}

            # Create a summary of the diagnostic results based on actual data
            issues = []

            # Check battery level
            battery_level = vehicle_status.get(
                "batteryLevel", vehicle_status.get("Battery", 0)
            )
            if battery_level < 20:
                issues.append("Low battery level detected")

            # Check temperature
            temperature = vehicle_status.get(
                "temperature", vehicle_status.get("Temperature", 0)
            )
            if temperature > 90:
                issues.append("High engine/system temperature detected")

            # Check tire pressure from telemetry if available
            telemetry = vehicle.get("CurrentTelemetry", {})
            tire_pressure = telemetry.get("TirePressure", {})

            for tire_position, pressure in tire_pressure.items():
                if pressure < 30:
                    issues.append(
                        f"Low tire pressure detected ({tire_position}: {pressure} PSI)"
                    )

            # Check if the vehicle is electric
            is_electric = vehicle.get("Features", {}).get("IsElectric", False)

            # For non-electric vehicles, check oil level
            if not is_electric:
                oil_level = vehicle_status.get(
                    "oilLevel", vehicle_status.get("OilLevel", 0)
                )
                if oil_level < 25:
                    issues.append("Low oil level detected")

            # Get service history to check maintenance status
            services = await cosmos_client.list_services(vehicle_id)
            if services:
                # Find most recent service
                sorted_services = sorted(
                    services, key=lambda s: s.get("StartDate", ""), reverse=True
                )
                if sorted_services:
                    last_service = sorted_services[0]
                    last_service_date = last_service.get("StartDate", "")

                    try:
                        service_date = datetime.fromisoformat(
                            last_service_date.replace("Z", "+00:00")
                        )
                        months_since = (datetime.now() - service_date).days // 30

                        if months_since > 6:
                            issues.append(
                                f"Regular maintenance due (last service: {months_since} months ago)"
                            )
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not parse service date: {e}")

            # Determine overall status
            status = "Issues detected" if issues else "All systems normal"

            # Format the response
            if issues:
                issues_text = "\n".join([f"• {issue}" for issue in issues])
                response_text = f"Diagnostic check complete. Issues detected:\n\n{issues_text}\n\nI recommend scheduling a service appointment."
            else:
                response_text = "Diagnostic check complete. All vehicle systems are operating normally."

            return self._format_response(
                response_text,
                data={
                    "diagnostics": diagnostics_data,
                    "issues": issues,
                    "status": status,
                    "vehicle_id": vehicle_id,
                },
            )
        except Exception as e:
            logger.error(f"Error running diagnostics: {str(e)}")
            return self._format_response(
                "I encountered an error while running diagnostics. Please try again later.",
                success=False,
            )

    @kernel_function(description="Check battery status and health")
    async def _handle_battery_status(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle a battery status request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to check battery status for.",
                success=False,
            )

        try:
            # Get vehicle data from Cosmos DB
            await cosmos_client.ensure_connected()

            # Get vehicle status
            vehicle_status = await cosmos_client.get_vehicle_status(vehicle_id)
            if not vehicle_status:
                return self._format_response(
                    "No recent battery status data is available.", success=False
                )

            # Get vehicle details
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next(
                (v for v in vehicles if v.get("VehicleId") == vehicle_id), None
            )
            if not vehicle:
                return self._format_response(
                    "Vehicle details are not available for battery status.",
                    success=False,
                )

            # Check if the vehicle is electric
            is_electric = vehicle.get("Features", {}).get("IsElectric", False)

            if is_electric:
                # For electric vehicles, get battery data
                battery_level = vehicle_status.get(
                    "batteryLevel",
                    vehicle_status.get("Battery", vehicle.get("BatteryLevel", 0)),
                )

                # Calculate range based on battery level and vehicle type
                # This is a simplified model; a real system would have more precise data
                base_range = 400  # Default range for a full battery in km

                # Adjust for vehicle make/model
                make = vehicle.get("Brand", "")
                model = vehicle.get("VehicleModel", "")

                if make == "Tesla":
                    base_range = 500
                elif "e-tron" in model or "EQS" in model:
                    base_range = 450
                elif "iX" in model or "Taycan" in model:
                    base_range = 420

                # Calculate estimated range
                range_km = int(base_range * (battery_level / 100))

                # Check charging status - in a real system, this would be explicitly tracked
                charging = False
                charge_rate = 0

                # Looking at status history can help determine if charging is happening
                status_history = await cosmos_client.list_vehicle_status(
                    vehicle_id, limit=5
                )
                if len(status_history) > 1:
                    # If the battery level has increased over time, the vehicle might be charging
                    sorted_history = sorted(
                        status_history,
                        key=lambda x: x.get("timestamp", ""),
                        reverse=True,
                    )
                    latest = sorted_history[0]
                    previous = sorted_history[-1]

                    latest_level = latest.get("batteryLevel", latest.get("Battery", 0))
                    previous_level = previous.get(
                        "batteryLevel", previous.get("Battery", 0)
                    )

                    if latest_level > previous_level:
                        charging = True
                        # Rough estimate of charge rate
                        charge_rate = 11  # Standard charge rate in kW

                # Build the response data
                battery_data = {
                    "level": battery_level,
                    "range_km": range_km,
                    "health": 100
                    - max(
                        0,
                        min(
                            15,
                            (
                                vehicle.get("Year", datetime.now().year)
                                - datetime.now().year
                                + 10
                            )
                            * 1.5,
                        ),
                    ),
                    "charging": charging,
                    "charge_rate_kw": charge_rate if charging else 0,
                    "estimated_replacement": f"{max(1, 8 - (datetime.now().year - vehicle.get('Year', datetime.now().year)))} years",
                }

                charging_status = (
                    "currently charging" if battery_data["charging"] else "not charging"
                )
                charging_info = (
                    f" and {charging_status}"
                    if battery_data["charge_rate_kw"] > 0
                    else ""
                )

                return self._format_response(
                    f"Battery status: {battery_data['level']}% charge level with an estimated range of {battery_data['range_km']} km. "
                    f"The battery health is {battery_data['health']}%{charging_info}. "
                    f"Estimated battery replacement in {battery_data['estimated_replacement']}.",
                    data={
                        "battery": battery_data,
                        "vehicle_id": vehicle_id,
                        "vehicle_type": "electric",
                    },
                )
            else:
                # For combustion engine vehicles, get 12V battery status
                # This is often not explicitly tracked, so we'll estimate based on vehicle age
                vehicle_age = datetime.now().year - vehicle.get(
                    "Year", datetime.now().year
                )

                # Battery voltage typically declines with age
                voltage = max(11.8, min(14.2, 13.0 - (vehicle_age * 0.1)))

                # Health declines with age
                health = max(70, 100 - (vehicle_age * 5))

                # Estimate replacement timeline based on health
                replacement = "Not needed"
                if health < 75:
                    replacement = "Within 6 months"
                if health < 70:
                    replacement = "Soon"

                battery_data = {
                    "voltage": round(voltage, 1),
                    "health": health,
                    "last_replaced": f"{max(1, min(48, vehicle_age * 12))} months ago",
                    "estimated_replacement": replacement,
                }

                voltage_status = "normal"
                if battery_data["voltage"] < 12.2:
                    voltage_status = "low"
                elif battery_data["voltage"] > 14.0:
                    voltage_status = "high"

                return self._format_response(
                    f"12V battery status: Voltage is {battery_data['voltage']}V ({voltage_status}), health is {battery_data['health']}%. "
                    f"Battery was last replaced {battery_data['last_replaced']}. "
                    f"Recommendation: {battery_data['estimated_replacement']}.",
                    data={
                        "battery": battery_data,
                        "vehicle_id": vehicle_id,
                        "vehicle_type": "combustion",
                    },
                )

        except Exception as e:
            logger.error(f"Error checking battery status: {str(e)}")
            return self._format_response(
                "I encountered an error while checking battery status. Please try again later.",
                success=False,
            )

    @kernel_function(description="Check system health and status")
    async def _handle_system_health(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle a system health request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to check system health for.",
                success=False,
            )

        try:
            # Get vehicle data from Cosmos DB
            await cosmos_client.ensure_connected()

            # Get vehicle status
            vehicle_status = await cosmos_client.get_vehicle_status(vehicle_id)
            if not vehicle_status:
                return self._format_response(
                    "No recent vehicle status data is available for system health check.",
                    success=False,
                )

            # Get vehicle details
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next(
                (v for v in vehicles if v.get("VehicleId") == vehicle_id), None
            )
            if not vehicle:
                return self._format_response(
                    "Vehicle details are not available for system health check.",
                    success=False,
                )

            # Get command history to check for any failed commands
            commands = await cosmos_client.list_commands(vehicle_id)
            recent_commands = sorted(
                commands, key=lambda c: c.get("timestamp", ""), reverse=True
            )[:10]
            failed_commands = [
                cmd for cmd in recent_commands if cmd.get("status", "") == "Failed"
            ]

            # System components to check
            system_health = {
                "overall_status": "Good",
                "components": {
                    "engine": "Normal",
                    "transmission": "Normal",
                    "brakes": "Normal",
                    "battery": "Good",
                    "electrical": "Normal",
                    "connectivity": "Connected",
                },
                "issues": [],
                "recommendations": [],
            }

            # Check for issues based on vehicle status
            temperature = vehicle_status.get(
                "temperature", vehicle_status.get("Temperature", 0)
            )
            if temperature > 90:
                system_health["components"]["engine"] = "Warning"
                system_health["issues"].append("High engine temperature detected")
                system_health["recommendations"].append("Check cooling system")

            battery_level = vehicle_status.get(
                "batteryLevel", vehicle_status.get("Battery", 0)
            )
            if battery_level < 20:
                system_health["components"]["battery"] = "Low"
                system_health["issues"].append("Low battery level")
                system_health["recommendations"].append("Charge battery soon")

            # Check for failed commands
            if failed_commands:
                system_health["components"]["connectivity"] = "Warning"
                system_health["issues"].append(
                    f"{len(failed_commands)} recent command failures"
                )
                system_health["recommendations"].append("Check vehicle connectivity")

            # Determine overall status
            warning_components = [
                k for k, v in system_health["components"].items()
                if v in ["Warning", "Low"]
            ]
            if warning_components:
                system_health["overall_status"] = (
                    "Warning" if len(warning_components) <= 2 else "Critical"
                )

            # Format response
            if system_health["issues"]:
                issues_text = "\n".join([f"• {issue}" for issue in system_health["issues"]])
                recommendations_text = "\n".join(
                    [f"• {rec}" for rec in system_health["recommendations"]]
                )
                response_text = f"System health check complete. Status: {system_health['overall_status']}\n\nIssues found:\n{issues_text}\n\nRecommendations:\n{recommendations_text}"
            else:
                response_text = "System health check complete. All vehicle systems are operating normally."

            return self._format_response(
                response_text,
                data={
                    "system_health": system_health,
                    "vehicle_id": vehicle_id,
                    "failed_commands": len(failed_commands),
                },
            )

        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return self._format_response(
                "I encountered an error while checking system health. Please try again later.",
                success=False,
            )

    @kernel_function(description="Check vehicle maintenance schedule")
    async def _handle_maintenance_check(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle a maintenance check request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to check maintenance for.",
                success=False,
            )

        try:
            # Get vehicle data from Cosmos DB
            await cosmos_client.ensure_connected()

            # Get vehicle details
            vehicles = await cosmos_client.list_vehicles()
            vehicle = next(
                (v for v in vehicles if v.get("VehicleId") == vehicle_id), None
            )
            if not vehicle:
                return self._format_response(
                    "Vehicle details are not available for maintenance check.",
                    success=False,
                )

            # Get service history
            services = await cosmos_client.list_services(vehicle_id)

            # Check vehicle properties
            is_electric = vehicle.get("Features", {}).get("IsElectric", False)
            mileage = vehicle.get("Mileage", 0)

            today = datetime.now()

            # Define maintenance items
            maintenance_items = []

            # Add relevant maintenance items based on vehicle type
            if not is_electric:
                maintenance_items.append(
                    {"type": "Oil Change", "interval_miles": 5000, "interval_months": 6}
                )

            # Common maintenance items for all vehicles
            maintenance_items.extend(
                [
                    {
                        "type": "Tire Rotation",
                        "interval_miles": 6000,
                        "interval_months": 6,
                    },
                    {
                        "type": "Brake Inspection",
                        "interval_miles": 12000,
                        "interval_months": 12,
                    },
                    {
                        "type": "Air Filter",
                        "interval_miles": 15000,
                        "interval_months": 12,
                    },
                    {
                        "type": "Cabin Filter",
                        "interval_miles": 15000,
                        "interval_months": 12,
                    },
                ]
            )

            # Add electric vehicle specific maintenance
            if is_electric:
                maintenance_items.append(
                    {
                        "type": "Battery Health Check",
                        "interval_miles": 10000,
                        "interval_months": 12,
                    }
                )

            # Process each maintenance item
            for item in maintenance_items:
                # Find relevant past services
                matching_services = [
                    s
                    for s in services
                    if s.get("ServiceCode", "").lower().replace("_", " ")
                    == item["type"].lower()
                ]

                # Set default values
                item["last_service"] = "Never"
                item["next_due"] = "Soon"
                item["status"] = "Overdue"

                if matching_services:
                    # Sort by date
                    sorted_services = sorted(
                        matching_services,
                        key=lambda s: s.get("StartDate", ""),
                        reverse=True,
                    )

                    # Get last service details
                    last_service = sorted_services[0]
                    try:
                        service_date = datetime.fromisoformat(
                            last_service.get("StartDate", "").replace("Z", "+00:00")
                        )
                        service_mileage = last_service.get("mileage", 0)

                        # Record last service date
                        item["last_service"] = service_date.strftime("%Y-%m-%d")

                        # Calculate when next service is due
                        next_date = service_date + timedelta(
                            days=30 * item["interval_months"]
                        )
                        next_mileage = service_mileage + item["interval_miles"]

                        # Determine status
                        months_since = (today - service_date).days // 30
                        miles_since = (
                            mileage - service_mileage
                            if mileage > service_mileage
                            else 0
                        )

                        if (
                            months_since >= item["interval_months"]
                            or miles_since >= item["interval_miles"]
                        ):
                            item["status"] = "Overdue"
                            item["next_due"] = "Immediately"
                        elif (
                            months_since >= item["interval_months"] * 0.8
                            or miles_since >= item["interval_miles"] * 0.8
                        ):
                            item["status"] = "Due Soon"
                            item["next_due"] = next_date.strftime("%Y-%m-%d")
                        else:
                            item["status"] = "OK"
                            item["next_due"] = next_date.strftime("%Y-%m-%d")

                    except (ValueError, TypeError) as e:
                        logger.warning(f"Could not parse service date: {e}")

            # Build the response
            attention_items = [
                item for item in maintenance_items if item["status"] != "OK"
            ]

            if attention_items:
                items_text = "\n".join(
                    [
                        f"• {item['type']}: {item['status']}, next due {item['next_due']}"
                        for item in attention_items
                    ]
                )
                response_text = f"Maintenance check: The following items require attention:\n\n{items_text}"
            else:
                response_text = (
                    "Maintenance check: All maintenance items are up to date."
                )

            return self._format_response(
                response_text,
                data={"maintenance_items": maintenance_items, "vehicle_id": vehicle_id},
            )
        except Exception as e:
            logger.error(f"Error checking maintenance: {str(e)}")
            return self._format_response(
                "I encountered an error while checking maintenance status. Please try again later.",
                success=False,
            )

    async def process(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a diagnostics or battery related query.

        Args:
            query: User query about diagnostics or battery
            context: Additional context for the query

        Returns:
            Response with diagnostics or battery information
        """
        # Extract vehicle ID from context if available
        vehicle_id = context.get("vehicle_id") if context else None

        # Simple keyword-based logic for demonstration
        query_lower = query.lower()

        # Handle diagnostics requests
        if (
            "diagnostic" in query_lower
            or "health" in query_lower
            or "check" in query_lower
        ):
            return await self._handle_diagnostics(vehicle_id, context)

        # Handle battery status requests
        elif "battery" in query_lower or "charge" in query_lower:
            return await self._handle_battery_status(vehicle_id, context)

        # Handle system health requests
        elif "system" in query_lower:
            return await self._handle_system_health(vehicle_id, context)

        # Handle maintenance check requests
        elif "maintenance" in query_lower or "service" in query_lower:
            return await self._handle_maintenance_check(vehicle_id, context)

        # Handle general information requests
        else:
            return self._format_response(
                "I can help you with vehicle diagnostics, battery status, system health reports, "
                "and maintenance checks. What information would you like to know?",
                data=self._get_capabilities(),
            )

    def _get_capabilities(self) -> Dict[str, str]:
        """Get the capabilities of this agent."""
        return {
            "diagnostics": "Run comprehensive diagnostics on vehicle systems",
            "battery_status": "Check battery charge level, health, and status",
            "system_health": "Get detailed reports on all vehicle systems",
            "maintenance_check": "Review maintenance schedule and upcoming service needs",
        }

    def _format_response(
        self, message: str, data: Optional[Dict[str, Any]] = None, success: bool = True
    ) -> Dict[str, Any]:
        """Format the response message."""
        return {
            "message": message,
            "data": data or {},
            "success": success,
        }

