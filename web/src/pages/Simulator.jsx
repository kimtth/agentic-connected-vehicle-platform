import SimulatorPanel from '../components/simulator/SimulatorPanel';

const Simulator = ({ selectedVehicle }) => {
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-xl font-semibold mb-3">Vehicle Simulator</h1>
      <SimulatorPanel vehicleId={selectedVehicle} />
    </div>
  );
};

export default Simulator;
