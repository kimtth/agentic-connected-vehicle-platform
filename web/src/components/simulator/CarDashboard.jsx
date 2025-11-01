import { useEffect, useState } from 'react';
import { Gauge, Zap, Fuel, MapPin } from 'lucide-react';

const CarDashboard = ({ vehicleStatus }) => {
  const [animatedSpeed, setAnimatedSpeed] = useState(0);
  const [animatedBattery, setAnimatedBattery] = useState(0);

  const speed = vehicleStatus?.speed || 0;
  const battery = vehicleStatus?.battery || 0;
  const engineTemp = vehicleStatus?.engineTemp || 0;
  const odometer = vehicleStatus?.odometer || 0;
  const temperature = vehicleStatus?.temperature || 20;
  const oilRemaining = vehicleStatus?.oilRemaining || 0;

  // Animate speed gauge
  useEffect(() => {
    const interval = setInterval(() => {
      setAnimatedSpeed(prev => {
        const diff = speed - prev;
        if (Math.abs(diff) < 0.5) return speed;
        return prev + diff * 0.1;
      });
    }, 50);
    return () => clearInterval(interval);
  }, [speed]);

  // Animate battery gauge
  useEffect(() => {
    const interval = setInterval(() => {
      setAnimatedBattery(prev => {
        const diff = battery - prev;
        if (Math.abs(diff) < 0.5) return battery;
        return prev + diff * 0.1;
      });
    }, 50);
    return () => clearInterval(interval);
  }, [battery]);

  // Calculate rotation angle for speedometer (0-180 degrees)
  const speedAngle = Math.min((animatedSpeed / 200) * 180, 180) - 90;
  
  // Calculate rotation angle for battery gauge (0-180 degrees)
  const batteryAngle = Math.min((animatedBattery / 100) * 180, 180) - 90;

  // Get color based on engine temperature
  const getTempColor = () => {
    if (engineTemp >= 100) return '#ef4444'; // red
    if (engineTemp >= 90) return '#f59e0b'; // orange
    return '#3b82f6'; // blue
  };

  // Get battery color
  const getBatteryColor = () => {
    if (battery <= 20) return '#ef4444'; // red
    if (battery <= 50) return '#f59e0b'; // orange
    return '#10b981'; // green
  };

  return (
    <div className="relative w-full h-full bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-6 overflow-hidden">
      {/* Animated background grid */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute inset-0" style={{
          backgroundImage: 'linear-gradient(#3b82f6 1px, transparent 1px), linear-gradient(90deg, #3b82f6 1px, transparent 1px)',
          backgroundSize: '50px 50px',
          animation: 'grid-scroll 20s linear infinite'
        }} />
      </div>

      {/* Main dashboard container */}
      <div className="relative z-10 grid grid-cols-1 md:grid-cols-2 gap-6 h-full">
        
        {/* Left side - Speedometer */}
        <div className="flex flex-col items-center justify-center">
          <div className="relative w-64 h-64">
            {/* Speedometer background */}
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 200 200">
              {/* Background arc */}
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke="rgba(59, 130, 246, 0.2)"
                strokeWidth="12"
                strokeLinecap="round"
              />
              {/* Colored speed arc */}
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke="#3b82f6"
                strokeWidth="12"
                strokeLinecap="round"
                strokeDasharray={`${(animatedSpeed / 200) * 251.2}, 251.2`}
                className="transition-all duration-300"
              />
              {/* Speed marks */}
              {[0, 40, 80, 120, 160, 200].map((mark, i) => {
                const angle = (i * 36) - 90;
                const rad = (angle * Math.PI) / 180;
                const x1 = 100 + 70 * Math.cos(rad);
                const y1 = 100 + 70 * Math.sin(rad);
                const x2 = 100 + 75 * Math.cos(rad);
                const y2 = 100 + 75 * Math.sin(rad);
                return (
                  <line
                    key={i}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke="white"
                    strokeWidth="2"
                  />
                );
              })}
            </svg>
            
            {/* Speedometer needle */}
            <div 
              className="absolute top-1/2 left-1/2 w-1 h-20 bg-red-500 origin-bottom transition-transform duration-300 shadow-lg"
              style={{ 
                transform: `translate(-50%, -100%) rotate(${speedAngle}deg)`,
                boxShadow: '0 0 10px rgba(239, 68, 68, 0.8)'
              }}
            >
              <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-4 h-4 bg-red-500 rounded-full shadow-lg" />
            </div>
            
            {/* Center display */}
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center mt-8">
              <div className="text-5xl font-bold text-white mb-1">
                {Math.round(animatedSpeed)}
              </div>
              <div className="text-sm text-blue-400 uppercase tracking-wider">km/h</div>
            </div>
          </div>
          
          {/* Speed label */}
          <div className="mt-4 text-center">
            <div className="text-white text-xl font-semibold uppercase tracking-wider">Speed</div>
          </div>
        </div>

        {/* Right side - Battery gauge and info */}
        <div className="flex flex-col items-center justify-center">
          <div className="relative w-64 h-64">
            {/* Battery gauge background */}
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 200 200">
              {/* Background arc */}
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke="rgba(16, 185, 129, 0.2)"
                strokeWidth="12"
                strokeLinecap="round"
              />
              {/* Colored battery arc */}
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke={getBatteryColor()}
                strokeWidth="12"
                strokeLinecap="round"
                strokeDasharray={`${(animatedBattery / 100) * 251.2}, 251.2`}
                className="transition-all duration-300"
              />
              {/* Battery marks */}
              {[0, 25, 50, 75, 100].map((mark, i) => {
                const angle = (i * 45) - 90;
                const rad = (angle * Math.PI) / 180;
                const x1 = 100 + 70 * Math.cos(rad);
                const y1 = 100 + 70 * Math.sin(rad);
                const x2 = 100 + 75 * Math.cos(rad);
                const y2 = 100 + 75 * Math.sin(rad);
                return (
                  <line
                    key={i}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke="white"
                    strokeWidth="2"
                  />
                );
              })}
            </svg>
            
            {/* Battery needle */}
            <div 
              className="absolute top-1/2 left-1/2 w-1 h-20 origin-bottom transition-transform duration-300 shadow-lg"
              style={{ 
                transform: `translate(-50%, -100%) rotate(${batteryAngle}deg)`,
                backgroundColor: getBatteryColor(),
                boxShadow: `0 0 10px ${getBatteryColor()}`
              }}
            >
              <div 
                className="absolute -top-2 left-1/2 -translate-x-1/2 w-4 h-4 rounded-full shadow-lg"
                style={{ backgroundColor: getBatteryColor() }}
              />
            </div>
            
            {/* Center display */}
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center mt-8">
              <div className="text-5xl font-bold text-white mb-1">
                {Math.round(animatedBattery)}
              </div>
              <div className="text-sm text-green-400 uppercase tracking-wider">%</div>
            </div>
          </div>
          
          {/* Battery label */}
          <div className="mt-4 text-center">
            <div className="text-white text-xl font-semibold uppercase tracking-wider">Battery</div>
          </div>
        </div>
      </div>

      {/* Bottom info strip */}
      <div className="relative z-10 grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
        {/* Engine Temperature */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700">
          <div className="flex items-center gap-2 mb-2">
            <Gauge className="h-5 w-5" style={{ color: getTempColor() }} />
            <span className="text-xs text-slate-400 uppercase">Engine Temp</span>
          </div>
          <div className="text-2xl font-bold text-white">
            {engineTemp}°C
          </div>
        </div>

        {/* Cabin Temperature */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="h-5 w-5 text-cyan-400" />
            <span className="text-xs text-slate-400 uppercase">Cabin</span>
          </div>
          <div className="text-2xl font-bold text-white">
            {temperature}°C
          </div>
        </div>

        {/* Oil Remaining */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700">
          <div className="flex items-center gap-2 mb-2">
            <Fuel className="h-5 w-5 text-yellow-400" />
            <span className="text-xs text-slate-400 uppercase">Oil</span>
          </div>
          <div className="text-2xl font-bold text-white">
            {oilRemaining}%
          </div>
        </div>

        {/* Odometer */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-4 border border-slate-700">
          <div className="flex items-center gap-2 mb-2">
            <MapPin className="h-5 w-5 text-purple-400" />
            <span className="text-xs text-slate-400 uppercase">Odometer</span>
          </div>
          <div className="text-2xl font-bold text-white">
            {odometer} km
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes grid-scroll {
          0% {
            transform: translateY(0);
          }
          100% {
            transform: translateY(50px);
          }
        }
      `}</style>
    </div>
  );
};

export default CarDashboard;
