# Vehicle Service Manager Agent
class VehicleServiceManager:
    def __init__(self):
        self.services = {}

    def add_service(self, vehicle_id, service):
        if vehicle_id not in self.services:
            self.services[vehicle_id] = []
        self.services[vehicle_id].append(service)
        return service

    def list_services(self, vehicle_id):
        return self.services.get(vehicle_id, [])
