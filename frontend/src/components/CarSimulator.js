import React, { useState, useEffect, useCallback } from 'react';
import { 
  Box, Typography, Container, Button, 
  TextField, Card, CardContent, Grid, Paper,
  Dialog, DialogTitle, DialogContent, DialogActions,
  FormControl, InputLabel, Select, MenuItem
} from '@mui/material';
import { DirectionsCar, Speed, LocalGasStation, Battery90, Thermostat, Add } from '@mui/icons-material';
import { fetchVehicles, addVehicle } from '../api/vehicles';
import { sendCommand } from '../api/commands';
import { api } from '../api/apiClient';

const VehicleCard = ({ vehicle, onRefresh }) => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  // Define loadStatus with useCallback before using it in useEffect
  const loadStatus = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.get(`/vehicle/status/${vehicle.VehicleId}`);
      setStatus(response.data);
    } catch (err) {
      console.error('Error loading status:', err);
    } finally {
      setLoading(false);
    }
  }, [vehicle.VehicleId]); // Add proper dependency here

  useEffect(() => {
    loadStatus();
    const interval = setInterval(loadStatus, 5000);
    return () => clearInterval(interval);
  }, [loadStatus]);

  const handleSendCommand = async (commandType, payload = {}) => {
    try {
      const command = {
        vehicleId: vehicle.VehicleId,
        commandType,
        payload
      };

      await sendCommand(command);
      setTimeout(loadStatus, 1500); // Refresh after delay to see effect
    } catch (err) {
      console.error('Error sending command:', err);
    }
  };

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
          <DirectionsCar sx={{ mr: 1 }} />
          {vehicle.Brand} {vehicle.VehicleModel} ({vehicle.VehicleId})
        </Typography>

        {status && (
          <Grid container spacing={2} sx={{ mb: 2 }}>
            <Grid item xs={3} sx={{ textAlign: 'center' }}>
              <Battery90 color="primary" />
              <Typography variant="h6">{status.Battery}%</Typography>
              <Typography variant="body2">Battery</Typography>
            </Grid>
            <Grid item xs={3} sx={{ textAlign: 'center' }}>
              <Thermostat color="error" />
              <Typography variant="h6">{status.Temperature}°C</Typography>
              <Typography variant="body2">Temperature</Typography>
            </Grid>
            <Grid item xs={3} sx={{ textAlign: 'center' }}>
              <Speed color="info" />
              <Typography variant="h6">{status.Speed} km/h</Typography>
              <Typography variant="body2">Speed</Typography>
            </Grid>
            <Grid item xs={3} sx={{ textAlign: 'center' }}>
              <LocalGasStation color="success" />
              <Typography variant="h6">{status.OilRemaining}%</Typography>
              <Typography variant="body2">Oil</Typography>
            </Grid>
          </Grid>
        )}

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button 
            variant="contained" 
            color="success" 
            size="small"
            onClick={() => handleSendCommand('START_ENGINE', { initial_speed: 5 })}
          >
            Start Engine
          </Button>
          <Button 
            variant="contained" 
            color="error" 
            size="small"
            onClick={() => handleSendCommand('STOP_ENGINE')}
          >
            Stop Engine
          </Button>
          <Button 
            variant="contained" 
            color="primary" 
            size="small"
            onClick={() => handleSendCommand('ACTIVATE_CLIMATE', { target_temperature: 22 })}
          >
            Climate Control
          </Button>
        </Box>
      </CardContent>
    </Card>
  );
};

const CarSimulator = () => {
  const [vehicles, setVehicles] = useState([]);
  const [openDialog, setOpenDialog] = useState(false);
  const [newVehicle, setNewVehicle] = useState({
    VehicleId: '',
    Brand: '',
    VehicleModel: '',
    Year: new Date().getFullYear(),
    Region: 'North America'
  });

  useEffect(() => {
    loadVehicles();
  }, []);

  const loadVehicles = async () => {
    try {
      const data = await fetchVehicles();
      setVehicles(data);
    } catch (err) {
      console.error('Error loading vehicles:', err);
    }
  };

  const handleAddVehicle = async () => {
    try {
      await addVehicle(newVehicle);
      setOpenDialog(false);
      loadVehicles();
    } catch (err) {
      console.error('Error adding vehicle:', err);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewVehicle({
      ...newVehicle,
      [name]: value
    });
  };

  return (
    <Container maxWidth="md" sx={{ my: 4 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4" component="h1">
          Car Simulator
        </Typography>
        <Button 
          variant="contained" 
          startIcon={<Add />}
          onClick={() => setOpenDialog(true)}
        >
          Add Vehicle
        </Button>
      </Box>

      <Typography variant="body1" paragraph>
        This simulator allows you to interact with virtual vehicles and observe how the system responds to various commands.
      </Typography>

      {vehicles.length > 0 ? (
        vehicles.map(vehicle => (
          <VehicleCard 
            key={vehicle.VehicleId} 
            vehicle={vehicle} 
            onRefresh={loadVehicles}
          />
        ))
      ) : (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography>No vehicles available. Add a vehicle to start.</Typography>
        </Paper>
      )}

      {/* Add Vehicle Dialog */}
      <Dialog open={openDialog} onClose={() => setOpenDialog(false)}>
        <DialogTitle>Add New Vehicle</DialogTitle>
        <DialogContent>
          <TextField
            margin="dense"
            name="VehicleId"
            label="Vehicle ID"
            fullWidth
            variant="outlined"
            value={newVehicle.VehicleId}
            onChange={handleInputChange}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            name="Brand"
            label="Brand"
            fullWidth
            variant="outlined"
            value={newVehicle.Brand}
            onChange={handleInputChange}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            name="VehicleModel"
            label="Model"
            fullWidth
            variant="outlined"
            value={newVehicle.VehicleModel}
            onChange={handleInputChange}
            sx={{ mb: 2 }}
          />
          <TextField
            margin="dense"
            name="Year"
            label="Year"
            type="number"
            fullWidth
            variant="outlined"
            value={newVehicle.Year}
            onChange={handleInputChange}
            sx={{ mb: 2 }}
          />
          <FormControl fullWidth>
            <InputLabel>Region</InputLabel>
            <Select
              name="Region"
              value={newVehicle.Region}
              label="Region"
              onChange={handleInputChange}
            >
              <MenuItem value="North America">North America</MenuItem>
              <MenuItem value="Europe">Europe</MenuItem>
              <MenuItem value="Asia">Asia</MenuItem>
              <MenuItem value="Africa">Africa</MenuItem>
              <MenuItem value="Australia">Australia</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
          <Button onClick={handleAddVehicle} variant="contained">Add</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default CarSimulator;
