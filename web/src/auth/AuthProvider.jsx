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
        console.debug('[AuthProvider] MSAL in progress:', inProgress);
        return null;
      }

      // Check auth state
      if (accounts.length === 0) {
        console.warn('[AuthProvider] ⚠️ No accounts - user needs to sign in');
        return null;
      }
      
      // Acquire token
      try {
        // console.log('[AuthProvider] Acquiring token for account:', accounts[0]);
        const token = await acquireAccessToken(instance, accounts[0]);
        if (token && process.env.NODE_ENV === 'development') {
          console.log('[AuthProvider] ✅ Token acquired');
          // Decode token to inspect claims (dev only)
          try {
            const [, payload] = token.split('.');
            const decoded = JSON.parse(atob(payload));
            console.log('[AuthProvider] Token claims:', {
              aud: decoded.aud,
              iss: decoded.iss,
              exp: new Date(decoded.exp * 1000).toISOString(),
            });
          } catch (e) {
            // Ignore decode errors
          }
        }
        return token;
      } catch (error) {
        console.error('[AuthProvider] ❌ Token error:', error.message);
        return null;
      }
    });

    // Log state
    if (process.env.NODE_ENV === 'development') {
      console.log('[AuthProvider] Init:', {
        hasAccounts: accounts.length > 0,
        inProgress
      });
    }
  }, [instance, accounts, inProgress]);

  return children;
};
