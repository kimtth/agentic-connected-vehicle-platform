# Vehicle Profile Manager Agent
class VehicleProfileManager:
    def __init__(self):
        self.vehicles = {}

    def add_vehicle(self, profile):
        vehicle_id = profile.get("VehicleId")
        self.vehicles[vehicle_id] = profile
        return vehicle_id

    def get_vehicle(self, vehicle_id):
        return self.vehicles.get(vehicle_id)

    def list_vehicles(self):
        return list(self.vehicles.values())
