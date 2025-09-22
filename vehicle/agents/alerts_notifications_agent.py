import datetime
import uuid
from typing import Dict, Any, Optional, Annotated
from azure.cosmos_db import get_cosmos_client
from semantic_kernel.functions import kernel_function
from semantic_kernel.agents import ChatCompletionAgent
from plugin.oai_service import create_chat_service
from utils.logging_config import get_logger
from utils.agent_context import extract_vehicle_id
from utils.vehicle_object_utils import notification_to_dict
from models.notification import Notification  # NEW

logger = get_logger(__name__)


class AlertsNotificationsAgent:
    """
    Alerts & Notifications Agent for the Connected Car Platform.
    """

    def __init__(self):
        # Get the singleton cosmos client instance
        self.cosmos_client = get_cosmos_client()
        service_factory = create_chat_service()
        self.agent = ChatCompletionAgent(
            service=service_factory,
            name="AlertsNotificationsAgent",
            instructions="You manage vehicle alerts and notifications.",
            plugins=[AlertsNotificationsPlugin()],
        )


class AlertsNotificationsPlugin:
    def __init__(self):
        self.cosmos_client = get_cosmos_client()

    @kernel_function(description="Check the status of all vehicle alerts")
    async def _handle_alert_status(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID to check"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context carrying conversation/query info"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)

        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to check alert status for.",
                success=False,
            )
        try:
            await self.cosmos_client.ensure_connected()
            alerts_raw = await self.cosmos_client.list_notifications(vid)
            alerts = [notification_to_dict(a) for a in alerts_raw]
            alerts = [
                a
                for a in alerts
                if a.get("type", "").endswith("_alert")
                or a.get("severity", "") in ["high", "critical"]
                or a.get("Type", "").endswith("_alert")
                or a.get("Severity", "") in ["high", "critical"]
            ]
            if not alerts:
                return self._format_response(
                    "There are no active alerts for your vehicle at this time.",
                    data={"alerts": [], "vehicleId": vid},
                )
            unack = [a for a in alerts if not a.get("read", a.get("Read", False))]
            text = "\n".join(
                [
                    f"• {(a.get('type') or a.get('Type','')).replace('_',' ').title()}: "
                    f"{a.get('message', a.get('Message','No message'))} "
                    f"({a.get('severity', a.get('Severity','medium'))} severity, "
                    f"{'unacknowledged' if not a.get('read', a.get('Read', False)) else 'acknowledged'})"
                    for a in alerts
                ]
            )
            return self._format_response(
                f"Alert status: {len(alerts)} alerts, {len(unack)} unacknowledged.\n\n{text}",
                data={
                    "alerts": alerts,
                    "unacknowledgedCount": len(unack),
                    "vehicleId": vid,
                },
                function_name="_handle_alert_status",
            )
        except Exception as e:
            logger.error(f"Error retrieving vehicle alerts: {e}")
            return self._format_response(
                "I'm having trouble retrieving your vehicle's alert information. Please try again later.",
                success=False,
                function_name="_handle_alert_status",
            )

    @kernel_function(description="Set a speed alert for a vehicle")
    async def _handle_speed_alert(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID to set speed alert for"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context (expects 'query')"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to set a speed alert for.",
                success=False,
            )
        # context expected to contain 'query' key
        query = call_context.get("query", "") if call_context else ""
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
        speed_limit = speed_limit or call_context.get("speed_limit") or 120.0
        try:
            await self.cosmos_client.ensure_connected()
            notification_obj = Notification(
                id=str(uuid.uuid4()),
                notification_id=str(uuid.uuid4()),
                vehicle_id=vid,
                type="speed_alert",
                message=f"Speed alert set for {speed_limit} km/h",
                timestamp=datetime.datetime.now().isoformat(),
                read=False,
                severity="medium",
                source="system",
                action_required=False,
                parameters={"speedLimit": speed_limit},
            )
            await self.cosmos_client.create_notification(
                notification_obj.model_dump(by_alias=True)
            )
            return self._format_response(
                f"I've set a speed alert for {speed_limit} km/h. You'll receive a notification if the vehicle exceeds this speed.",
                data={
                    "action": "setSpeedAlert",
                    "vehicleId": vid,
                    "speedLimit": speed_limit,
                    "notification": notification_obj.model_dump(by_alias=True),
                },
                function_name="_handle_speed_alert",
            )
        except Exception as e:
            logger.error(f"Error setting speed alert: {e}")
            return self._format_response(
                "I encountered an error when trying to set the speed alert. Please try again later.",
                success=False,
                function_name="_handle_speed_alert",
            )

    @kernel_function(description="Set a curfew alert for a vehicle")
    async def _handle_curfew_alert(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID to set curfew alert for"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context (may include start/end)"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to set a curfew alert for.",
                success=False,
            )
        query = call_context.get("query", "") if call_context else ""
        start = call_context.get("curfew_start") or "22:00"
        end = call_context.get("curfew_end") or "06:00"
        try:
            await self.cosmos_client.ensure_connected()
            notification_obj = Notification(
                id=str(uuid.uuid4()),
                notification_id=str(uuid.uuid4()),
                vehicle_id=vid,
                type="curfew_alert",
                message=f"Curfew alert set from {start} to {end}",
                timestamp=datetime.datetime.now().isoformat(),
                read=False,
                severity="medium",
                source="system",
                action_required=False,
                parameters={"startTime": start, "endTime": end},
            )
            await self.cosmos_client.create_notification(
                notification_obj.model_dump(by_alias=True)
            )
            return self._format_response(
                f"I've set a curfew alert from {start} to {end}. You'll receive a notification if the vehicle is used during these hours.",
                data={
                    "action": "setCurfewAlert",
                    "vehicleId": vid,
                    "startTime": start,
                    "endTime": end,
                    "notification": notification_obj.model_dump(by_alias=True),
                },
                function_name="_handle_curfew_alert",
            )
        except Exception as e:
            logger.error(f"Error setting curfew alert: {e}")
            return self._format_response(
                "I encountered an error when trying to set the curfew alert. Please try again later.",
                success=False,
                function_name="_handle_curfew_alert",
            )

    @kernel_function(description="Set a battery alert for a vehicle")
    async def _handle_battery_alert(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID to set battery alert for"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context (expects threshold in query)"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to set a battery alert for.",
                success=False,
            )
        query = call_context.get("query", "") if call_context else ""
        threshold = None
        for w in query.split():
            try:
                v = float(w)
                if 5 <= v <= 50:
                    threshold = v
                    break
            except:
                continue
        threshold = threshold or call_context.get("battery_threshold") or 20.0
        try:
            await self.cosmos_client.ensure_connected()
            notification_obj = Notification(
                id=str(uuid.uuid4()),
                notification_id=str(uuid.uuid4()),
                vehicle_id=vid,
                type="battery_alert",
                message=f"Battery alert set for {threshold}%",
                timestamp=datetime.datetime.now().isoformat(),
                read=False,
                severity="medium",
                source="system",
                action_required=False,
                parameters={"threshold": threshold},
            )
            await self.cosmos_client.create_notification(
                notification_obj.model_dump(by_alias=True)
            )
            return self._format_response(
                f"I've set a battery alert for {threshold}%. You'll receive a notification if the battery level falls below this threshold.",
                data={
                    "action": "setBatteryAlert",
                    "vehicleId": vid,
                    "threshold": threshold,
                    "notification": notification_obj.model_dump(by_alias=True),
                },
                function_name="_handle_battery_alert",
            )
        except Exception as e:
            logger.error(f"Error setting battery alert: {e}")
            return self._format_response(
                "I encountered an error when trying to set the battery alert. Please try again later.",
                success=False,
                function_name="_handle_battery_alert",
            )

    @kernel_function(description="View and adjust notification settings")
    async def _handle_notification_settings(
        self,
        vehicle_id: Annotated[str, "Vehicle GUID to inspect settings for"] = "",
        call_context: Annotated[Dict[str, Any], "Invocation context"] = {},
        **kwargs
    ) -> Dict[str, Any]:
        vid = extract_vehicle_id(call_context, vehicle_id or None)
        if not vid:
            return self._format_response(
                "Please specify which vehicle you'd like to check notification settings for.",
                success=False,
            )
        try:
            await self.cosmos_client.ensure_connected()
            notifications_raw = await self.cosmos_client.list_notifications(vid)
            notifications = [notification_to_dict(n) for n in notifications_raw]
            types = {
                (n.get("type") or n.get("Type") or "")
                for n in notifications
                if (n.get("type") or n.get("Type") or "").endswith("_alert")
            }
            settings = {
                "speedAlerts": "speed_alert" in types,
                "curfewAlerts": "curfew_alert" in types,
                "batteryAlerts": "battery_alert" in types,
                "maintenanceAlerts": ("maintenance_alert" in types)
                or ("service_alert" in types),
                "geofenceAlerts": "geofence_alert" in types,
                "notificationChannels": {"email": True, "push": True, "sms": False},
            }
            # Fixed: use camelCase key 'notificationChannels' consistently
            enabled = [
                k for k, v in settings.items() if v and k != "notificationChannels"
            ]
            ch = [c for c, v in settings["notificationChannels"].items() if v]
            text = f"Enabled alerts: {', '.join(enabled) if enabled else 'None'}\nNotification channels: {', '.join(ch)}"
            return self._format_response(
                f"Notification settings for your vehicle:\n\n{text}",
                data={"settings": settings, "vehicleId": vid},
                function_name="_handle_notification_settings",
            )
        except Exception as e:
            logger.error(f"Error retrieving notification settings: {e}")
            return self._format_response(
                "I'm having trouble retrieving your notification settings. Please try again later.",
                success=False,
                function_name="_handle_notification_settings",
            )

    def _format_response(
        self,
        message: str,
        success: bool = True,
        data: Optional[Dict[str, Any]] = None,
        function_name: str = "",
    ) -> Dict[str, Any]:
        resp = {
            "message": message,
            "success": success,
            "plugins_used": [f"{self.__class__.__name__}.{function_name}"] if function_name else [self.__class__.__name__],
        }
        if data:
            resp["data"] = data
        return resp
