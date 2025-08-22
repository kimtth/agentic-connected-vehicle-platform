/**
 * MSAL configuration
 */
import { PublicClientApplication, BrowserAuthError, InteractionRequiredAuthError } from '@azure/msal-browser';

// Get and validate client ID
const RAW_CLIENT_ID = process.env.REACT_APP_AZURE_CLIENT_ID;
const TENANT_ID = process.env.REACT_APP_AZURE_TENANT_ID;

// Validate client ID configuration
export const clientIdIssue = (() => {
  if (!RAW_CLIENT_ID) return 'REACT_APP_AZURE_CLIENT_ID is not set.';
  if (RAW_CLIENT_ID === '00000000-0000-0000-0000-000000000000' || RAW_CLIENT_ID === 'MISSING_CLIENT_ID')
    return 'REACT_APP_AZURE_CLIENT_ID still has a placeholder value.';
  if (RAW_CLIENT_ID.startsWith('api://'))
    return 'REACT_APP_AZURE_CLIENT_ID is an Application ID URI (api://...). Frontend must use the SPA app registration GUID, not the API Application ID URI.';
  if (!/^[0-9a-fA-F-]{36}$/.test(RAW_CLIENT_ID))
    return 'REACT_APP_AZURE_CLIENT_ID is not a valid GUID.';
  return null;
})();

export const isClientIdConfigured = () => clientIdIssue === null;

const API_SCOPE = process.env.REACT_APP_AZURE_SCOPE;

// New: validate API scope (common misconfig causes AADSTS650053 with scope '#')
export const apiScopeIssue = (() => {
  if (!API_SCOPE) return null;
  if (API_SCOPE.trim() === '' ) return 'REACT_APP_AZURE_SCOPE is empty.';
  if (API_SCOPE === '#') return "REACT_APP_AZURE_SCOPE resolved to '#'. Remove stray # or comments after the value in .env.";
  if (API_SCOPE.startsWith('#')) return 'REACT_APP_AZURE_SCOPE starts with # (commented out?).';
  if (/\s/.test(API_SCOPE)) return 'REACT_APP_AZURE_SCOPE contains whitespace. It must be a single scope string.';
  if (!API_SCOPE.includes('/')) return 'REACT_APP_AZURE_SCOPE missing final path segment (e.g. /access_as_user).';
  // Basic heuristic: api:// GUID style or resource URI + scope
  if (API_SCOPE.startsWith('api://')) {
    const parts = API_SCOPE.split('/');
    if (parts.length < 4 || !parts[2]) return 'REACT_APP_AZURE_SCOPE format should be api://<api-app-id-uri>/scope_name.';
  }
  return null;
})();

if (apiScopeIssue) {
  // eslint-disable-next-line no-console
  console.warn('[MSAL] Ignoring invalid API scope:', apiScopeIssue);
}

export const API_SCOPE_CONFIGURED = !!API_SCOPE && !apiScopeIssue;

// Baseline identity scopes always requested
const BASE_SCOPES = ['openid', 'profile', 'offline_access'];

// Always request identity scopes + API (if valid)
export const loginRequest = {
  scopes: [
    ...BASE_SCOPES,
    ...(API_SCOPE_CONFIGURED ? [API_SCOPE] : [])
  ]
};

if (!API_SCOPE_CONFIGURED) {
  // eslint-disable-next-line no-console
  console.warn('[MSAL] No valid API scope configured. Access tokens for backend will not include your resource. Set REACT_APP_AZURE_SCOPE=api://<api-app-id-uri>/access_as_user');
}

const msalConfig = {
  auth: {
    clientId: isClientIdConfigured() ? RAW_CLIENT_ID : '',
    authority: TENANT_ID
      ? `https://login.microsoftonline.com/${TENANT_ID}`
      : 'https://login.microsoftonline.com/common',
    redirectUri: process.env.REACT_APP_AZURE_REDIRECT_URI || window.location.origin,
    postLogoutRedirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: null,
      piiLoggingEnabled: false,
      logLevel: 0,
    },
  },
};

// Create the shared MSAL instance
export const msalInstance = new PublicClientApplication(msalConfig);

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

export async function acquireApiToken(options = {}) {
  const { forceRefresh = false, interactive = true } = options;
  const accounts = msalInstance.getAllAccounts();
  let account = accounts[0];

  if (!account && interactive) {
    try {
      const loginResult = await msalInstance.loginPopup(loginRequest);
      account = loginResult.account || msalInstance.getAllAccounts()[0];
    } catch (e) {
      console.warn('[MSAL] loginPopup failed; cannot acquire API token.', e.message);
      return null;
    }
  }
  if (!account) return null;

  if (!API_SCOPE_CONFIGURED) {
    // eslint-disable-next-line no-console
    console.warn('[MSAL] acquireApiToken called but API scope not configured.');
    return null;
  }

  const scopes = [API_SCOPE]; // API scope needed for resource access
  try {
    const r = await msalInstance.acquireTokenSilent({ account, scopes, forceRefresh });
    return r.accessToken;
  } catch (e) {
    if (e instanceof InteractionRequiredAuthError && interactive) {
      try {
        const r2 = await msalInstance.acquireTokenPopup({ account, scopes, forceRefresh });
        return r2.accessToken;
      } catch (ie) {
        console.warn('[MSAL] Interactive token acquisition failed.', ie.message);
        return null;
      }
    } else if (e instanceof BrowserAuthError) {
      console.warn('[MSAL] BrowserAuthError during silent token acquisition.', e.message);
      if (interactive) {
        try {
          const r3 = await msalInstance.acquireTokenPopup({ account, scopes, forceRefresh });
          return r3.accessToken;
        } catch {
          return null;
        }
      }
      return null;
    }
    return null;
  }
}

export async function getAuthorizationHeader(forceRefresh = false) {
  if (!API_SCOPE_CONFIGURED) return null;
  const token = await acquireApiToken({ forceRefresh, interactive: true });
  return token ? { Authorization: `Bearer ${token}` } : null;
}

export const hasApiScope = () => API_SCOPE_CONFIGURED;
export { msalConfig, API_SCOPE };