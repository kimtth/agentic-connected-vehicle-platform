import React, { useState, useEffect, useCallback } from 'react';
import { 
  List, ListItem, ListItemText, Typography, 
  Box, CircularProgress, Divider, Chip,
  Button, Dialog, DialogTitle, DialogContent, 
  DialogActions, TextField
} from '@mui/material';
import { fetchServices, addService } from '../api/services';

const ServiceInfo = ({ vehicleId }) => {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [newService, setNewService] = useState({
    ServiceCode: '',
    Description: '',
    StartDate: new Date().toISOString().split('T')[0],
    EndDate: ''
  });

  const loadServices = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchServices(vehicleId);
      setServices(data);
    } catch (error) {
      console.error('Error loading services:', error);
    } finally {
      setLoading(false);
    }
  }, [vehicleId]);

  useEffect(() => {
    if (vehicleId) {
      loadServices();
    }
  }, [vehicleId, loadServices]);

  const handleOpenDialog = () => {
    setOpenDialog(true);
  };

  const handleCloseDialog = () => {
    setOpenDialog(false);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setNewService({
      ...newService,
      [name]: value,
    });
  };

  const handleAddService = async () => {
    try {
      await addService(vehicleId, newService);
      handleCloseDialog();
      loadServices();
    } catch (error) {
      console.error('Error adding service:', error);
    }
  };

  return (
    <>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6" component="h2">
          Vehicle Services
        </Typography>
        <Button 
          variant="contained" 
          color="primary"
          size="small"
          onClick={handleOpenDialog}
        >
          Add Service
        </Button>
      </Box>
      
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
          <CircularProgress size={24} />
        </Box>
      ) : (
        <Box sx={{ width: '55vw', maxHeight: 500, overflow: 'auto' }}>
          <List>
            {services.length > 0 ? (
              services.map((service, index) => (
                <React.Fragment key={`${service.ServiceCode}-${index}`}>
                  <ListItem alignItems="flex-start" className="service-item">
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <span>{service.Description}</span>
                          <Chip 
                            label={service.ServiceCode} 
                            size="small" 
                            color="primary" 
                            variant="outlined" 
                          />
                        </Box>
                      }
                      secondary={
                        <>
                          <Typography component="span" variant="body2" color="text.primary">
                            Start: {new Date(service.StartDate).toLocaleDateString()}
                          </Typography>
                          {service.EndDate && (
                            <>
                              {" — "}
                              <Typography component="span" variant="body2" color="text.primary">
                                End: {new Date(service.EndDate).toLocaleDateString()}
                              </Typography>
                            </>
                          )}
                        </>
                      }
                    />
                  </ListItem>
                  {index < services.length - 1 && <Divider component="li" />}
                </React.Fragment>
              ))
            ) : (
              <ListItem>
                <ListItemText primary="No services available for this vehicle" />
              </ListItem>
            )}
          </List>
        </Box>
      )}

      {/* Add Service Dialog */}
      <Dialog open={openDialog} onClose={handleCloseDialog}>
        <DialogTitle>Add New Service</DialogTitle>
        <DialogContent>
          <TextField
            margin="dense"
            name="ServiceCode"
            label="Service Code"
            fullWidth
            variant="outlined"
            value={newService.ServiceCode}
            onChange={handleInputChange}
          />
          <TextField
            margin="dense"
            name="Description"
            label="Description"
            fullWidth
            variant="outlined"
            value={newService.Description}
            onChange={handleInputChange}
          />
          <TextField
            margin="dense"
            name="StartDate"
            label="Start Date"
            type="date"
            fullWidth
            variant="outlined"
            value={newService.StartDate}
            onChange={handleInputChange}
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            margin="dense"
            name="EndDate"
            label="End Date (Optional)"
            type="date"
            fullWidth
            variant="outlined"
            value={newService.EndDate}
            onChange={handleInputChange}
            InputLabelProps={{ shrink: true }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button onClick={handleAddService} variant="contained">Add</Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default ServiceInfo;
