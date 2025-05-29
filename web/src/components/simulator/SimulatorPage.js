import { useEffect, useState } from 'react';
import { Container, Typography, Box, Breadcrumbs, Link, Alert, CircularProgress } from '@mui/material';
import { useSearchParams, useNavigate } from 'react-router-dom';
import CarSimulator from './CarSimulator';
import { fetchVehicleStatus } from '../../api/status'; 

const SimulatorPage = () => {
  const [searchParams] = useSearchParams();
  const vehicleId = searchParams.get('vehicleId');
  const navigate = useNavigate();
  const [isVehicleValid, setIsVehicleValid] = useState(null);
  
  // Verify if the vehicle ID is valid
  useEffect(() => {
    const verifyVehicleId = async () => {
      if (!vehicleId) {
        setIsVehicleValid(true); // No vehicle ID is fine - demo mode
        return;
      }
      
      try {
        // Try to fetch the vehicle status to validate the ID
        await fetchVehicleStatus(vehicleId);
        setIsVehicleValid(true);
      } catch (error) {
        console.error('Invalid vehicle ID:', error);
        setIsVehicleValid(false);
      }
    };
    
    verifyVehicleId();
  }, [vehicleId]);
  
  // Show loading while validating vehicle
  if (isVehicleValid === null && vehicleId) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4, textAlign: 'center', py: 5 }}>
        <CircularProgress />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Verifying vehicle...
        </Typography>
      </Container>
    );
  }
  
  // Show error if vehicle ID is invalid
  if (isVehicleValid === false) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="error">
          Invalid vehicle ID. Please select a valid vehicle.
        </Alert>
        <Box sx={{ mt: 2, textAlign: 'center' }}>
          <Link 
            component="button"
            onClick={() => navigate('/')}
            variant="body1"
          >
            Return to Dashboard
          </Link>
        </Box>
      </Container>
    );
  }
  
  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box mb={3}>
        <Breadcrumbs aria-label="breadcrumb">
          <Link color="inherit" href="/" onClick={(e) => {
            e.preventDefault();
            navigate('/');
          }}>
            Dashboard
          </Link>
          {vehicleId && (
            <Link color="inherit" href={`/vehicles/${vehicleId}`} onClick={(e) => {
              e.preventDefault();
              navigate(`/vehicle-dashboard?id=${vehicleId}`);
            }}>
              Vehicle
            </Link>
          )}
          <Typography color="textPrimary">Simulator</Typography>
        </Breadcrumbs>
        
        <Typography variant="h5" component="h1" gutterBottom mt={2}>
          Car Device Simulator {vehicleId ? `(Vehicle #${vehicleId})` : ''}
        </Typography>
        <Typography variant="subtitle1" color="textSecondary" paragraph>
          This simulator allows you to test vehicle commands and monitor responses
          {vehicleId ? ' for a specific vehicle.' : ' in demo mode.'}
        </Typography>
        
        {vehicleId ? (
          <Alert severity="info" sx={{ mb: 1 }}>
            Connected to vehicle ID: {vehicleId}. Commands will be sent to this vehicle.
          </Alert>
        ) : (
          <Alert severity="warning" sx={{ mb: 1 }}>
            Running in demo mode. Select a vehicle from the dashboard to send real commands.
          </Alert>
        )}
      </Box>
      
      <CarSimulator vehicleId={vehicleId} />
    </Container>
  );
};

export default SimulatorPage;
