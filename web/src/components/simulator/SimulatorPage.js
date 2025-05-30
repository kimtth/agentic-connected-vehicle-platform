import { useEffect, useState } from 'react';
import { Container, Typography, Box, Breadcrumbs, Link, Alert, CircularProgress, Button } from '@mui/material';
import { useSearchParams, useNavigate, useParams, useLocation } from 'react-router-dom';
import SimulatorPanel from './SimulatorPanel';
import { fetchVehicleStatus } from '../../api/status';
import { createVehicleStatusThrottle } from '../../config/intervals';

const SimulatorPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const params = useParams();
  const location = useLocation();
  const [isVehicleValid, setIsVehicleValid] = useState(null);
  const [vehicleData, setVehicleData] = useState(null);
  
  // Get vehicle ID from multiple sources
  const vehicleId = 
    searchParams.get('vehicleId') || 
    searchParams.get('id') || 
    searchParams.get('vehicle') ||
    params.vehicleId ||
    params.id ||
    location.state?.vehicleId;

  // Debug logging
  useEffect(() => {
    console.log('SimulatorPage - Debug info:', {
      searchParams: Object.fromEntries(searchParams.entries()),
      params,
      locationState: location.state,
      finalVehicleId: vehicleId
    });
  }, [searchParams, params, location.state, vehicleId]);

  // Verify if the vehicle ID is valid
  useEffect(() => {
    const verifyVehicleId = async () => {
      if (!vehicleId) {
        console.log('No vehicle ID found');
        setIsVehicleValid(false);
        return;
      }
      
      try {
        // Try to fetch the vehicle status to validate the ID with throttling
        if (createVehicleStatusThrottle(vehicleId)) {
          const data = await fetchVehicleStatus(vehicleId);
          setVehicleData(data);
          setIsVehicleValid(true);
        } else {
          console.warn('Vehicle status call throttled, assuming valid');
          setIsVehicleValid(true);
        }
      } catch (error) {
        console.error('Invalid vehicle ID:', error);
        setIsVehicleValid(false);
      }
    };
    
    verifyVehicleId();
  }, [vehicleId]);
  
  // Show loading while validating vehicle
  if (isVehicleValid === null) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4, textAlign: 'center', py: 5 }}>
        <CircularProgress />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Verifying vehicle {vehicleId}...
        </Typography>
      </Container>
    );
  }
  
  // Show error if vehicle ID is invalid or missing
  if (isVehicleValid === false) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="error">
          {!vehicleId 
            ? 'Vehicle ID is required to use the simulator. Please select a vehicle from the dashboard.' 
            : `Invalid vehicle ID "${vehicleId}". Please select a valid vehicle.`
          }
        </Alert>
        
        {/* Debug information */}
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            <strong>Debug Info:</strong><br/>
            URL: {location.pathname + location.search}<br/>
            Query params: {JSON.stringify(Object.fromEntries(searchParams.entries()))}<br/>
            Route params: {JSON.stringify(params)}<br/>
            Location state: {JSON.stringify(location.state)}
          </Typography>
        </Alert>
        
        <Box sx={{ mt: 2, textAlign: 'center', display: 'flex', gap: 2, justifyContent: 'center' }}>
          <Button 
            variant="contained"
            onClick={() => navigate('/')}
          >
            Return to Dashboard
          </Button>
          <Button 
            variant="outlined"
            onClick={() => navigate('/simulator?vehicleId=1')}
          >
            Test with Vehicle ID 1
          </Button>
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
          <Link color="inherit" href={`/vehicles/${vehicleId}`} onClick={(e) => {
            e.preventDefault();
            navigate(`/vehicle-dashboard?id=${vehicleId}`);
          }}>
            Vehicle #{vehicleId}
          </Link>
          <Typography color="textPrimary">Simulator</Typography>
        </Breadcrumbs>
        
        <Typography variant="h5" component="h1" gutterBottom mt={2}>
          Car Device Simulator (Vehicle #{vehicleId})
        </Typography>
        <Typography variant="subtitle1" color="textSecondary" paragraph>
          This simulator allows you to test vehicle commands and monitor responses for this vehicle.
          {vehicleData?.make && vehicleData?.model && ` ${vehicleData.make} ${vehicleData.model}`}
        </Typography>
        
        <Alert severity="info" sx={{ mb: 1 }}>
          Connected to vehicle ID: {vehicleId}. Commands will be sent to this vehicle.
        </Alert>
      </Box>
      
      <SimulatorPanel vehicleId={vehicleId} vehicleData={vehicleData} />
    </Container>
  );
};

export default SimulatorPage;
