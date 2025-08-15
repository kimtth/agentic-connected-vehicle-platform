/**
 * MSAL configuration (relocated from /auth to /src/auth to satisfy CRA import rules)
 */
import { PublicClientApplication, BrowserAuthError } from '@azure/msal-browser';

// Get and validate client ID
const RAW_CLIENT_ID = process.env.REACT_APP_AZURE_CLIENT_ID;
const TENANT_ID = process.env.REACT_APP_AZURE_TENANT_ID;

// Validation helper
export const isClientIdConfigured = () => {
  return !!RAW_CLIENT_ID && 
         RAW_CLIENT_ID !== '00000000-0000-0000-0000-000000000000' &&
         RAW_CLIENT_ID !== 'MISSING_CLIENT_ID' &&
         RAW_CLIENT_ID.length === 36; // Basic GUID format check
};

if (process.env.NODE_ENV === 'development' && !isClientIdConfigured()) {
  // eslint-disable-next-line no-console
  console.warn('MSAL: REACT_APP_AZURE_CLIENT_ID not configured.');
}

// Optional API scope
const API_SCOPE = process.env.REACT_APP_AZURE_API_SCOPE;
export const loginRequest = {
  scopes: ['openid', 'profile', 'email', ...(API_SCOPE ? [API_SCOPE] : [])]
};

const msalConfig = {
  auth: {
    clientId: RAW_CLIENT_ID || '', 
    authority: TENANT_ID
      ? `https://login.microsoftonline.com/${TENANT_ID}`
      : (process.env.REACT_APP_AZURE_AUTHORITY || 'https://login.microsoftonline.com/common'),
    redirectUri: process.env.REACT_APP_AZURE_REDIRECT_URI || window.location.origin,
    postLogoutRedirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (!containsPii && process.env.NODE_ENV === 'development') {
          switch (level) {
            case 0: console.error('[MSAL]', message); return;
            case 1: console.warn('[MSAL]', message); return;
            case 2: console.info('[MSAL]', message); return;
            case 3: console.debug('[MSAL]', message); return;
            default: return;
          }
        }
      },
      piiLoggingEnabled: false,
      logLevel: process.env.NODE_ENV === 'development' ? 2 : 0,
    },
  },
};

export const msalInstance = new PublicClientApplication(msalConfig);

// NOTE: Do not call msalInstance.initialize() here; index.js performs and awaits initialization

export const getActiveAccount = () => {
  const accounts = msalInstance.getAllAccounts();
  return accounts.length ? accounts[0] : null;
};

export const getAccessToken = async (scopes) => {
  const account = getActiveAccount();
  if (!account) throw new Error('No active account');
  try {
    const r = await msalInstance.acquireTokenSilent({ account, scopes });
    return r.accessToken;
  } catch (e) {
    if (e instanceof BrowserAuthError) {
      const r = await msalInstance.acquireTokenPopup({ account, scopes });
      return r.accessToken;
    }
    throw e;
  }
};

export async function acquireApiToken() {
  const accounts = msalInstance.getAllAccounts();
  if (!accounts.length) return null;
  
  try {
    // Try silent acquisition
    const r = await msalInstance.acquireTokenSilent({
      account: accounts[0],
      scopes: loginRequest.scopes
    });
    return r.accessToken;
  } catch (silentError) {
    // If silent fails, try popup
    try {
      const r = await msalInstance.acquireTokenPopup({
        account: accounts[0],
        scopes: loginRequest.scopes
      });
      return r.accessToken;
    } catch (popupError) {
      console.debug('Token acquisition failed:', popupError.message);
      return null;
    }
  }
}

export { msalConfig };