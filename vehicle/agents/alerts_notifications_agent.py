"""
Alerts & Notifications Agent for the Connected Car Platform.

This agent sends critical alerts such as speed violations, curfew breaches,
and battery warnings.
"""

import logging
import random
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from agents.base_agent import BaseAgent
from utils.agent_tools import format_notification

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertsNotificationsAgent(BaseAgent):
    """
    Alerts & Notifications Agent for managing vehicle alerts and notifications.
    """
    
    def __init__(self):
        """Initialize the Alerts & Notifications Agent."""
        super().__init__("Alerts & Notifications Agent")
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process an alerts or notifications related query.
        
        Args:
            query: User query about alerts or notifications
            context: Additional context for the query
            
        Returns:
            Response with alerts or notifications information or actions
        """
        # Extract vehicle ID from context if available
        vehicle_id = context.get("vehicle_id") if context else None
        
        # Simple keyword-based logic for demonstration
        query_lower = query.lower()
        
        # Handle alert status requests
        if "alert" in query_lower and "status" in query_lower:
            return await self._handle_alert_status(vehicle_id, context)
        
        # Handle speed alert requests
        elif "speed" in query_lower and "alert" in query_lower:
            return await self._handle_speed_alert(vehicle_id, query, context)
        
        # Handle curfew alert requests
        elif "curfew" in query_lower:
            return await self._handle_curfew_alert(vehicle_id, query, context)
            
        # Handle battery alert requests
        elif "battery" in query_lower and "alert" in query_lower:
            return await self._handle_battery_alert(vehicle_id, query, context)
            
        # Handle notification settings requests
        elif "notification" in query_lower and "setting" in query_lower:
            return await self._handle_notification_settings(vehicle_id, context)
            
        # Handle general information requests
        else:
            return self._format_response(
                "I can help you manage vehicle alerts and notifications, including speed alerts, "
                "curfew notifications, battery warnings, and notification settings. "
                "What would you like to know or adjust?",
                data=self._get_capabilities()
            )
    
    async def _handle_alert_status(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle an alert status request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to check alert status for.", 
                success=False
            )
        
        # In a real implementation, this would query the vehicle's alert database
        # Mock data for demonstration
        alerts = [
            {
                "id": f"alert-{random.randint(1000, 9999)}",
                "type": "battery_low",
                "severity": "medium",
                "timestamp": (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
                "message": "Battery level below 20%",
                "acknowledged": random.choice([True, False])
            } if random.random() > 0.7 else None,
            {
                "id": f"alert-{random.randint(1000, 9999)}",
                "type": "speed_violation",
                "severity": "high",
                "timestamp": (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
                "message": f"Speed limit exceeded by {random.randint(10, 30)} km/h",
                "acknowledged": random.choice([True, False])
            } if random.random() > 0.7 else None,
            {
                "id": f"alert-{random.randint(1000, 9999)}",
                "type": "curfew_breach",
                "severity": "medium",
                "timestamp": (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
                "message": "Vehicle used outside allowed hours",
                "acknowledged": random.choice([True, False])
            } if random.random() > 0.7 else None,
            {
                "id": f"alert-{random.randint(1000, 9999)}",
                "type": "maintenance_due",
                "severity": "low",
                "timestamp": (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat(),
                "message": "Maintenance service due soon",
                "acknowledged": random.choice([True, False])
            } if random.random() > 0.7 else None
        ]
        
        # Clean up None values
        alerts = [alert for alert in alerts if alert]
        
        if not alerts:
            return self._format_response(
                "There are no active alerts for your vehicle at this time.",
                data={
                    "alerts": [],
                    "vehicle_id": vehicle_id
                }
            )
        
        # Format the response
        unacknowledged = [alert for alert in alerts if not alert["acknowledged"]]
        
        alerts_text = "\n".join([
            f"• {alert['type'].replace('_', ' ').title()}: {alert['message']} "
            f"({alert['severity']} severity, {'unacknowledged' if not alert['acknowledged'] else 'acknowledged'})"
            for alert in alerts
        ])
        
        return self._format_response(
            f"Alert status: {len(alerts)} alerts, {len(unacknowledged)} unacknowledged.\n\n{alerts_text}",
            data={
                "alerts": alerts,
                "unacknowledged_count": len(unacknowledged),
                "vehicle_id": vehicle_id
            }
        )
    
    async def _handle_speed_alert(self, vehicle_id: Optional[str], query: str, 
                                 context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a speed alert request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to set a speed alert for.", 
                success=False
            )
        
        # Try to extract speed limit from query
        speed_limit = None
        for word in query.split():
            try:
                limit = float(word)
                if 20 <= limit <= 200:  # Reasonable speed range in km/h
                    speed_limit = limit
                    break
            except ValueError:
                continue
        
        # Use context speed limit if available and not in query
        if not speed_limit and context and "speed_limit" in context:
            speed_limit = context["speed_limit"]
        
        # Default speed limit if not specified
        if not speed_limit:
            speed_limit = 120.0  # Default highway speed
        
        # In a real implementation, this would set a speed alert in the vehicle
        notification = format_notification(
            notification_type="system_alert",
            message=f"Speed alert set for {speed_limit} km/h",
            severity="medium"
        )
        
        return self._format_response(
            f"I've set a speed alert for {speed_limit} km/h. "
            "You'll receive a notification if the vehicle exceeds this speed.",
            data={
                "action": "set_speed_alert",
                "vehicle_id": vehicle_id,
                "speed_limit": speed_limit,
                "notification": notification
            }
        )
    
    async def _handle_curfew_alert(self, vehicle_id: Optional[str], query: str,
                                  context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a curfew alert request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to set a curfew alert for.", 
                success=False
            )
        
        # Try to extract curfew times from query or context
        start_time = context.get("curfew_start") if context else None
        end_time = context.get("curfew_end") if context else None
        
        # Default curfew times if not specified
        if not start_time:
            start_time = "22:00"
        if not end_time:
            end_time = "06:00"
        
        # In a real implementation, this would set a curfew alert in the vehicle
        notification = format_notification(
            notification_type="system_alert",
            message=f"Curfew alert set from {start_time} to {end_time}",
            severity="medium"
        )
        
        return self._format_response(
            f"I've set a curfew alert from {start_time} to {end_time}. "
            "You'll receive a notification if the vehicle is used during these hours.",
            data={
                "action": "set_curfew_alert",
                "vehicle_id": vehicle_id,
                "start_time": start_time,
                "end_time": end_time,
                "notification": notification
            }
        )
    
    async def _handle_battery_alert(self, vehicle_id: Optional[str], query: str,
                                   context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a battery alert request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to set a battery alert for.", 
                success=False
            )
        
        # Try to extract battery threshold from query
        threshold = None
        for word in query.split():
            try:
                value = float(word)
                if 5 <= value <= 50:  # Reasonable battery threshold range in %
                    threshold = value
                    break
            except ValueError:
                continue
        
        # Use context threshold if available and not in query
        if not threshold and context and "battery_threshold" in context:
            threshold = context["battery_threshold"]
        
        # Default threshold if not specified
        if not threshold:
            threshold = 20.0  # Default 20% battery threshold
        
        # In a real implementation, this would set a battery alert in the vehicle
        notification = format_notification(
            notification_type="system_alert",
            message=f"Battery alert set for {threshold}%",
            severity="medium"
        )
        
        return self._format_response(
            f"I've set a battery alert for {threshold}%. "
            "You'll receive a notification if the battery level falls below this threshold.",
            data={
                "action": "set_battery_alert",
                "vehicle_id": vehicle_id,
                "threshold": threshold,
                "notification": notification
            }
        )
    
    async def _handle_notification_settings(self, vehicle_id: Optional[str], 
                                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a notification settings request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to check notification settings for.", 
                success=False
            )
        
        # In a real implementation, this would query the vehicle's notification settings
        # Mock data for demonstration
        settings = {
            "speed_alerts": random.choice([True, False]),
            "curfew_alerts": random.choice([True, False]),
            "battery_alerts": random.choice([True, False]),
            "maintenance_alerts": random.choice([True, False]),
            "geofence_alerts": random.choice([True, False]),
            "notification_channels": {
                "email": random.choice([True, False]),
                "push": random.choice([True, False]),
                "sms": random.choice([True, False])
            }
        }
        
        # Format the response
        enabled = [k.replace("_", " ").title() for k, v in settings.items() if v and k != "notification_channels"]
        channels = [k for k, v in settings["notification_channels"].items() if v]
        
        settings_text = f"Enabled alerts: {', '.join(enabled)}\nNotification channels: {', '.join(channels)}"
        
        return self._format_response(
            f"Notification settings for your vehicle:\n\n{settings_text}",
            data={
                "settings": settings,
                "vehicle_id": vehicle_id
            }
        )
    
    def _get_capabilities(self) -> Dict[str, str]:
        """Get the capabilities of this agent."""
        return {
            "alert_status": "Check the status of all vehicle alerts",
            "speed_alert": "Set alerts for exceeding speed limits",
            "curfew_alert": "Set alerts for vehicle use outside allowed hours",
            "battery_alert": "Set alerts for low battery levels",
            "notification_settings": "View and adjust notification preferences"
        }
