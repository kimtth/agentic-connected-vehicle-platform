import { useEffect, useState } from 'react';
import { Container, Typography, Box, Breadcrumbs, Link, Alert, CircularProgress, Button } from '@mui/material';
import { useSearchParams, useNavigate, useParams, useLocation } from 'react-router-dom';
import SimulatorPanel from './SimulatorPanel';
import { fetchVehicleStatus } from '../../api/status';

const SimulatorPage = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const params = useParams();
  const location = useLocation();
  const [isVehicleValid, setIsVehicleValid] = useState(null);
  const [vehicleData, setVehicleData] = useState(null);

  const vehicleId =
    searchParams.get('vehicleId') ||
    params.vehicleId ||
    location.state?.vehicleId;

  useEffect(() => {
    let cancelled = false;

    const verifyVehicleId = async () => {
      if (!vehicleId) {
        if (!cancelled) setIsVehicleValid(false);
        return;
      }
      // Best-effort fetch; don't block the page if it fails (hackathon simplicity)
      try {
        const data = await fetchVehicleStatus(vehicleId);
        if (!cancelled) {
          setVehicleData(data || null);
          setIsVehicleValid(true);
        }
      } catch {
        if (!cancelled) setIsVehicleValid(true);
      }
    };

    verifyVehicleId();
    return () => {
      cancelled = true;
    };
  }, [vehicleId]);

  if (isVehicleValid === null) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4, textAlign: 'center', py: 5 }}>
        <CircularProgress />
        <Typography variant="h6" sx={{ mt: 2 }}>
          Verifying vehicle {vehicleId || ''}...
        </Typography>
      </Container>
    );
  }

  if (!vehicleId || isVehicleValid === false) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Alert severity="error">
          {`Vehicle ID is required to use the simulator. Please select a vehicle from the dashboard.`}
        </Alert>
        <Box sx={{ mt: 2, textAlign: 'center', display: 'flex', gap: 2, justifyContent: 'center' }}>
          <Button variant="contained" onClick={() => navigate('/')}>Return to Dashboard</Button>
          <Button variant="outlined" onClick={() => navigate('/simulator?vehicleId=1')}>Test with Vehicle ID 1</Button>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
      <Box mb={3}>
        <Breadcrumbs aria-label="breadcrumb">
          <Link color="inherit" href="/" onClick={(e) => { e.preventDefault(); navigate('/'); }}>
            Dashboard
          </Link>
          <Link color="inherit" href={`/vehicles/${vehicleId}`} onClick={(e) => { e.preventDefault(); navigate(`/vehicle-dashboard?id=${vehicleId}`); }}>
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