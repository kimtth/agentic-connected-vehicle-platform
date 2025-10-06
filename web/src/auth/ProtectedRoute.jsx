import { AuthenticatedTemplate, UnauthenticatedTemplate } from '@azure/msal-react';
import { Box, Typography, Container } from '@mui/material';

const ProtectedRoute = ({ children }) => {
  return (
    <>
      <AuthenticatedTemplate>
        {children}
      </AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <Container maxWidth="sm">
          <Box sx={{ 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center', 
            justifyContent: 'center',
            minHeight: '100vh',
            textAlign: 'center'
          }}>
            <Typography variant="h4" gutterBottom>
              Welcome to Connected Car Platform
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
              Please sign in using the button in the header to access the application
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Click "Sign In" in the top-right corner to continue
            </Typography>
          </Box>
        </Container>
      </UnauthenticatedTemplate>
    </>
  );
};

export default ProtectedRoute;