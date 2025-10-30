import React, { useRef, useEffect, useState } from 'react';
import { ArrowUp, ArrowDown, AlertCircle, Link as LinkIcon, Unlink, Loader2, List } from 'lucide-react';

const LogsPanel = ({ logs, isConnected, onToggleConnection, vehicleId, onLoadHistory }) => {
  const logsRef = useRef(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  
  useEffect(() => {
    // Auto-scroll to the bottom when logs update
    if (logsRef.current) {
      logsRef.current.scrollTop = logsRef.current.scrollHeight;
    }
  }, [logs]);

  // Load command history when connected with a vehicle ID
  useEffect(() => {
    const loadCommandHistory = async () => {
      if (isConnected && vehicleId && onLoadHistory) {
        try {
          setIsLoadingHistory(true);
          
          // Fetch command history from the backend
          const response = await fetch(`/api/vehicles/${vehicleId}/command-history`);
          if (!response.ok) {
            throw new Error(`Failed to fetch history: ${response.statusText}`);
          }
          
          const historyData = await response.json();
          
          // Transform history data into log format
          const historyLogs = historyData.map(item => ({
            timestamp: new Date(item.timestamp).toLocaleTimeString(),
            type: item.status === 'success' ? 'success' : 
                  item.status === 'error' ? 'error' : 'sent',
            message: `${item.command}: ${item.response || item.error || 'Command sent'}`
          }));
          
          // Call parent callback to add history to logs
          onLoadHistory(historyLogs);
          
        } catch (error) {
          console.error('Failed to load command history:', error);
          // Add error log entry
          if (onLoadHistory) {
            onLoadHistory([{
              timestamp: new Date().toLocaleTimeString(),
              type: 'error',
              message: `Failed to load command history: ${error.message}`
            }]);
          }
        } finally {
          setIsLoadingHistory(false);
        }
      }
    };
    
    loadCommandHistory();
  }, [isConnected, vehicleId, onLoadHistory]);

  const getIconForLogType = (type) => {
    if (type === 'sent') return <ArrowUp className="h-4 w-4 text-green-600 dark:text-green-400 mr-2" />;
    if (type === 'error') return <AlertCircle className="h-4 w-4 text-red-600 dark:text-red-400 mr-2" />;
    return <ArrowDown className="h-4 w-4 text-blue-600 dark:text-blue-400 mr-2" />;
  };

  const getLogEntryClass = (type) => {
    if (type === 'sent') return 'border-l-4 border-green-500 bg-green-50 dark:bg-green-950/20';
    if (type === 'error') return 'border-l-4 border-red-500 bg-red-50 dark:bg-red-950/20';
    if (type === 'success') return 'border-l-4 border-green-500 bg-green-50 dark:bg-green-950/20';
    return 'border-l-4 border-blue-500 bg-blue-50 dark:bg-blue-950/20';
  };

  return (
    <div className="bg-card rounded-lg border border-border p-4 flex flex-col h-auto">
      <div className="flex items-center gap-2 mb-3 flex-shrink-0">
        <List className="h-5 w-5" />
        <h2 className="text-xl font-semibold">Connection Logs</h2>
        {isLoadingHistory && <Loader2 className="h-5 w-5 animate-spin ml-2" />}
      </div>
      
      <div className="mb-3">
        <div ref={logsRef} className="border border-border rounded-md overflow-y-auto p-2 max-h-[300px]">
          {logs.map((log, index) => {
            // Check if we need to add a timestamp divider
            const needsTimestamp = 
              index === 0 || 
              logs[index-1].timestamp !== log.timestamp;
            
            return (
              <React.Fragment key={index}>
                {needsTimestamp && (
                  <div className="text-xs text-muted-foreground mb-2">[{log.timestamp}]</div>
                )}
                <div className={`flex items-center px-3 py-2 mb-1 rounded ${getLogEntryClass(log.type)}`}>
                  {getIconForLogType(log.type)}
                  <span className="text-sm">{log.message}</span>
                </div>
              </React.Fragment>
            );
          })}
        </div>
      </div>
      
      <div className="flex-shrink-0 border-t border-border pt-3 flex items-center gap-2">
        <i className="fas fa-server" />
        <button
          onClick={onToggleConnection}
          disabled={isConnected}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 dark:bg-blue-700 text-white rounded-md hover:bg-blue-700 dark:hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <LinkIcon className="h-4 w-4" />
          Connect
        </button>
        <button
          onClick={onToggleConnection}
          disabled={!isConnected}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 dark:bg-slate-800 text-white rounded-md hover:bg-slate-800 dark:hover:bg-slate-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Unlink className="h-4 w-4" />
          Disconnect
        </button>
      </div>
    </div>
  );
};

export default LogsPanel;
