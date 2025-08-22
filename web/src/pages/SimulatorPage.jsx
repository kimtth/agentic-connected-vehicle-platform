import { Container, Typography, Box, Breadcrumbs, Link, Alert } from '@mui/material';
import { useSearchParams, useNavigate } from 'react-router-dom';
import CarSimulator from '../components/simulator/CarSimulator';

const SimulatorPage = () => {
  const [searchParams] = useSearchParams();
  const vehicleId = searchParams.get('vehicleId');
  const navigate = useNavigate();
  
  return (
    <Box sx={{ width: '100%', height: 'calc(100vh - 120px)', overflow: 'auto' }}>
      <Container maxWidth={false} sx={{ maxWidth: '1800px', px: { xs: 2, md: 3, lg: 4 } }}>
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
                navigate(`/vehicles/${vehicleId}`);
              }}>
                Vehicle
              </Link>
            )}
            <Typography color="textPrimary">Simulator</Typography>
          </Breadcrumbs>
          
          <Typography variant="h4" component="h1" gutterBottom mt={2}>
            Car Device Simulator {vehicleId ? `(Vehicle #${vehicleId})` : ''}
          </Typography>
          <Typography variant="subtitle1" color="textSecondary" paragraph>
            This simulator allows you to test vehicle commands and monitor responses
            without connecting to a real vehicle.
          </Typography>
          
          {vehicleId && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Connected to vehicle ID: {vehicleId}. Commands will be specific to this vehicle.
            </Alert>
          )}
        </Box>
        
        <CarSimulator vehicleId={vehicleId} />
      </Container>
    </Box>
  );
};

export default SimulatorPage;
