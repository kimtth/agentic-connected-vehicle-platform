# Vehicle Data Manager Agent
class VehicleDataManager:
    def __init__(self):
        self.data_dictionaries = {}
        self.vehicle_logs = {}

    def add_data_dictionary(self, vehicle_id, dictionary):
        self.data_dictionaries[vehicle_id] = dictionary

    def log_vehicle_data(self, vehicle_id, log):
        if vehicle_id not in self.vehicle_logs:
            self.vehicle_logs[vehicle_id] = []
        self.vehicle_logs[vehicle_id].append(log)

    def get_logs(self, vehicle_id):
        return self.vehicle_logs.get(vehicle_id, [])
