import datetime
import uuid
from typing import Dict, Any, Optional
from utils.agent_tools import format_notification
from azure.cosmos_db import cosmos_client
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from plugin.oai_service import create_chat_service
from utils.logging_config import get_logger

logger = get_logger(__name__)


class AlertsNotificationsAgent:
    """
    Alerts & Notifications Agent for the Connected Car Platform.
    """

    def __init__(self):
        service_factory = create_chat_service()
        self.agent = ChatCompletionAgent(
            service=service_factory,
            name="AlertsNotificationsAgent",
            instructions="You manage vehicle alerts and notifications.",
            plugins=[AlertsNotificationsPlugin()],
        )


class AlertsNotificationsPlugin:
    @kernel_function(description="Check the status of all vehicle alerts")
    async def _handle_alert_status(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to check alert status for.",
                success=False,
            )
        try:
            await cosmos_client.ensure_connected()
            alerts = await cosmos_client.list_notifications(vehicle_id)
            alerts = [
                a
                for a in alerts
                if a.get("type", "").endswith("_alert")
                or a.get("severity", "") in ["high", "critical"]
            ]
            if not alerts:
                return self._format_response(
                    "There are no active alerts for your vehicle at this time.",
                    data={"alerts": [], "vehicle_id": vehicle_id},
                )
            unack = [a for a in alerts if not a.get("read", False)]
            text = "\n".join(
                [
                    f"• {a.get('type','').replace('_',' ').title()}: {a.get('message','No message')} "
                    f"({a.get('severity','medium')} severity, "
                    f"{'unacknowledged' if not a.get('read',False) else 'acknowledged'})"
                    for a in alerts
                ]
            )
            return self._format_response(
                f"Alert status: {len(alerts)} alerts, {len(unack)} unacknowledged.\n\n{text}",
                data={
                    "alerts": alerts,
                    "unacknowledged_count": len(unack),
                    "vehicle_id": vehicle_id,
                },
            )
        except Exception as e:
            logger.error(f"Error retrieving vehicle alerts: {e}")
            return self._format_response(
                "I'm having trouble retrieving your vehicle's alert information. Please try again later.",
                success=False,
            )

    @kernel_function(description="Set a speed alert for a vehicle")
    async def _handle_speed_alert(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # context expected to contain 'query' key
        query = context.get("query", "") if context else ""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to set a speed alert for.",
                success=False,
            )
        # extract speed limit
        speed_limit = None
        for w in query.split():
            try:
                v = float(w)
                if 20 <= v <= 200:
                    speed_limit = v
                    break
            except:
                continue
        speed_limit = speed_limit or context.get("speed_limit") or 120.0
        try:
            await cosmos_client.ensure_connected()
            notification = {
                "id": str(uuid.uuid4()),
                "notificationId": str(uuid.uuid4()),
                "vehicleId": vehicle_id,
                "type": "speed_alert",
                "message": f"Speed alert set for {speed_limit} km/h",
                "timestamp": datetime.datetime.now().isoformat(),
                "read": False,
                "severity": "medium",
                "source": "System",
                "actionRequired": False,
                "parameters": {"speed_limit": speed_limit},
            }
            await cosmos_client.create_notification(notification)
            formatted = format_notification(
                notification_type="system_alert",
                message=f"Speed alert set for {speed_limit} km/h",
                severity="medium",
            )
            return self._format_response(
                f"I've set a speed alert for {speed_limit} km/h. You'll receive a notification if the vehicle exceeds this speed.",
                data={
                    "action": "set_speed_alert",
                    "vehicle_id": vehicle_id,
                    "speed_limit": speed_limit,
                    "notification": formatted,
                },
            )
        except Exception as e:
            logger.error(f"Error setting speed alert: {e}")
            return self._format_response(
                "I encountered an error when trying to set the speed alert. Please try again later.",
                success=False,
            )

    @kernel_function(description="Set a curfew alert for a vehicle")
    async def _handle_curfew_alert(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        query = context.get("query", "") if context else ""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to set a curfew alert for.",
                success=False,
            )
        start = context.get("curfew_start") or "22:00"
        end = context.get("curfew_end") or "06:00"
        try:
            await cosmos_client.ensure_connected()
            notification = {
                "id": str(uuid.uuid4()),
                "notificationId": str(uuid.uuid4()),
                "vehicleId": vehicle_id,
                "type": "curfew_alert",
                "message": f"Curfew alert set from {start} to {end}",
                "timestamp": datetime.datetime.now().isoformat(),
                "read": False,
                "severity": "medium",
                "source": "System",
                "actionRequired": False,
                "parameters": {"start_time": start, "end_time": end},
            }
            await cosmos_client.create_notification(notification)
            formatted = format_notification(
                notification_type="system_alert",
                message=f"Curfew alert set from {start} to {end}",
                severity="medium",
            )
            return self._format_response(
                f"I've set a curfew alert from {start} to {end}. You'll receive a notification if the vehicle is used during these hours.",
                data={
                    "action": "set_curfew_alert",
                    "vehicle_id": vehicle_id,
                    "start_time": start,
                    "end_time": end,
                    "notification": formatted,
                },
            )
        except Exception as e:
            logger.error(f"Error setting curfew alert: {e}")
            return self._format_response(
                "I encountered an error when trying to set the curfew alert. Please try again later.",
                success=False,
            )

    @kernel_function(description="Set a battery alert for a vehicle")
    async def _handle_battery_alert(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        query = context.get("query", "") if context else ""
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to set a battery alert for.",
                success=False,
            )
        threshold = None
        for w in query.split():
            try:
                v = float(w)
                if 5 <= v <= 50:
                    threshold = v
                    break
            except:
                continue
        threshold = threshold or context.get("battery_threshold") or 20.0
        try:
            await cosmos_client.ensure_connected()
            notification = {
                "id": str(uuid.uuid4()),
                "notificationId": str(uuid.uuid4()),
                "vehicleId": vehicle_id,
                "type": "battery_alert",
                "message": f"Battery alert set for {threshold}%",
                "timestamp": datetime.datetime.now().isoformat(),
                "read": False,
                "severity": "medium",
                "source": "System",
                "actionRequired": False,
                "parameters": {"threshold": threshold},
            }
            await cosmos_client.create_notification(notification)
            formatted = format_notification(
                notification_type="system_alert",
                message=f"Battery alert set for {threshold}%",
                severity="medium",
            )
            return self._format_response(
                f"I've set a battery alert for {threshold}%. You'll receive a notification if the battery level falls below this threshold.",
                data={
                    "action": "set_battery_alert",
                    "vehicle_id": vehicle_id,
                    "threshold": threshold,
                    "notification": formatted,
                },
            )
        except Exception as e:
            logger.error(f"Error setting battery alert: {e}")
            return self._format_response(
                "I encountered an error when trying to set the battery alert. Please try again later.",
                success=False,
            )

    @kernel_function(description="View and adjust notification settings")
    async def _handle_notification_settings(
        self, vehicle_id: Optional[str], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if not vehicle_id:
            return self._format_response(
                "Please specify which vehicle you'd like to check notification settings for.",
                success=False,
            )
        try:
            await cosmos_client.ensure_connected()
            notifications = await cosmos_client.list_notifications(vehicle_id)
            types = {
                n.get("type", "")
                for n in notifications
                if n.get("type", "").endswith("_alert")
            }
            settings = {
                "speed_alerts": "speed_alert" in types,
                "curfew_alerts": "curfew_alert" in types,
                "battery_alerts": "battery_alert" in types,
                "maintenance_alerts": "maintenance_alert" in types
                or "service_alert" in types,
                "geofence_alerts": "geofence_alert" in types,
                "notification_channels": {"email": True, "push": True, "sms": False},
            }
            enabled = [
                k.replace("_", " ").title()
                for k, v in settings.items()
                if v and k != "notification_channels"
            ]
            ch = [c for c, v in settings["notification_channels"].items() if v]
            text = f"Enabled alerts: {', '.join(enabled) if enabled else 'None'}\nNotification channels: {', '.join(ch)}"
            return self._format_response(
                f"Notification settings for your vehicle:\n\n{text}",
                data={"settings": settings, "vehicle_id": vehicle_id},
            )
        except Exception as e:
            logger.error(f"Error retrieving notification settings: {e}")
            return self._format_response(
                "I'm having trouble retrieving your notification settings. Please try again later.",
                success=False,
            )

    async def process(
        self, query: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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
                data=self._get_capabilities(),
            )

    def _get_capabilities(self) -> Dict[str, str]:
        return {
            "alert_status": "Check the status of all vehicle alerts",
            "speed_alert": "Set alerts for exceeding speed limits",
            "curfew_alert": "Set alerts for vehicle use outside allowed hours",
            "battery_alert": "Set alerts for low battery levels",
            "notification_settings": "View and adjust notification settings",
        }
