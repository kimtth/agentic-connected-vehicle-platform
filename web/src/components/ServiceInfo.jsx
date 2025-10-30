import React, { useState, useEffect, useCallback } from 'react';
import { Loader2, Plus, X } from 'lucide-react';
import { fetchServices, addService } from '../api/services';

const ServiceInfo = ({ vehicleId }) => {
  const [services, setServices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(false);
  const [newService, setNewService] = useState({
    serviceCode: '',
    description: '',
    startDate: new Date().toISOString().split('T')[0],
    endDate: ''
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
    <div className="p-5">
      <div className="flex justify-between items-center mb-3">
        <h1 className="text-xl font-semibold mb-3">Vehicle Services</h1>
        <button 
          onClick={handleOpenDialog}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 text-xs"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Service
        </button>
      </div>
      
      {loading ? (
        <div className="flex justify-center p-3">
          <Loader2 className="h-5 w-5 animate-spin" />
        </div>
      ) : (
        <div className="w-[55vw] max-h-[450px] overflow-auto">
          <div className="space-y-1.5">
            {services.length > 0 ? (
              services.map((service, index) => (
                <React.Fragment key={`${service.serviceCode}-${index}`}>
                  <div className="service-item py-2.5">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <span className="font-medium text-sm">{service.description}</span>
                      <span className="px-1.5 py-0.5 text-[10px] border border-primary text-primary rounded">
                        {service.serviceCode}
                      </span>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      <span>Start: {new Date(service.startDate).toLocaleDateString()}</span>
                      {service.endDate && (
                        <>
                          <span> — </span>
                          <span>End: {new Date(service.endDate).toLocaleDateString()}</span>
                        </>
                      )}
                    </div>
                  </div>
                  {index < services.length - 1 && <div className="border-t border-border" />}
                </React.Fragment>
              ))
            ) : (
              <div className="py-2.5 text-xs text-muted-foreground">
                No services available for this vehicle
              </div>
            )}
          </div>
        </div>
      )}

      {/* Add Service Dialog */}
      {openDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-card rounded-lg border border-border p-5 w-full max-w-md">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-base font-semibold">Add New Service</h3>
              <button onClick={handleCloseDialog} className="text-muted-foreground hover:text-foreground">
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium mb-0.5">Service Code</label>
                <input
                  type="text"
                  name="serviceCode"
                  className="w-full px-2.5 py-1.5 text-sm border border-input rounded-md"
                  value={newService.serviceCode}
                  onChange={handleInputChange}
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-0.5">Description</label>
                <input
                  type="text"
                  name="description"
                  className="w-full px-2.5 py-1.5 text-sm border border-input rounded-md"
                  value={newService.description}
                  onChange={handleInputChange}
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-0.5">Start Date</label>
                <input
                  type="date"
                  name="startDate"
                  className="w-full px-2.5 py-1.5 text-sm border border-input rounded-md"
                  value={newService.startDate}
                  onChange={handleInputChange}
                />
              </div>
              <div>
                <label className="block text-xs font-medium mb-0.5">End Date (Optional)</label>
                <input
                  type="date"
                  name="endDate"
                  className="w-full px-2.5 py-1.5 text-sm border border-input rounded-md"
                  value={newService.endDate}
                  onChange={handleInputChange}
                />
              </div>
            </div>
            <div className="flex justify-end gap-1.5 mt-5">
              <button onClick={handleCloseDialog} className="px-3 py-1.5 text-sm border border-input rounded-md hover:bg-accent">
                Cancel
              </button>
              <button onClick={handleAddService} className="px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-md hover:bg-primary/90">
                Add
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ServiceInfo;
