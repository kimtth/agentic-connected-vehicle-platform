import React, { useRef, useEffect, useState } from 'react';
import { 
  Paper, Typography, Box, Button, TextField, Divider, CircularProgress 
} from '@mui/material';
import { styled } from '@mui/material/styles';
import { ArrowUpward, ArrowDownward, Error, Link, LinkOff } from '@mui/icons-material';
import { getCommandHistory } from '../../api/commands';

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
    bgColor = 'rgba(220, 53, 69, 0.1)';
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

const LogsPanel = ({ logs, isConnected, onToggleConnection, vehicleId }) => {
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
      if (isConnected && vehicleId) {
        try {
          setIsLoadingHistory(true);
          const history = await getCommandHistory(vehicleId);
          
          // Process history items and add them to logs
          // This would typically be handled through the parent component
          // via a callback, but we're showing the implementation here
        } catch (error) {
          console.error('Failed to load command history:', error);
        } finally {
          setIsLoadingHistory(false);
        }
      }
    };
    
    loadCommandHistory();
  }, [isConnected, vehicleId]);

  const getIconForLogType = (type) => {
    if (type === 'sent') return <ArrowUpward fontSize="small" color="success" sx={{ mr: 1 }} />;
    if (type === 'error') return <Error fontSize="small" color="error" sx={{ mr: 1 }} />;
    return <ArrowDownward fontSize="small" color="info" sx={{ mr: 1 }} />;
  };

  return (
    <StyledPaper elevation={3}>
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
      
      <ConnectionControls>
        <Box component="i" className="fas fa-server" sx={{ mr: 1 }} />
        <TextField
          size="small"
          value={`https://api.car-platform.example.com/v1/vehicles/${vehicleId || 'demo'}/commands`}
          disabled
          sx={{ mr: 1, flex: 1 }}
        />
        <Button
          variant="contained"
          color={isConnected ? "success" : "error"}
          onClick={onToggleConnection}
          startIcon={isConnected ? <Link /> : <LinkOff />}
        >
          {isConnected ? 'Connected' : 'Disconnected'}
        </Button>
      </ConnectionControls>
    </StyledPaper>
  );
};

export default LogsPanel;
