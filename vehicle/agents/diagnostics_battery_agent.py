"""
Diagnostics & Battery Agent for the Connected Car Platform.

This agent oversees vehicle diagnostics, battery status, and system health reports.
"""

import logging
import random
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from agents.base_agent import BaseAgent
from utils.agent_tools import analyze_vehicle_data

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DiagnosticsBatteryAgent(BaseAgent):
    """
    Diagnostics & Battery Agent for overseeing vehicle diagnostics and health.
    """
    
    def __init__(self):
        """Initialize the Diagnostics & Battery Agent."""
        super().__init__("Diagnostics & Battery Agent")
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
        if "diagnostic" in query_lower or "health" in query_lower or "check" in query_lower:
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
                data=self._get_capabilities()
            )
    
    async def _handle_diagnostics(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a diagnostics request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to run diagnostics for.", 
                success=False
            )
        
        # In a real implementation, this would query the vehicle's diagnostic systems
        # Use the analyze_vehicle_data tool with mock data
        metrics = ["battery_health", "tire_pressure", "brake_wear", "oil_level", "engine_health"]
        diagnostics_data = analyze_vehicle_data(vehicle_id, "1d", metrics)
        
        # Create a simplified summary of the diagnostic results
        issues = []
        status = "All systems normal"
        
        # Check for issues
        if "metrics" in diagnostics_data:
            if "tire_pressure" in diagnostics_data["metrics"]:
                tire_status = random.choice(["normal", "low", "normal", "normal"])
                if tire_status == "low":
                    issues.append("Low tire pressure detected")
            
            if "brake_wear" in diagnostics_data["metrics"]:
                brake_status = random.choice(["normal", "worn", "normal", "normal"])
                if brake_status == "worn":
                    issues.append("Brake pads showing signs of wear")
            
            if "oil_level" in diagnostics_data["metrics"]:
                oil_status = random.choice(["normal", "low", "normal", "normal"])
                if oil_status == "low":
                    issues.append("Oil level is low")
            
            if "engine_health" in diagnostics_data["metrics"]:
                engine_status = random.choice(["normal", "check", "normal", "normal"])
                if engine_status == "check":
                    issues.append("Engine requires inspection")
        
        if issues:
            status = "Issues detected"
        
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
                "vehicle_id": vehicle_id
            }
        )
    
    async def _handle_battery_status(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a battery status request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to check battery status for.", 
                success=False
            )
        
        # In a real implementation, this would query the vehicle's battery management system
        # Mock data for demonstration
        is_electric = random.choice([True, False])
        
        if is_electric:
            battery_data = {
                "level": random.randint(10, 100),
                "range_km": random.randint(50, 450),
                "health": random.randint(85, 100),
                "charging": random.choice([True, False]),
                "charge_rate_kw": random.choice([0, 7.2, 11, 22, 50, 150]),
                "estimated_replacement": f"{random.randint(1, 8)} years"
            }
            
            charging_status = "currently charging" if battery_data["charging"] else "not charging"
            charging_info = f" and {charging_status}" if battery_data["charge_rate_kw"] > 0 else ""
            
            return self._format_response(
                f"Battery status: {battery_data['level']}% charge level with an estimated range of {battery_data['range_km']} km. "
                f"The battery health is {battery_data['health']}%{charging_info}. "
                f"Estimated battery replacement in {battery_data['estimated_replacement']}.",
                data={
                    "battery": battery_data,
                    "vehicle_id": vehicle_id,
                    "vehicle_type": "electric"
                }
            )
        else:
            # For combustion engine cars, return 12V battery status
            battery_data = {
                "voltage": round(random.uniform(11.8, 14.2), 1),
                "health": random.randint(70, 100),
                "last_replaced": f"{random.randint(1, 48)} months ago",
                "estimated_replacement": random.choice(["Not needed", "Within 6 months", "Soon"])
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
                    "vehicle_type": "combustion"
                }
            )
    
    async def _handle_system_health(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a system health request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to check system health for.", 
                success=False
            )
        
        # In a real implementation, this would query the vehicle's system health
        # Mock data for demonstration
        systems = [
            {"name": "Engine Control Module", "status": random.choice(["Normal", "Normal", "Warning", "Normal"])},
            {"name": "Transmission Control", "status": random.choice(["Normal", "Normal", "Normal", "Warning"])},
            {"name": "Brake Control System", "status": random.choice(["Normal", "Normal", "Normal", "Normal"])},
            {"name": "Battery Management System", "status": random.choice(["Normal", "Normal", "Normal", "Warning"])},
            {"name": "Infotainment System", "status": random.choice(["Normal", "Normal", "Normal", "Error"])},
            {"name": "Climate Control System", "status": random.choice(["Normal", "Normal", "Normal", "Normal"])},
            {"name": "Driver Assistance Systems", "status": random.choice(["Normal", "Normal", "Warning", "Normal"])},
        ]
        
        # Determine overall status
        if any(system["status"] == "Error" for system in systems):
            overall_status = "Error"
        elif any(system["status"] == "Warning" for system in systems):
            overall_status = "Warning"
        else:
            overall_status = "Normal"
        
        # Build the response
        issues = [system for system in systems if system["status"] != "Normal"]
        
        if issues:
            issues_text = "\n".join([f"• {issue['name']}: {issue['status']}" for issue in issues])
            response_text = f"System health report: {overall_status}. The following systems require attention:\n\n{issues_text}"
        else:
            response_text = "System health report: All systems are functioning normally."
        
        return self._format_response(
            response_text,
            data={
                "systems": systems,
                "overall_status": overall_status,
                "vehicle_id": vehicle_id
            }
        )
    
    async def _handle_maintenance_check(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a maintenance check request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to check maintenance for.", 
                success=False
            )
        
        # In a real implementation, this would query the vehicle's maintenance schedule
        # Mock data for demonstration
        today = datetime.now()
        maintenance_items = [
            {
                "type": "Oil Change",
                "last_service": (today - timedelta(days=random.randint(30, 180))).strftime("%Y-%m-%d"),
                "next_due": (today + timedelta(days=random.randint(-30, 180))).strftime("%Y-%m-%d"),
                "status": random.choice(["OK", "Due Soon", "Overdue", "OK"])
            },
            {
                "type": "Tire Rotation",
                "last_service": (today - timedelta(days=random.randint(30, 180))).strftime("%Y-%m-%d"),
                "next_due": (today + timedelta(days=random.randint(-30, 180))).strftime("%Y-%m-%d"),
                "status": random.choice(["OK", "Due Soon", "OK", "OK"])
            },
            {
                "type": "Brake Inspection",
                "last_service": (today - timedelta(days=random.randint(90, 270))).strftime("%Y-%m-%d"),
                "next_due": (today + timedelta(days=random.randint(-30, 180))).strftime("%Y-%m-%d"),
                "status": random.choice(["OK", "Due Soon", "Overdue", "OK"])
            },
            {
                "type": "Air Filter",
                "last_service": (today - timedelta(days=random.randint(180, 365))).strftime("%Y-%m-%d"),
                "next_due": (today + timedelta(days=random.randint(-30, 180))).strftime("%Y-%m-%d"),
                "status": random.choice(["OK", "Due Soon", "OK", "OK"])
            },
            {
                "type": "Cabin Filter",
                "last_service": (today - timedelta(days=random.randint(180, 365))).strftime("%Y-%m-%d"),
                "next_due": (today + timedelta(days=random.randint(-30, 180))).strftime("%Y-%m-%d"),
                "status": random.choice(["OK", "Due Soon", "OK", "OK"])
            }
        ]
        
        # Build the response
        attention_items = [item for item in maintenance_items if item["status"] != "OK"]
        
        if attention_items:
            items_text = "\n".join([
                f"• {item['type']}: {item['status']}, next due {item['next_due']}"
                for item in attention_items
            ])
            response_text = f"Maintenance check: The following items require attention:\n\n{items_text}"
        else:
            response_text = "Maintenance check: All maintenance items are up to date."
        
        return self._format_response(
            response_text,
            data={
                "maintenance_items": maintenance_items,
                "vehicle_id": vehicle_id
            }
        )
    
    def _get_capabilities(self) -> Dict[str, str]:
        """Get the capabilities of this agent."""
        return {
            "diagnostics": "Run comprehensive diagnostics on vehicle systems",
            "battery_status": "Check battery charge level, health, and status",
            "system_health": "Get detailed reports on all vehicle systems",
            "maintenance_check": "Review maintenance schedule and upcoming service needs"
        }
