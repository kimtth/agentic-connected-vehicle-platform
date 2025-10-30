import { useState } from 'react';
import {
  Lock, Unlock, Power, Square,
  Car, Lightbulb, AlertTriangle, Snowflake, Sun,
  ChevronUp, ChevronDown, Heart,
  BatteryCharging, Navigation, Terminal
} from 'lucide-react';

const CommandPanel = ({ onSendCommand, isConnected, vehicleId }) => {
  const [isSending, setIsSending] = useState(false);
  const selectedCategory = 'vehicle_features';

  const handleSendCommand = async (command) => {
    if (!isConnected) {
      alert('Please connect to server first!');
      return;
    }

    setIsSending(true);
    try {
      await onSendCommand(command);
    } finally {
      setIsSending(false);
    }
  };

  const handleEmergencyCommand = async (command) => {
    if (!isConnected) {
      alert('Please connect to server first!');
      return;
    }

    setIsSending(true);
    try {
      await onSendCommand(command);
    } finally {
      setIsSending(false);
    }
  };

  // Enhanced command categories
  const commandCategories = {
    vehicle_features: {
      title: 'Vehicle Features',
      icon: <Car className="h-4 w-4" />,
      commands: [
        { command: 'LIGHTS_ON', icon: <Lightbulb className="h-4 w-4" />, label: 'Turn On Headlights', params: { light_type: 'headlights' } },
        { command: 'LIGHTS_OFF', icon: <Lightbulb className="h-4 w-4" />, label: 'Turn Off Headlights', params: { light_type: 'headlights' } },
        { command: 'CLIMATE_CONTROL', icon: <Snowflake className="h-4 w-4" />, label: 'Set Climate 20°C', params: { temperature: 20, action: 'cooling' } },
        { command: 'CLIMATE_CONTROL', icon: <Sun className="h-4 w-4" />, label: 'Set Climate 26°C', params: { temperature: 26, action: 'heating' } },
        { command: 'WINDOWS_UP', icon: <ChevronUp className="h-4 w-4" />, label: 'Windows Up', params: { windows: 'all' } },
        { command: 'WINDOWS_DOWN', icon: <ChevronDown className="h-4 w-4" />, label: 'Windows Down', params: { windows: 'all' } }
      ]
    },
    remote_access: {
      title: 'Remote Access',
      icon: <Lock className="h-4 w-4" />,
      commands: [
        { command: 'LOCK_DOORS', icon: <Lock className="h-4 w-4" />, label: 'Lock Doors', params: { doors: 'all' } },
        { command: 'UNLOCK_DOORS', icon: <Unlock className="h-4 w-4" />, label: 'Unlock Doors', params: { doors: 'all' } },
        { command: 'START_ENGINE', icon: <Power className="h-4 w-4" />, label: 'Start Engine', params: { remote: true } },
        { command: 'STOP_ENGINE', icon: <Square className="h-4 w-4" />, label: 'Stop Engine', params: { remote: true } },
        { command: 'HORN_LIGHTS', icon: <AlertTriangle className="h-4 w-4" />, label: 'Horn & Lights', params: { duration: 10 } }
      ]
    },
    emergency: {
      title: 'Emergency & Safety',
      icon: <Heart className="h-4 w-4" />,
      emergency: true,
      commands: [
        { command: 'SOS_REQUEST', icon: <Heart className="h-4 w-4" />, label: 'SOS Emergency', params: { priority: 'critical' } },
        { command: 'EMERGENCY_CALL', icon: <Heart className="h-4 w-4" />, label: 'Emergency Call', params: { call_type: 'manual' } },
        { command: 'COLLISION_ALERT', icon: <AlertTriangle className="h-4 w-4" />, label: 'Report Collision', params: { severity: 'minor' } },
        { command: 'THEFT_NOTIFICATION', icon: <AlertTriangle className="h-4 w-4" />, label: 'Report Theft', params: { reported_by: 'owner' } }
      ]
    },
    charging: {
      title: 'Charging & Energy',
      icon: <BatteryCharging className="h-4 w-4" />,
      commands: [
        { command: 'START_CHARGING', icon: <BatteryCharging className="h-4 w-4" />, label: 'Start Charging', params: {} },
        { command: 'STOP_CHARGING', icon: <Square className="h-4 w-4" />, label: 'Stop Charging', params: {} },
        {
          command: 'SET_CHARGING_SCHEDULE', icon: <BatteryCharging className="h-4 w-4" />, label: 'Set Charge Schedule',
          params: { schedule: { start_time: '22:00', end_time: '06:00' } }
        }
      ]
    },
    information: {
      title: 'Information & Navigation',
      icon: <Navigation className="h-4 w-4" />,
      commands: [
        { command: 'GET_WEATHER', icon: <Navigation className="h-4 w-4" />, label: 'Get Weather Info', params: {} },
        { command: 'FIND_CHARGING_STATIONS', icon: <BatteryCharging className="h-4 w-4" />, label: 'Find Charging Stations', params: {} },
        { command: 'GET_TRAFFIC', icon: <Navigation className="h-4 w-4" />, label: 'Traffic Information', params: {} },
        { command: 'FIND_POI', icon: <Navigation className="h-4 w-4" />, label: 'Find Points of Interest', params: { category: 'restaurant' } }
      ]
    }
  };

  const emergencyCommands = [
    { label: 'Emergency Stop', command: 'EMERGENCY_STOP' },
    { label: 'Emergency Brake', command: 'EMERGENCY_BRAKE' },
    { label: 'Hazard Lights On', command: 'HAZARD_ON' },
    { label: 'Call Emergency', command: 'CALL_911' }
  ];

  const isEmergencyCategory = commandCategories[selectedCategory]?.emergency;

  return (
    <div className="bg-card rounded-lg border border-border p-4 flex flex-col h-auto">
      <div className="flex items-center gap-2 mb-3 flex-shrink-0">
        <Terminal className="h-5 w-5" />
        <h2 className="text-xl font-semibold">Send Commands</h2>
      </div>

      <div className="flex flex-col gap-3 mb-2">
        {/* Primary command grid */}
        <div className="overflow-y-auto max-h-[300px]">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {commandCategories[selectedCategory]?.commands.map((cmd, index) => (
              <button
                key={index}
                onClick={() => handleSendCommand(`${cmd.command}:${JSON.stringify(cmd.params)}`)}
                disabled={isSending || !isConnected}
                className={`flex items-center gap-2 w-full text-left justify-start px-4 py-3 rounded-md transition-all ${isEmergencyCategory
                    ? 'bg-red-600 text-white hover:bg-red-700 hover:-translate-y-0.5 hover:shadow-md disabled:opacity-50'
                    : 'bg-accent hover:bg-primary hover:text-primary-foreground hover:-translate-y-0.5 hover:shadow-md disabled:opacity-50'
                  }`}
              >
                {cmd.icon}
                {cmd.label}
              </button>
            ))}
          </div>
        </div>

        {/* Emergency Commands Section - Always Visible */}
        <div className="flex-shrink-0 border-t border-border pt-3">
          <div className="flex items-center gap-2 mb-3 flex-shrink-0">
            <Terminal className="h-5 w-5" />
            <h2 className="text-xl font-semibold">Emergency Commands</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {emergencyCommands.map((cmd) => (
              <button
                key={cmd.command}
                onClick={() => handleEmergencyCommand(cmd.command)}
                disabled={!isConnected}
                className="flex items-center gap-2 w-full text-left justify-start px-4 py-3 rounded-md transition-all bg-accent hover:bg-primary hover:text-primary-foreground hover:-translate-y-0.5 hover:shadow-md disabled:opacity-50"
              >
                <AlertTriangle className="h-4 w-4" />
                {cmd.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-2 flex-shrink-0">
        {vehicleId && (
          <p className="text-xs text-muted-foreground">
            Target: Vehicle {vehicleId}
          </p>
        )}
      </div>
    </div>
  );
};

export default CommandPanel;
