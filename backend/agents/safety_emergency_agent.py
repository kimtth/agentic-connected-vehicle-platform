"""
Safety & Emergency Agent for the Connected Car Platform.

This agent handles emergency-related features including collision alerts,
eCalls, and theft notifications.
"""

import logging
from typing import Dict, Any, Optional

from agents.base_agent import BaseAgent
from utils.agent_tools import format_notification

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SafetyEmergencyAgent(BaseAgent):
    """
    Safety & Emergency Agent for handling emergency-related features.
    """
    
    def __init__(self):
        """Initialize the Safety & Emergency Agent."""
        super().__init__("Safety & Emergency Agent")
    
    async def process(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a safety or emergency related query.
        
        Args:
            query: User query about safety or emergency features
            context: Additional context for the query
            
        Returns:
            Response with safety or emergency information or actions
        """
        # Extract vehicle ID from context if available
        vehicle_id = context.get("vehicle_id") if context else None
        
        # Simple keyword-based logic for demonstration
        query_lower = query.lower()
        
        # Handle emergency call requests
        if "ecall" in query_lower or "emergency call" in query_lower:
            return await self._handle_emergency_call(vehicle_id, context)
        
        # Handle collision alert requests
        elif "collision" in query_lower or "crash" in query_lower or "accident" in query_lower:
            return await self._handle_collision_alert(vehicle_id, context)
        
        # Handle theft notification requests
        elif "theft" in query_lower or "stolen" in query_lower:
            return await self._handle_theft_notification(vehicle_id, context)
            
        # Handle SOS requests
        elif "sos" in query_lower or "help" in query_lower:
            return await self._handle_sos(vehicle_id, context)
            
        # Handle general information requests
        else:
            return self._format_response(
                "I can help you with safety and emergency features, including emergency calls, "
                "collision alerts, theft notifications, and SOS assistance. "
                "What would you like to do?",
                data=self._get_capabilities()
            )
    
    async def _handle_emergency_call(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle an emergency call request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle needs emergency assistance.", 
                success=False
            )
        
        # In a real implementation, this would initiate an emergency call
        notification = format_notification(
            notification_type="system_alert",
            message="Emergency call initiated. Help is on the way.",
            severity="critical"
        )
        
        return self._format_response(
            "Emergency call has been initiated. Help is on the way. "
            "Stay on the line and follow any instructions from emergency services.",
            data={
                "action": "emergency_call",
                "vehicle_id": vehicle_id,
                "status": "initiated",
                "notification": notification
            }
        )
    
    async def _handle_collision_alert(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a collision alert."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle was involved in the collision.", 
                success=False
            )
        
        # In a real implementation, this would process a collision alert
        notification = format_notification(
            notification_type="system_alert",
            message="Collision detected. Emergency services have been notified.",
            severity="critical"
        )
        
        return self._format_response(
            "I've detected a collision and notified emergency services. "
            "Are you okay? Do you need any immediate assistance?",
            data={
                "action": "collision_alert",
                "vehicle_id": vehicle_id,
                "status": "processed",
                "notification": notification
            }
        )
    
    async def _handle_theft_notification(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle a theft notification."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you believe has been stolen.", 
                success=False
            )
        
        # In a real implementation, this would process a theft notification
        notification = format_notification(
            notification_type="system_alert",
            message="Potential vehicle theft detected. Authorities have been notified.",
            severity="high"
        )
        
        return self._format_response(
            "I've recorded your vehicle theft report and notified the authorities. "
            "The vehicle's location is being tracked, and you'll receive updates on the situation.",
            data={
                "action": "theft_notification",
                "vehicle_id": vehicle_id,
                "status": "processed",
                "notification": notification
            }
        )
    
    async def _handle_sos(self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handle an SOS request."""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle needs SOS assistance.", 
                success=False
            )
        
        # In a real implementation, this would process an SOS request
        notification = format_notification(
            notification_type="system_alert",
            message="SOS request received. Emergency services have been dispatched.",
            severity="critical"
        )
        
        return self._format_response(
            "SOS signal received. Emergency services have been dispatched to your location. "
            "Please stay in the vehicle if it's safe to do so. Help is on the way.",
            data={
                "action": "sos",
                "vehicle_id": vehicle_id,
                "status": "processed",
                "notification": notification
            }
        )
    
    def _get_capabilities(self) -> Dict[str, str]:
        """Get the capabilities of this agent."""
        return {
            "emergency_call": "Initiate emergency calls to local emergency services",
            "collision_alert": "Process collision alerts and notify emergency services",
            "theft_notification": "Report vehicle theft and track vehicle location",
            "sos": "Send an SOS signal for immediate assistance"
        }
