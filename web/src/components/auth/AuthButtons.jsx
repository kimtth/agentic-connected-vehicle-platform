import { AuthenticatedTemplate, UnauthenticatedTemplate, useMsal } from '@azure/msal-react';
import { Button, Stack, Typography } from '@mui/material';
import { loginRequest, isClientIdConfigured } from '../../auth/msalConfig';

const AuthButtons = () => {
  const { instance } = useMsal();
  let account = null;
  try {
    account = instance.getActiveAccount() || instance.getAllAccounts()[0];
  } catch {
    account = null;
  }

  const handleSignIn = () => {
    if (!isClientIdConfigured()) {
      console.error('Cannot sign in: Azure AD client ID not configured');
      return;
    }
    instance.loginRedirect(loginRequest);
  };

  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <AuthenticatedTemplate>
        {account && (
          <Typography variant="body2" sx={{ mr: 1, maxWidth: 180 }} noWrap title={account.username}>
            {account.username}
          </Typography>
        )}
        <Button
          size="small"
          variant="outlined"
          onClick={() => instance.logoutRedirect()}
        >
          Sign Out
        </Button>
      </AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <Button
          size="small"
          variant="contained"
          onClick={handleSignIn}
          disabled={!isClientIdConfigured()}
        >
          Sign In
        </Button>
      </UnauthenticatedTemplate>
    </Stack>
  );
};

export default AuthButtons;
