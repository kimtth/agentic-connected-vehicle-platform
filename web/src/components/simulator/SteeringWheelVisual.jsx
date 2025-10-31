import { useState, useEffect } from 'react';
import { Navigation, Radio, Phone, MessageSquare, Gauge, Zap, Fuel, MapPin } from 'lucide-react';

const SteeringWheelVisual = ({ speed, isConnected, vehicleStatus }) => {
  const [rotation, setRotation] = useState(0);
  const [animatedSpeed, setAnimatedSpeed] = useState(0);
  const [animatedBattery, setAnimatedBattery] = useState(0);

  const battery = vehicleStatus?.battery || 0;
  const engineTemp = vehicleStatus?.engineTemp || 0;
  const temperature = vehicleStatus?.temperature || 20;
  const oilRemaining = vehicleStatus?.oilRemaining || 0;
  const odometer = vehicleStatus?.odometer || 0;

  // Simulate steering wheel movement based on speed
  useEffect(() => {
    if (speed > 0) {
      const interval = setInterval(() => {
        setRotation(prev => {
          // Oscillate between -15 and 15 degrees when driving
          const amplitude = Math.min(speed / 10, 15);
          const newRotation = amplitude * Math.sin(Date.now() / 1000);
          return newRotation;
        });
      }, 50);
      return () => clearInterval(interval);
    } else {
      setRotation(0);
    }
  }, [speed]);

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

  // Calculate rotation angles for gauges
  const speedAngle = Math.min((animatedSpeed / 200) * 180, 180) - 90;
  const batteryAngle = Math.min((animatedBattery / 100) * 180, 180) - 90;

  // Get color based on engine temperature
  const getTempColor = () => {
    if (engineTemp >= 100) return '#ef4444';
    if (engineTemp >= 90) return '#f59e0b';
    return '#3b82f6';
  };

  // Get battery color
  const getBatteryColor = () => {
    if (battery <= 20) return '#ef4444';
    if (battery <= 50) return '#f59e0b';
    return '#10b981';
  };

  return (
    <div className="relative w-full h-full min-h-[450px] bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-6 overflow-hidden">
      {/* Animated background grid */}
      <div className="absolute inset-0 opacity-10">
        <div className="absolute inset-0" style={{
          backgroundImage: 'linear-gradient(#3b82f6 1px, transparent 1px), linear-gradient(90deg, #3b82f6 1px, transparent 1px)',
          backgroundSize: '50px 50px',
          animation: 'grid-scroll 20s linear infinite'
        }} />
      </div>

      {/* Moving road lines */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {[...Array(5)].map((_, i) => (
          <div
            key={i}
            className="absolute w-2 h-16 bg-white/30 rounded"
            style={{
              left: `${20 + i * 20}%`,
              animation: speed > 0 ? `road-line ${3 - speed / 100}s linear infinite` : 'none',
              animationDelay: `${i * 0.3}s`
            }}
          />
        ))}
      </div>

      {/* Main content container */}
      <div className="relative z-10 h-full flex flex-col">
        {/* Center section - Steering Wheel with side gauges */}
        <div className="flex-1 flex items-center justify-center gap-8">
          {/* Left Gauge - Speedometer */}
          <div className="flex flex-col items-center">
            <div className="relative w-40 h-40">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 200 200">
                <path
                  d="M 20 100 A 80 80 0 0 1 180 100"
                  fill="none"
                  stroke="rgba(59, 130, 246, 0.2)"
                  strokeWidth="10"
                  strokeLinecap="round"
                />
                <path
                  d="M 20 100 A 80 80 0 0 1 180 100"
                  fill="none"
                  stroke="#3b82f6"
                  strokeWidth="10"
                  strokeLinecap="round"
                  strokeDasharray={`${(animatedSpeed / 200) * 251.2}, 251.2`}
                  className="transition-all duration-300"
                />
                {[0, 40, 80, 120, 160, 200].map((mark, i) => {
                  const angle = (i * 36) - 90;
                  const rad = (angle * Math.PI) / 180;
                  const x1 = 100 + 70 * Math.cos(rad);
                  const y1 = 100 + 70 * Math.sin(rad);
                  const x2 = 100 + 75 * Math.cos(rad);
                  const y2 = 100 + 75 * Math.sin(rad);
                  return (
                    <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="white" strokeWidth="2" />
                  );
                })}
              </svg>
              <div 
                className="absolute top-1/2 left-1/2 w-1 h-14 bg-red-500 origin-bottom transition-transform duration-300 shadow-lg"
                style={{ 
                  transform: `translate(-50%, -100%) rotate(${speedAngle}deg)`,
                  boxShadow: '0 0 10px rgba(239, 68, 68, 0.8)'
                }}
              >
                <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-3 h-3 bg-red-500 rounded-full shadow-lg" />
              </div>
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center mt-4">
                <div className="text-3xl font-bold text-white mb-1">{Math.round(animatedSpeed)}</div>
                <div className="text-xs text-blue-400 uppercase tracking-wider">km/h</div>
              </div>
            </div>
            <div className="mt-2 text-white text-sm font-semibold uppercase tracking-wider">Speed</div>
          </div>

          {/* Center - Steering Wheel */}
          <div 
            className="relative transition-transform duration-200"
            style={{ transform: `rotate(${rotation}deg)` }}
          >
            {/* Main steering wheel */}
            <div className="relative w-64 h-64">
              {/* Outer rim */}
              <div className="absolute inset-0 rounded-full bg-gradient-to-br from-slate-700 via-slate-600 to-slate-800 shadow-2xl">
                {/* Grip texture */}
                <div className="absolute inset-2 rounded-full border-4 border-slate-500/30" />
                <div className="absolute inset-5 rounded-full border-2 border-slate-500/20" />
              </div>

              {/* Inner ring */}
              <div className="absolute inset-10 rounded-full bg-gradient-to-br from-slate-800 to-slate-900 border-4 border-slate-600 shadow-inner">
                {/* Center hub with logo */}
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center shadow-lg">
                    <Navigation className="h-8 w-8 text-white" />
                  </div>
                </div>
              </div>

              {/* Steering wheel spokes */}
              {[0, 90, 180, 270].map((angle, i) => (
                <div
                  key={i}
                  className="absolute top-1/2 left-1/2 w-2 h-28 bg-gradient-to-b from-slate-600 to-slate-700 origin-top rounded shadow-lg"
                  style={{
                    transform: `translate(-50%, -50%) rotate(${angle}deg)`,
                    height: i % 2 === 0 ? '6rem' : '0'
                  }}
                />
              ))}

              {/* Control buttons on steering wheel */}
              <div className="absolute top-5 left-1/2 transform -translate-x-1/2">
                <div className="bg-slate-700 rounded-lg p-1.5 shadow-lg">
                  <Phone className="h-4 w-4 text-green-400" />
                </div>
              </div>
              
              <div className="absolute bottom-5 left-1/2 transform -translate-x-1/2">
                <div className="bg-slate-700 rounded-lg p-1.5 shadow-lg">
                  <MessageSquare className="h-4 w-4 text-blue-400" />
                </div>
              </div>
              
              <div className="absolute top-1/2 left-5 transform -translate-y-1/2">
                <div className="bg-slate-700 rounded-lg p-1.5 shadow-lg">
                  <Radio className="h-4 w-4 text-purple-400" />
                </div>
              </div>

              {/* Connection indicator */}
              <div className="absolute -top-3 -right-3">
                <div className={`w-4 h-4 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'} shadow-lg`}>
                  {isConnected && (
                    <div className="w-4 h-4 rounded-full bg-green-500 animate-ping" />
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Right Gauge - Battery */}
          <div className="flex flex-col items-center">
            <div className="relative w-40 h-40">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 200 200">
                <path
                  d="M 20 100 A 80 80 0 0 1 180 100"
                  fill="none"
                  stroke="rgba(16, 185, 129, 0.2)"
                  strokeWidth="10"
                  strokeLinecap="round"
                />
                <path
                  d="M 20 100 A 80 80 0 0 1 180 100"
                  fill="none"
                  stroke={getBatteryColor()}
                  strokeWidth="10"
                  strokeLinecap="round"
                  strokeDasharray={`${(animatedBattery / 100) * 251.2}, 251.2`}
                  className="transition-all duration-300"
                />
                {[0, 25, 50, 75, 100].map((mark, i) => {
                  const angle = (i * 45) - 90;
                  const rad = (angle * Math.PI) / 180;
                  const x1 = 100 + 70 * Math.cos(rad);
                  const y1 = 100 + 70 * Math.sin(rad);
                  const x2 = 100 + 75 * Math.cos(rad);
                  const y2 = 100 + 75 * Math.sin(rad);
                  return (
                    <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="white" strokeWidth="2" />
                  );
                })}
              </svg>
              <div 
                className="absolute top-1/2 left-1/2 w-1 h-14 origin-bottom transition-transform duration-300 shadow-lg"
                style={{ 
                  transform: `translate(-50%, -100%) rotate(${batteryAngle}deg)`,
                  backgroundColor: getBatteryColor(),
                  boxShadow: `0 0 10px ${getBatteryColor()}`
                }}
              >
                <div 
                  className="absolute -top-2 left-1/2 -translate-x-1/2 w-3 h-3 rounded-full shadow-lg"
                  style={{ backgroundColor: getBatteryColor() }}
                />
              </div>
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-center mt-4">
                <div className="text-3xl font-bold text-white mb-1">{Math.round(animatedBattery)}</div>
                <div className="text-xs text-green-400 uppercase tracking-wider">%</div>
              </div>
            </div>
            <div className="mt-2 text-white text-sm font-semibold uppercase tracking-wider">Battery</div>
          </div>
        </div>

        {/* Bottom section - Info Cards & Dashboard lights */}
        <div className="relative mt-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {/* Engine Temperature */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-3 border border-slate-700">
              <div className="flex items-center gap-2 mb-1">
                <Gauge className="h-4 w-4" style={{ color: getTempColor() }} />
                <span className="text-xs text-slate-400 uppercase">Engine Temp</span>
              </div>
              <div className="text-xl font-bold text-white">
                {engineTemp}°C
              </div>
            </div>

            {/* Cabin Temperature */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-3 border border-slate-700">
              <div className="flex items-center gap-2 mb-1">
                <Zap className="h-4 w-4 text-cyan-400" />
                <span className="text-xs text-slate-400 uppercase">Cabin</span>
              </div>
              <div className="text-xl font-bold text-white">
                {temperature}°C
              </div>
            </div>

            {/* Oil Remaining */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-3 border border-slate-700">
              <div className="flex items-center gap-2 mb-1">
                <Fuel className="h-4 w-4 text-yellow-400" />
                <span className="text-xs text-slate-400 uppercase">Oil</span>
              </div>
              <div className="text-xl font-bold text-white">
                {oilRemaining}%
              </div>
            </div>

            {/* Odometer */}
            <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl p-3 border border-slate-700">
              <div className="flex items-center gap-2 mb-1">
                <MapPin className="h-4 w-4 text-purple-400" />
                <span className="text-xs text-slate-400 uppercase">Odometer</span>
              </div>
              <div className="text-xl font-bold text-white">
                {odometer} km
              </div>
            </div>
          </div>

          {/* Dashboard lights indicator */}
          <div className="absolute -bottom-2 left-2 flex gap-4">
            <div className="flex flex-col items-center gap-1">
              <div className={`w-2.5 h-2.5 rounded-full ${speed > 0 ? 'bg-green-500 animate-pulse' : 'bg-gray-600'}`} />
              <span className="text-xs text-slate-400">PWR</span>
            </div>
            <div className="flex flex-col items-center gap-1">
              <div className={`w-2.5 h-2.5 rounded-full ${isConnected ? 'bg-blue-500 animate-pulse' : 'bg-gray-600'}`} />
              <span className="text-xs text-slate-400">CONN</span>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes road-line {
          0% {
            transform: translateY(-100%);
            opacity: 0;
          }
          10% {
            opacity: 1;
          }
          90% {
            opacity: 1;
          }
          100% {
            transform: translateY(calc(100vh + 100%));
            opacity: 0;
          }
        }
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

export default SteeringWheelVisual;
