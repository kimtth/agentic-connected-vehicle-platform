import { useState } from 'react';
import {
  Lock, Unlock, Power, Square,
  Lightbulb, AlertTriangle, Snowflake, Heart, Terminal
} from 'lucide-react';

const CommandPanel = ({ onSendCommand, isConnected, vehicleId }) => {
  const [isSending, setIsSending] = useState(false);

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

  // Essential commands only - consolidated for compact display
  const essentialCommands = [
    { command: 'LOCK_DOORS', icon: <Lock className="h-4 w-4" />, label: 'Lock Doors', params: { doors: 'all' } },
    { command: 'UNLOCK_DOORS', icon: <Unlock className="h-4 w-4" />, label: 'Unlock Doors', params: { doors: 'all' } },
    { command: 'START_ENGINE', icon: <Power className="h-4 w-4" />, label: 'Start Engine', params: { remote: true } },
    { command: 'STOP_ENGINE', icon: <Square className="h-4 w-4" />, label: 'Stop Engine', params: { remote: true } },
    { command: 'LIGHTS_ON', icon: <Lightbulb className="h-4 w-4" />, label: 'Lights On', params: { light_type: 'headlights' } },
    { command: 'CLIMATE_CONTROL', icon: <Snowflake className="h-4 w-4" />, label: 'Climate 20°C', params: { temperature: 20, action: 'cooling' } },
  ];

  const emergencyCommands = [
    { label: 'SOS Emergency', command: 'SOS_REQUEST', icon: <Heart className="h-4 w-4" /> },
    { label: 'Emergency Stop', command: 'EMERGENCY_STOP', icon: <AlertTriangle className="h-4 w-4" /> },
  ];

  return (
    <div className="bg-card rounded-lg border border-border p-3 flex flex-col h-auto">
      <div className="flex items-center gap-2 mb-2 flex-shrink-0">
        <Terminal className="h-4 w-4" />
        <h2 className="text-lg font-semibold">Commands</h2>
      </div>

      <div className="flex flex-col gap-2">
        {/* Essential Commands */}
        <div className="grid grid-cols-2 gap-2">
          {essentialCommands.map((cmd, index) => (
            <button
              key={index}
              onClick={() => handleSendCommand(`${cmd.command}:${JSON.stringify(cmd.params)}`)}
              disabled={isSending || !isConnected}
              className="flex items-center gap-1.5 w-full text-left justify-start px-3 py-2 rounded-md transition-all bg-accent hover:bg-primary hover:text-primary-foreground text-sm disabled:opacity-50"
            >
              {cmd.icon}
              <span className="truncate">{cmd.label}</span>
            </button>
          ))}
        </div>

        {/* Emergency Commands */}
        <div className="border-t border-border pt-2">
          <div className="grid grid-cols-2 gap-2">
            {emergencyCommands.map((cmd) => (
              <button
                key={cmd.command}
                onClick={() => handleEmergencyCommand(cmd.command)}
                disabled={!isConnected}
                className="flex items-center gap-1.5 w-full text-left justify-start px-3 py-2 rounded-md transition-all bg-accent text-sm hover:text-primary-foreground text-sm disabled:opacity-50"
              >
                {cmd.icon}
                <span className="truncate">{cmd.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-1 flex-shrink-0">
        {vehicleId && (
          <p className="text-xs text-muted-foreground">
            Vehicle {vehicleId}
          </p>
        )}
      </div>
    </div>
  );
};

export default CommandPanel;
