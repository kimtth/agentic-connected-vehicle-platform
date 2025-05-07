"""
Agent Manager for the Connected Vehicle Platform.
Integrates with Cosmos DB for real data access.
"""

import os
import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, AsyncGenerator
from azure.cosmos_db import cosmos_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AgentManager:
    """
    Agent manager to handle agent requests and coordinate with Cosmos DB
    """
    
    def __init__(self):
        """Initialize the agent manager"""
        logger.info("Agent Manager initialized")
    
    async def process_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a request from an agent
        
        Args:
            query: User query
            context: Request context
            
        Returns:
            Response to the agent request
        """
        try:
            agent_type = context.get("agent_type", "general")
            vehicle_id = context.get("vehicle_id")
            
            # Enrich context with vehicle data if available
            if vehicle_id:
                try:
                    # Get vehicle data from Cosmos DB
                    vehicle_data = await self._get_vehicle_data(vehicle_id)
                    if vehicle_data:
                        context["vehicle_data"] = vehicle_data
                        
                    # Get vehicle status
                    vehicle_status = await cosmos_client.get_vehicle_status(vehicle_id)
                    if vehicle_status:
                        context["vehicle_status"] = vehicle_status
                except Exception as e:
                    logger.error(f"Error getting vehicle data: {str(e)}")
            
            # Process based on agent type
            if agent_type == "remote_access":
                return await self._handle_remote_access(query, context)
            elif agent_type == "safety_emergency":
                return await self._handle_safety_emergency(query, context)
            elif agent_type == "charging_energy":
                return await self._handle_charging_energy(query, context)
            elif agent_type == "information_services":
                return await self._handle_information_services(query, context)
            elif agent_type == "vehicle_feature_control":
                return await self._handle_vehicle_feature_control(query, context)
            elif agent_type == "diagnostics_battery":
                return await self._handle_diagnostics_battery(query, context)
            elif agent_type == "alerts_notifications":
                return await self._handle_alerts_notifications(query, context)
            else:
                # General purpose handling
                return await self._handle_general(query, context)
                
        except Exception as e:
            logger.error(f"Error processing agent request: {str(e)}")
            return {
                "response": f"I encountered an error processing your request: {str(e)}",
                "success": False
            }
    
    async def process_request_stream(self, query: str, context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Process a request with streaming response
        
        Args:
            query: User query
            context: Request context
            
        Yields:
            Response chunks
        """
        try:
            # Initial response
            yield {"response": "Processing your request...", "complete": False}
            
            # Get full response
            response = await self.process_request(query, context)
            
            # Split response into chunks for streaming
            full_response = response.get("response", "")
            
            # Simple chunking by sentences
            sentences = full_response.split('. ')
            
            for i, sentence in enumerate(sentences):
                # Last chunk should end with period if original did
                if i < len(sentences) - 1:
                    sentence += '.'
                    
                yield {
                    "response": sentence,
                    "complete": i == len(sentences) - 1,
                    "plugins_used": response.get("plugins_used", []) if i == len(sentences) - 1 else []
                }
                
                # Small delay for realistic streaming
                await asyncio.sleep(0.2)
                
        except Exception as e:
            logger.error(f"Error in streaming response: {str(e)}")
            yield {"response": f"Error: {str(e)}", "complete": True}
    
    async def _get_vehicle_data(self, vehicle_id: str) -> Optional[Dict[str, Any]]:
        """
        Get vehicle data from Cosmos DB
        
        Args:
            vehicle_id: ID of the vehicle
            
        Returns:
            Vehicle data or None if not found
        """
        try:
            # Get all vehicles
            vehicles = await cosmos_client.list_vehicles()
            
            # Find the vehicle with matching ID
            for vehicle in vehicles:
                if vehicle.get("VehicleId") == vehicle_id:
                    return vehicle
            
            return None
        except Exception as e:
            logger.error(f"Error getting vehicle data: {str(e)}")
            return None
    
    # Handler methods for different agent types
    
    async def _handle_remote_access(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle remote access agent requests"""
        # Remote access sample response
        return {
            "response": f"I'll help you with remote access to your vehicle. Your query: {query}",
            "success": True,
            "plugins_used": ["remote_access"]
        }
    
    async def _handle_safety_emergency(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle safety and emergency agent requests"""
        return {
            "response": f"I'm here to assist with safety and emergency situations. Your query: {query}",
            "success": True,
            "plugins_used": ["safety_emergency"]
        }
    
    async def _handle_charging_energy(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle charging and energy agent requests"""
        # Get vehicle status if available
        vehicle_status = context.get("vehicle_status", {})
        battery_level = vehicle_status.get("Battery", "unknown")
        
        if "battery" in query.lower() and battery_level != "unknown":
            return {
                "response": f"Your vehicle's current battery level is {battery_level}%.",
                "success": True,
                "plugins_used": ["charging_energy"],
                "data": {"battery_level": battery_level}
            }
        
        return {
            "response": f"I'll help you with charging and energy management. Your query: {query}",
            "success": True,
            "plugins_used": ["charging_energy"]
        }
    
    async def _handle_information_services(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle information services agent requests"""
        return {
            "response": f"I'll provide information services for your vehicle. Your query: {query}",
            "success": True,
            "plugins_used": ["information_services"]
        }
    
    async def _handle_vehicle_feature_control(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle vehicle feature control agent requests"""
        return {
            "response": f"I'll help you control your vehicle features. Your query: {query}",
            "success": True,
            "plugins_used": ["vehicle_feature_control"]
        }
    
    async def _handle_diagnostics_battery(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle diagnostics and battery agent requests"""
        # Get vehicle status if available
        vehicle_status = context.get("vehicle_status", {})
        
        if vehicle_status:
            battery = vehicle_status.get("Battery", "N/A")
            temperature = vehicle_status.get("Temperature", "N/A")
            speed = vehicle_status.get("Speed", "N/A")
            oil = vehicle_status.get("OilRemaining", "N/A")
            
            return {
                "response": f"Based on diagnostics, your vehicle's status is: Battery: {battery}%, Temperature: {temperature}°C, Current Speed: {speed} km/h, Oil: {oil}%",
                "success": True,
                "plugins_used": ["diagnostics_battery"],
                "data": vehicle_status
            }
        
        return {
            "response": f"I'll help you with vehicle diagnostics and battery monitoring. Your query: {query}",
            "success": True,
            "plugins_used": ["diagnostics_battery"]
        }
    
    async def _handle_alerts_notifications(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle alerts and notifications agent requests"""
        return {
            "response": f"I'll manage alerts and notifications for your vehicle. Your query: {query}",
            "success": True,
            "plugins_used": ["alerts_notifications"]
        }
    
    async def _handle_general(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general agent requests"""
        return {
            "response": f"I'll assist you with your connected vehicle needs. Your query: {query}",
            "success": True,
            "plugins_used": ["general"]
        }

# Create a singleton instance
agent_manager = AgentManager()
