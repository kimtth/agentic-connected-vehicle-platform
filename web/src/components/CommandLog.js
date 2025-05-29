import { useState, useEffect, useCallback } from 'react';
import { 
  Table, TableBody, TableCell, TableContainer, 
  TableHead, TableRow, Paper, Typography, Box, Button, 
  Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, MenuItem, Select, InputLabel, FormControl
} from '@mui/material';
import { getCommandHistory as fetchCommands, sendVehicleCommand } from '../api/commands';

const CommandLog = ({ vehicleId }) => {
  const [commands, setCommands] = useState([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [newCommand, setNewCommand] = useState({
    vehicleId: '',
    commandType: '',
    payload: {},
  });
  const [payloadString, setPayloadString] = useState('{}');

  const loadCommands = useCallback(async () => {
    try {
      const data = await fetchCommands(vehicleId);
      setCommands(data);
    } catch (error) {
      console.error('Error loading commands:', error);
    }
  }, [vehicleId]);

  useEffect(() => {
    loadCommands();
    // Poll for updates every 5 seconds
    const interval = setInterval(loadCommands, 5000);
    return () => clearInterval(interval);
  }, [loadCommands, vehicleId]); // Add vehicleId as dependency

  const handleOpenDialog = () => {
    setOpenDialog(true);
    // Pre-fill the vehicle ID if provided
    if (vehicleId) {
      setNewCommand(prev => ({
        ...prev,
        vehicleId
      }));
    }
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewCommand({
      ...newCommand,
      [name]: value,
    });
  };

  const handlePayloadChange = (e) => {
    setPayloadString(e.target.value);
    try {
      const payload = JSON.parse(e.target.value);
      setNewCommand({
        ...newCommand,
        payload,
      });
    } catch (error) {
      // Invalid JSON, ignore for now
    }
  };

  const handleSendCommand = async () => {
    try {
      await sendVehicleCommand(newCommand);
      handleCloseDialog();
      loadCommands();
    } catch (error) {
      console.error('Error sending command:', error);
    }
  };

  return (
    <>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" component="h2">
          Command Log
        </Typography>
        <Button 
          variant="contained" 
          color="primary"
          size="small"
          onClick={handleOpenDialog}
          className="send-command-button"
        >
          Send Command
        </Button>
      </Box>
      
      <TableContainer component={Paper} sx={{ maxHeight: 200 }}>
        <Table stickyHeader aria-label="command log table" size="small" className="command-log-table">
          <TableHead>
            <TableRow>
              <TableCell>Command ID</TableCell>
              <TableCell>Vehicle ID</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {commands.length > 0 ? (
              commands.map((command) => (
                <TableRow key={command.commandId}>
                  <TableCell>{command.commandId}</TableCell>
                  <TableCell>{command.vehicleId}</TableCell>
                  <TableCell>{command.commandType}</TableCell>
                  <TableCell>{command.status}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  No commands found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Send Command Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog}>
        <DialogTitle>Send New Command</DialogTitle>
        <DialogContent>
          <TextField
            margin="dense"
            name="vehicleId"
            label="Vehicle ID"
            fullWidth
            variant="outlined"
            value={newCommand.vehicleId}
            onChange={handleInputChange}
          />
          <FormControl fullWidth margin="dense">
            <InputLabel id="command-type-label">Command Type</InputLabel>
            <Select
              labelId="command-type-label"
              name="commandType"
              value={newCommand.commandType}
              label="Command Type"
              onChange={handleInputChange}
            >
              <MenuItem value="START_ENGINE">Start Engine</MenuItem>
              <MenuItem value="STOP_ENGINE">Stop Engine</MenuItem>
              <MenuItem value="LOCK_DOORS">Lock Doors</MenuItem>
              <MenuItem value="UNLOCK_DOORS">Unlock Doors</MenuItem>
              <MenuItem value="ACTIVATE_CLIMATE">Activate Climate Control</MenuItem>
            </Select>
          </FormControl>
          <TextField
            margin="dense"
            name="payload"
            label="Payload (JSON)"
            fullWidth
            multiline
            rows={4}
            variant="outlined"
            value={payloadString}
            onChange={handlePayloadChange}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleSendCommand} variant="contained">Send</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default CommandLog;
