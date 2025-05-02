# Vehicle Notification Handler Agent
class VehicleNotificationHandler:
    def __init__(self):
        self.notifications = []

    def send_notification(self, notification):
        self.notifications.append(notification)
        # In a real system, this would push to a websocket or external system
        return notification

    def list_notifications(self):
        return self.notifications
