import React, { useRef, useEffect, useState } from 'react';
import { 
  Paper, Typography, Box, Button, CircularProgress 
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { ArrowUpward, ArrowDownward, Error, Link, LinkOff } from '@mui/icons-material';

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(2),
  height: '100%',
  display: 'flex',
  flexDirection: 'column',
  backgroundColor: theme.palette.background.paper,
}));

const LogsContainer = styled(Box)(({ theme }) => ({
  flex: 1,
  overflowY: 'auto',
  maxHeight: '400px',
  marginBottom: theme.spacing(2),
  border: `1px solid ${theme.palette.divider}`,
  borderRadius: theme.shape.borderRadius,
  padding: theme.spacing(1),
}));

const LogEntry = styled(Box)(({ theme, type }) => {
  let borderColor = theme.palette.info.main;
  let bgColor = theme.palette.info.light;
  
  if (type === 'sent') {
    borderColor = theme.palette.success.main;
    bgColor = 'rgba(40, 167, 69, 0.1)';
  } else if (type === 'error') {
    borderColor = theme.palette.error.main;
    bgColor = 'rgba(40, 167, 69, 0.1)';
  } else if (type === 'success') {
    borderColor = theme.palette.success.main;
    bgColor = 'rgba(40, 167, 69, 0.1)';
  }
  
  return {
    padding: '8px 10px',
    marginBottom: '5px',
    borderRadius: theme.shape.borderRadius,
    borderLeft: `3px solid ${borderColor}`,
    backgroundColor: bgColor,
    fontSize: '0.9rem',
    display: 'flex',
    alignItems: 'center',
  };
});

const TimeStamp = styled(Typography)(({ theme }) => ({
  color: theme.palette.text.secondary,
  fontSize: '0.8rem',
  marginBottom: theme.spacing(1),
  padding: 0,
}));

const ConnectionControls = styled(Box)(({ theme }) => ({
  marginTop: 'auto',
  paddingTop: theme.spacing(2),
  borderTop: `1px solid ${theme.palette.divider}`,
  display: 'flex',
  alignItems: 'center',
}));

const LogsHeader = styled(Box)(({ theme }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  marginBottom: theme.spacing(2),
}));

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
    if (type === 'sent') return <ArrowUpward fontSize="small" color="success" sx={{ mr: 1 }} />;
    if (type === 'error') return <ArrowDownward fontSize="small" color="info" sx={{ mr: 1 }} />;
    return <ArrowDownward fontSize="small" color="info" sx={{ mr: 1 }} />;
  };

  return (
    <StyledPaper elevation={3}>
      <LogsContainer>
        <LogsHeader>
          <Typography variant="h6" sx={{ color: 'white', flexGrow: 1 }}>
            Connection Logs
          </Typography>
        </LogsHeader>
        
        <Typography variant="h6" gutterBottom>
          <Box component="i" className="fas fa-list" sx={{ mr: 1 }} />
          Communication Logs
          {isLoadingHistory && <CircularProgress size={20} sx={{ ml: 1 }} />}
        </Typography>
        
        <LogsContainer ref={logsRef}>
          {logs.map((log, index) => {
            // Check if we need to add a timestamp divider
            const needsTimestamp = 
              index === 0 || 
              logs[index-1].timestamp !== log.timestamp;
            
            return (
              <React.Fragment key={index}>
                {needsTimestamp && (
                  <TimeStamp variant="caption">[{log.timestamp}]</TimeStamp>
                )}
                <LogEntry type={log.type}>
                  {getIconForLogType(log.type)}
                  {log.message}
                </LogEntry>
              </React.Fragment>
            );
          })}
        </LogsContainer>
      </LogsContainer>
      
      <ConnectionControls>
        <Box component="i" className="fas fa-server" sx={{ mr: 1 }} />
        <Button
          variant="contained"
          color="success"
          onClick={onToggleConnection}
          startIcon={<Link />}
          disabled={isConnected}
          sx={{ mr: 1 }}
        >
          Connect
        </Button>
        <Button
          variant="contained"
          color="error"
          onClick={onToggleConnection}
          startIcon={<LinkOff />}
          disabled={!isConnected}
        >
          Disconnect
        </Button>
      </ConnectionControls>
    </StyledPaper>
  );
};

export default LogsPanel;
