import { useEffect } from 'react';
import { useMsal } from '@azure/msal-react';
import { acquireAccessToken } from './msalConfig';
import { setTokenProvider } from '../api/apiClient';

/**
 * Component that bridges MSAL authentication with the API client
 * Sets up token provider so API calls can automatically include auth headers
 */
export const AuthProvider = ({ children }) => {
  const { instance, accounts, inProgress } = useMsal();

  useEffect(() => {
    // Set up the token provider immediately
    setTokenProvider(async () => {
      // Wait for MSAL
      if (inProgress !== 'none') {
        return null;
      }

      // Check auth state
      if (accounts.length === 0) {
        return null;
      }
      
      // Acquire token
      try {
        const token = await acquireAccessToken(instance, accounts[0]);
        return token;
      } catch (error) {
        console.error('Token acquisition failed:', error.message);
        return null;
      }
    });
  }, [instance, accounts, inProgress]);

  return children;
};
