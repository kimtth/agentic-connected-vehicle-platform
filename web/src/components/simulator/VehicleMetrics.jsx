import { Loader2 } from 'lucide-react';

// Simplified: payload already provides raw numbers
const num = (v) => {
  if (v === 0) return 0;
  return (v === undefined || v === null) ? null : (typeof v === 'number' ? v : (isNaN(Number(v)) ? null : Number(v)));
};

const RANGE_KM_PER_PERCENT = 5; // simple derived metric assumption

const VehicleMetrics = ({ vehicleStatus, loading = false }) => {
  const engineTempValue = num(vehicleStatus?.engineTemp);
  const speedValue = num(vehicleStatus?.speed);
  const batteryValue = num(vehicleStatus?.battery);
  const odometerValue = num(vehicleStatus?.odometer);
  const cabinTempValue = num(vehicleStatus?.temperature); 
  const oilRemainingValue = num(vehicleStatus?.oilRemaining); 
  const timestamp = vehicleStatus?.timestamp;

  const engineColor = engineTempValue == null
    ? 'text-blue-600 dark:text-blue-400'
    : engineTempValue >= 100
      ? 'text-red-600 dark:text-red-400'
      : engineTempValue >= 90
        ? 'text-orange-600 dark:text-orange-400'
        : 'text-blue-600 dark:text-blue-400';

  const metrics = [
    { label: 'Engine Temperature', value: engineTempValue != null ? `${engineTempValue}°C` : 'N/A', icon: '🌡️', color: engineColor },
    { label: 'Cabin Temperature', value: cabinTempValue != null ? `${cabinTempValue}°C` : 'N/A', icon: '🌡️', color: 'text-blue-600 dark:text-blue-400' },
    { label: 'Speed', value: speedValue != null ? `${speedValue} km/h` : 'N/A', icon: '⚡', color: 'text-blue-600 dark:text-blue-400' },
    { label: 'Battery Level', value: batteryValue != null ? `${batteryValue}%` : 'N/A', icon: '🔋', color: 'text-blue-600 dark:text-blue-400' },
    { label: 'Oil Remaining', value: oilRemainingValue != null ? `${oilRemainingValue}%` : 'N/A', icon: '⛽', color: 'text-blue-600 dark:text-blue-400' },
    { label: 'Odometer', value: odometerValue != null ? `${odometerValue} km` : 'N/A', icon: '📊', color: 'text-blue-600 dark:text-blue-400' },
    { label: 'Range Estimate', value: batteryValue != null ? `${Math.round(batteryValue * RANGE_KM_PER_PERCENT)} km` : 'N/A', icon: '🗺️', color: 'text-blue-600 dark:text-blue-400' },
    { label: 'Last Update', value: timestamp ? new Date(timestamp).toLocaleTimeString() : 'N/A', icon: '🕐', color: 'text-blue-600 dark:text-blue-400' }
  ];

  if (loading) {
    return (
      <div className="rounded-lg border bg-card p-2">
        <div className="flex items-center justify-center min-h-[120px]">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-lg border bg-card p-3">
      <h3 className="text-base font-bold mb-3">
        📊 Vehicle Status
      </h3>
      
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {metrics.map((metric, index) => (
          <div key={index} className="rounded-lg border bg-card p-3 hover:bg-accent/50 transition-colors">
            <div className="flex items-center gap-2">
              <span className="text-2xl">{metric.icon}</span>
              <div className="min-w-0 flex-1">
                <div className="text-xs text-muted-foreground truncate">{metric.label}</div>
                <div className={`text-sm font-semibold ${metric.color}`}>{metric.value}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default VehicleMetrics;
