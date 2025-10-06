import { LogLevel, PublicClientApplication } from '@azure/msal-browser';

// Get configuration from environment
const clientId = process.env.REACT_APP_AZURE_CLIENT_ID || '';
const tenantId = process.env.REACT_APP_AZURE_TENANT_ID || 'common';

/**
 * Configuration object to be passed to MSAL instance on creation.
 * For a full list of MSAL.js configuration parameters, visit:
 * https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-browser/docs/configuration.md
 */
export const msalConfig = {
  auth: {
    clientId: clientId,
    authority: `https://login.microsoftonline.com/${tenantId}`,
    redirectUri: window.location.origin,
    postLogoutRedirectUri: window.location.origin,
    navigateToLoginRequestUrl: false,
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) {
          return;
        }
        switch (level) {
          case LogLevel.Error:
            console.error(message);
            return;
          case LogLevel.Info:
            console.info(message);
            return;
          case LogLevel.Verbose:
            console.debug(message);
            return;
          case LogLevel.Warning:
            console.warn(message);
            return;
          default:
            return;
        }
      },
      piiLoggingEnabled: false,
      logLevel: LogLevel.Warning,
    },
  },
};

/**
 * Scopes you add here will be prompted for user consent during sign-in.
 * By default, MSAL.js will add OIDC scopes (openid, profile, email) to any login request.
 * For more information about OIDC scopes, visit: 
 * https://docs.microsoft.com/en-us/azure/active-directory/develop/v2-permissions-and-consent#openid-connect-scopes
 */
export const loginRequest = {
  scopes: [],
};

/**
 * Scopes for acquiring access token for API calls
 * Uses the backend API scope if configured, otherwise empty array
 */
const backendScope = process.env.REACT_APP_AZURE_SCOPE;
export const tokenRequest = {
  scopes: backendScope ? [backendScope] : [],
};

// Validation helpers
export const isClientIdConfigured = () => {
  const invalidValues = [
    '00000000-0000-0000-0000-000000000000',
    'MISSING_CLIENT_ID',
    'YOUR_CLIENT_ID_HERE',
    '<your-client-id>',
    'placeholder',
  ];
  
  return clientId && 
         clientId.trim().length > 0 && 
         !invalidValues.includes(clientId) &&
         /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(clientId);
};

/**
 * Singleton MSAL instance to prevent multiple instances with same client ID.
 * This prevents the "already an instance of MSAL.js in the window" warning.
 */
let msalInstance = null;

/**
 * Get or create the singleton MSAL instance
 * @returns {PublicClientApplication} MSAL instance
 */
export function getMsalInstance() {
  if (!msalInstance && isClientIdConfigured()) {
    msalInstance = new PublicClientApplication(msalConfig);
    
    // Initialize MSAL instance (required before use)
    msalInstance.initialize().catch(error => {
      console.error('[MSAL] Failed to initialize:', error);
    });
  }
  
  return msalInstance;
}

/**
 * Acquire an access token silently, or interactively if required
 * Uses the backend API scope configured in REACT_APP_AZURE_SCOPE
 * @param {PublicClientApplication} msalInstance - MSAL instance from useMsal hook
 * @param {Object} account - Active account from useMsal hook
 * @returns {Promise<string|null>} Access token or null
 */
export async function acquireAccessToken(msalInstance, account) {
  if (!account) {
    console.warn('[MSAL] No active account for token acquisition');
    return null;
  }

  const request = {
    ...tokenRequest,
    account: account,
  };

  try {
    // Try silent acquisition first
    const response = await msalInstance.acquireTokenSilent(request);
    console.log('[MSAL] ✅ Backend API token acquired silently', {
      audience: response.idTokenClaims?.aud,
      scopes: response.scopes,
    });
    return response.accessToken;
  } catch (error) {
    console.warn('[MSAL] Silent token acquisition failed:', error.message);
  
    // Check if interaction is required
    if (error.name === 'InteractionRequiredAuthError') {
      try {
        // Fallback to interactive popup
        const response = await msalInstance.acquireTokenPopup(request);
        console.log('[MSAL] ✅ Backend API token acquired via popup', {
          audience: response.idTokenClaims?.aud,
          scopes: response.scopes,
        });
        return response.accessToken;
      } catch (popupError) {
        console.error('[MSAL] ❌ Popup token acquisition failed:', popupError);
        return null;
      }
    } else {
      console.error('[MSAL] ❌ Token acquisition error:', error);
      return null;
    }
  }
}

/**
 * Get authorization header with Bearer token
 * @param {PublicClientApplication} msalInstance - MSAL instance from useMsal hook
 * @param {Object} account - Active account from useMsal hook
 * @returns {Promise<Object|null>} Authorization header object or null
 */
export async function getAuthorizationHeader(msalInstance, account) {
  const token = await acquireAccessToken(msalInstance, account);
  return token ? { Authorization: `Bearer ${token}` } : null;
}