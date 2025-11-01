import React, { useState, useEffect, useCallback } from 'react';
import { 
  Rocket, Settings, Bell, RefreshCw,
  MessageCircle, Volume2, AlertTriangle, Loader2
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import VehicleMetrics from '../components/simulator/VehicleMetrics';
import { fetchVehicleStatus } from '../api/status';
import { fetchNotifications } from '../api/notifications';
import { fetchFleetMetrics } from '../api/vehicles';

const Dashboard = ({ selectedVehicle }) => {
  const navigate = useNavigate();
  const [vehicleStatus, setVehicleStatus] = useState({
    speed: 0,
    battery: 0,
    temperature: 0,
    engineTemp: 0,
    oilRemaining: 0,
    odometer: 0,
    // engine: 'off', // added
    timestamp: null
  });
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fleetMetrics, setFleetMetrics] = useState({
    totalVehicles: 0,
    activeVehicles: 0,
    lowBattery: 0,
    maintenanceNeeded: 0,
    avgBattery: 0,
    totalDistance: 0
  });

  const refreshDashboard = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Fetch fleet metrics using the vehicles API
      const metrics = await fetchFleetMetrics();
      setFleetMetrics({
        totalVehicles: metrics.totalVehicles ?? 0,
        activeVehicles: metrics.activeVehicles ?? 0,
        lowBattery: metrics.lowBattery ?? 0,
        maintenanceNeeded: metrics.maintenanceNeeded ?? 0,
        avgBattery: Math.round(metrics.avgBattery ?? 0),
        totalDistance: Math.round(metrics.totalDistance ?? 0)
      });
      
      if (!selectedVehicle) {
        setLoading(false);
        return;
      }
      
      const vehicleId = selectedVehicle.vehicleId;
      // Fetch status
      const status = await fetchVehicleStatus(vehicleId);
      if (status) {
        setVehicleStatus({
          speed: status.speed ?? 0,
          battery: status.battery ?? 0,
          temperature: status.temperature ?? 0,
          engineTemp: status.engineTemp ?? status.temperature ?? 0,
          oilRemaining: status.oilRemaining ?? 0,
          odometer: status.odometer ?? 0,
          // engine: status.engine ?? status.engineStatus ?? ((status.speed ?? 0) > 0 ? 'on' : 'off'), // added
          timestamp: status.timestamp || new Date().toISOString()
        });
      }
      // Fetch notifications
      const notificationData = await fetchNotifications(vehicleId);
      setNotifications(Array.isArray(notificationData) ? notificationData.slice(0, 5) : []);
    } catch (err) {
      console.error('Dashboard error:', err);
      setError(`Failed to load dashboard data: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }, [selectedVehicle]);

  useEffect(() => {
    refreshDashboard();
  }, [refreshDashboard]);

  const quickStats = [
    { label: 'Current Speed', rawValue: vehicleStatus.speed, icon: '🚗', unit: 'km/h' },
    { label: 'Battery Level', rawValue: vehicleStatus.battery, icon: '🔋', unit: '%', showProgress: true },
    { label: 'Engine Temp', rawValue: vehicleStatus.engineTemp, icon: '🌡️', unit: '°C' },
    { label: 'Oil Level', rawValue: vehicleStatus.oilRemaining, icon: '⛽', unit: '%', showProgress: true }
  ];

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex justify-center my-8">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-3 px-4 py-3 rounded-md bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200">
          <AlertTriangle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="p-5">
      {/* Fleet Manager Overview */}
      <div className="mb-4 p-3 bg-gradient-to-r from-primary/10 to-primary/5 rounded-lg border border-primary/20">
        <h2 className="text-base font-bold mb-2 flex items-center gap-2">
          <Rocket className="h-4 w-4" />
          Fleet Overview
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
          <div className="flex items-center gap-2 p-2 bg-background/50 rounded">
            <Rocket className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-lg font-bold">{fleetMetrics.totalVehicles}</p>
              <p className="text-[10px] text-muted-foreground">Total Vehicles</p>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 bg-background/50 rounded">
            <Rocket className="h-5 w-5 text-green-600" />
            <div>
              <p className="text-lg font-bold text-green-600">{fleetMetrics.activeVehicles}</p>
              <p className="text-[10px] text-muted-foreground">Active Now</p>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 bg-background/50 rounded">
            <AlertTriangle className="h-5 w-5 text-orange-600" />
            <div>
              <p className="text-lg font-bold text-orange-600">{fleetMetrics.lowBattery}</p>
              <p className="text-[10px] text-muted-foreground">Low Battery</p>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 bg-background/50 rounded">
            <Settings className="h-5 w-5 text-red-600" />
            <div>
              <p className="text-lg font-bold text-red-600">{fleetMetrics.maintenanceNeeded}</p>
              <p className="text-[10px] text-muted-foreground">Need Service</p>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 bg-background/50 rounded">
            <Bell className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-lg font-bold">{fleetMetrics.avgBattery}%</p>
              <p className="text-[10px] text-muted-foreground">Avg Battery</p>
            </div>
          </div>
          <div className="flex items-center gap-2 p-2 bg-background/50 rounded">
            <RefreshCw className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-lg font-bold">{fleetMetrics.totalDistance.toLocaleString()}</p>
              <p className="text-[10px] text-muted-foreground">Total km</p>
            </div>
          </div>
        </div>
      </div>

      {!selectedVehicle ? (
        <div className="flex items-center gap-3 px-4 py-3 rounded-md bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
          <span>Please select a vehicle to view detailed dashboard.</span>
        </div>
      ) : (
        <>
          <div className="mb-6">
            <h1 className="text-xl font-semibold mb-3">
              Vehicle Dashboard
            </h1>
            <p className="text-sm text-muted-foreground mb-3">
              {selectedVehicle.make} {selectedVehicle.model} ({selectedVehicle.vehicleId})
            </p>
        <button 
          className="px-3 py-1.5 text-sm rounded-md border border-input bg-background hover:bg-accent inline-flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          onClick={refreshDashboard} 
          disabled={loading || !selectedVehicle}
        >
          <RefreshCw className="h-3.5 w-3.5" /> {loading ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
        {quickStats.map((stat, index) => (
          <div key={index} className="rounded-lg border bg-card p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-3xl">{stat.icon}</span>
              <div className="flex-1">
                <p className="text-xs text-muted-foreground">{stat.label}</p>
                <p className="text-xl font-bold">
                  {typeof stat.rawValue === 'number' ? stat.rawValue : 0}{stat.unit}
                </p>
              </div>
            </div>
            {stat.showProgress && (
              <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                <div 
                  className="h-full bg-primary transition-all duration-300" 
                  style={{ width: `${stat.rawValue || 0}%` }}
                />
              </div>
            )}
            <p className="text-[10px] text-muted-foreground mt-1.5">
              Last updated: {vehicleStatus.timestamp ? new Date(vehicleStatus.timestamp).toLocaleTimeString() : '-'}
            </p>
          </div>
        ))}
      </div>

      <div className="p-4 bg-card rounded-lg border mb-5">
        <div className="flex items-center gap-2 mb-3">
          <Settings className="h-4 w-4" />
          <h2 className="text-lg font-bold">Quick Actions</h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="rounded-lg border bg-card p-4 shadow-sm cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/agent-chat')}>
            <div className="flex flex-col items-center gap-2 text-center">
              <MessageCircle className="h-10 w-10" />
              <div>
                <h3 className="text-base font-bold mb-1.5">Agent Chat</h3>
                <p className="text-xs text-muted-foreground">Get assistance and control your vehicle with AI-powered chat</p>
              </div>
              <button className="mt-1.5 px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 inline-flex items-center gap-1.5">
                <MessageCircle className="h-3.5 w-3.5" /> Start Chat
              </button>
            </div>
          </div>

          <div className="rounded-lg border bg-card p-4 shadow-sm cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/simulator')}>
            <div className="flex flex-col items-center gap-2 text-center">
              <Rocket className="h-10 w-10" />
              <div>
                <h3 className="text-base font-bold mb-1.5">Car Simulator</h3>
                <p className="text-xs text-muted-foreground">Test and simulate vehicle commands and responses</p>
              </div>
              <button className="mt-1.5 px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 inline-flex items-center gap-1.5">
                <Rocket className="h-3.5 w-3.5" /> Launch Simulator
              </button>
            </div>
          </div>

          <div className="rounded-lg border bg-card p-4 shadow-sm cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate('/services')}>
            <div className="flex flex-col items-center gap-2 text-center">
              <Settings className="h-10 w-10" />
              <div>
                <h3 className="text-base font-bold mb-1.5">Service Status</h3>
                <p className="text-xs text-muted-foreground">View upcoming maintenance and service details</p>
              </div>
              <button className="mt-1.5 px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 inline-flex items-center gap-1.5">
                <Settings className="h-3.5 w-3.5" /> View Services
              </button>
            </div>
          </div>

          <div className="rounded-lg border bg-card p-4 shadow-sm cursor-pointer hover:shadow-md transition-shadow" onClick={() => navigate(`/vehicle-assistant?vehicleId=${selectedVehicle.vehicleId}`)}>
            <div className="flex flex-col items-center gap-2 text-center">
              <Volume2 className="h-10 w-10" />
              <div>
                <h3 className="text-base font-bold mb-1.5">Vehicle Assistant</h3>
                <p className="text-xs text-muted-foreground">Use real-time speech & avatar assistant</p>
              </div>
              <button className="mt-1.5 px-3 py-1.5 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 inline-flex items-center gap-1.5">
                <Volume2 className="h-3.5 w-3.5" /> Launch
              </button>
            </div>
          </div>
        </div>

        <div className="mt-4">
          <h3 className="text-base font-bold mb-2">Vehicle Controls</h3>
          <div className="flex gap-1.5 flex-wrap items-center">
            <button className="px-3 py-1.5 text-sm rounded-md border border-input bg-background hover:bg-accent" onClick={() => navigate(`/agent-chat?query=enable eco mode&vehicleId=${selectedVehicle.vehicleId}`)}>
              🌿 Eco Mode
            </button>
            <button className="px-3 py-1.5 text-sm rounded-md border border-input bg-background hover:bg-accent" onClick={() => navigate(`/agent-chat?query=adjust climate control&vehicleId=${selectedVehicle.vehicleId}`)}>
              ❄️ Climate Control
            </button>
            <button className="px-3 py-1.5 text-sm rounded-md border border-input bg-background hover:bg-accent" onClick={() => navigate(`/agent-chat?query=run vehicle diagnostics&vehicleId=${selectedVehicle.vehicleId}`)}>
              🔧 Diagnostics
            </button>
            <button className="px-3 py-1.5 text-sm rounded-md border border-input bg-background hover:bg-accent inline-flex items-center gap-1.5" onClick={() => navigate('/notifications')}>
              <Bell className="h-3.5 w-3.5" /> View Alerts
            </button>
            <div className="h-5 w-px bg-border mx-1" />
            <button className="px-3 py-1.5 text-sm rounded-md border border-orange-500 text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-950" onClick={() => navigate(`/agent-chat?query=initiate emergency call&vehicleId=${selectedVehicle.vehicleId}`)}>
              📞 Emergency Call
            </button>
            <button className="px-3 py-1.5 text-sm rounded-md border border-red-500 text-red-600 hover:bg-red-50 dark:hover:bg-red-950" onClick={() => navigate(`/agent-chat?query=activate SOS&vehicleId=${selectedVehicle.vehicleId}`)}>
              🆘 SOS Assistance
            </button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 mb-5">
        <div className="lg:col-span-2 p-4 bg-card rounded-lg border h-[350px]">
          <h2 className="text-lg font-bold mb-3">Vehicle Metrics</h2>
          <VehicleMetrics vehicleStatus={vehicleStatus} />
        </div>

        <div className="p-4 bg-card rounded-lg border h-[350px] overflow-auto">
          <div className="flex items-center gap-2 mb-3">
            <Bell className="h-4 w-4" />
            <h2 className="text-lg font-bold">Recent Notifications</h2>
          </div>
          <div className="h-px bg-border mb-3" />

          {notifications.length > 0 ? (
            <div className="flex flex-col gap-1.5">
              {notifications.map((notification, index) => (
                <div key={notification.id || index} className="p-2.5 bg-muted rounded-md">
                  <div className="flex items-start gap-1.5">
                    <div 
                      className="w-1.5 h-1.5 rounded-full mt-1"
                      style={{ 
                        background: notification.severity === 'error' ? '#ef4444' : 
                                   notification.severity === 'warning' ? '#f97316' : '#3b82f6'
                      }}
                    />
                    <div className="flex-1">
                      <p className="text-xs font-medium mb-0.5">
                        {notification.message || notification.title}
                      </p>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] text-muted-foreground">
                          {notification.timestamp ? new Date(notification.timestamp).toLocaleString() : 'Recent'}
                        </span>
                        {notification.severity && (
                          <span className={`inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium ${
                            notification.severity === 'error' ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200' :
                            notification.severity === 'warning' ? 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' :
                            'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                          }`}>
                            {notification.severity}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground text-center mt-6">
              No recent notifications
            </p>
          )}
          <button className="mt-3 w-full px-3 py-1.5 text-sm rounded-md bg-secondary hover:bg-secondary/80" onClick={() => navigate('/notifications')}>
            View All Notifications
          </button>
        </div>
      </div>
        </>
      )}
    </div>
  );
};

export default Dashboard;