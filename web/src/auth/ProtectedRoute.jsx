import { AuthenticatedTemplate, UnauthenticatedTemplate, useMsal } from '@azure/msal-react';
import { Box, Button, CircularProgress, Typography } from '@mui/material';
import { useState, useEffect } from 'react';
import { loginRequest, isClientIdConfigured } from './msalConfig';

const ProtectedRoute = ({ children }) => {
  const { inProgress, instance } = useMsal();
  const [initializing, setInitializing] = useState(true);

  useEffect(() => {
    try {
      const active = instance.getActiveAccount();
      if (!active) {
        const accounts = instance.getAllAccounts();
        if (accounts.length) instance.setActiveAccount(accounts[0]);
      }
    } catch {
      // Instance not ready yet; will retry next render
    }
    setInitializing(false);
  }, [instance, inProgress]);

  if (initializing || inProgress === 'startup') {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <CircularProgress />
        <Typography variant="body2" sx={{ mt: 2 }}>Initializing authentication...</Typography>
      </Box>
    );
  }

  return (
    <>
      <AuthenticatedTemplate>{children}</AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <Box sx={{ p: 4, textAlign: 'center' }}>
          {!isClientIdConfigured() ? (
            <>
              <Typography variant="h6" gutterBottom>Authentication Unavailable</Typography>
              <Typography variant="body2" color="text.secondary">
                Please try again later.
              </Typography>
            </>
          ) : (
            <>
              <Typography variant="h6" gutterBottom>Sign in required</Typography>
              <Button
                variant="contained"
                onClick={() => isClientIdConfigured() && instance.loginRedirect(loginRequest)}
              >
                Sign In
              </Button>
            </>
          )}
        </Box>
      </UnauthenticatedTemplate>
    </>
  );
};

export default ProtectedRoute;