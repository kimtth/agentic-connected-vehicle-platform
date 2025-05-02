/**
 * Microsoft Authentication Library (MSAL) configuration
 */

import { PublicClientApplication, InteractionType, BrowserAuthError } from '@azure/msal-browser';

// MSAL configuration
const msalConfig = {
  auth: {
    clientId: process.env.REACT_APP_AZURE_CLIENT_ID || '',
    authority: process.env.REACT_APP_AZURE_AUTHORITY || 'https://login.microsoftonline.com/common',
    redirectUri: process.env.REACT_APP_AZURE_REDIRECT_URI || window.location.origin,
    postLogoutRedirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'sessionStorage', // Options: 'sessionStorage' or 'localStorage'
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (!containsPii) {
          switch (level) {
            case 0:
              console.error(message);
              return;
            case 1:
              console.warn(message);
              return;
            case 2:
              console.info(message);
              return;
            case 3:
              console.debug(message);
              return;
            default:
              console.log(message);
              return;
          }
        }
      },
      piiLoggingEnabled: false,
      logLevel: 2, // Error: 0, Warning: 1, Info: 2, Verbose: 3
    },
  },
};

// MSAL instance
export const msalInstance = new PublicClientApplication(msalConfig);

// Check if instance is initialized
export const isMsalInitialized = () => {
  return msalInstance && msalInstance.getAllAccounts().length > 0;
};

// Login with popup
export const login = async () => {
  try {
    const response = await msalInstance.loginPopup({
      scopes: ['openid', 'profile', 'email'],
      prompt: 'select_account',
    });
    
    if (response) {
      return response.account;
    }
    
    return null;
  } catch (error) {
    console.error('Error during login:', error);
    throw error;
  }
};

// Logout 
export const logout = async () => {
  try {
    await msalInstance.logoutPopup();
  } catch (error) {
    console.error('Error during logout:', error);
    throw error;
  }
};

// Get active account
export const getActiveAccount = () => {
  const accounts = msalInstance.getAllAccounts();
  
  if (accounts.length === 0) {
    return null;
  }
  
  if (accounts.length === 1) {
    return accounts[0];
  }
  
  // If multiple accounts, return the first one for now
  // In a real application, you might want to let the user choose
  return accounts[0];
};

// Get access token
export const getAccessToken = async (scopes) => {
  const account = getActiveAccount();
  
  if (!account) {
    throw new Error('No active account');
  }
  
  try {
    const response = await msalInstance.acquireTokenSilent({
      account,
      scopes,
    });
    
    return response.accessToken;
  } catch (error) {
    if (error instanceof BrowserAuthError) {
      // Fallback to interactive login if silent acquisition fails
      try {
        const response = await msalInstance.acquireTokenPopup({
          account,
          scopes,
        });
        
        return response.accessToken;
      } catch (interactiveError) {
        console.error('Error during interactive token acquisition:', interactiveError);
        throw interactiveError;
      }
    }
    
    console.error('Error during token acquisition:', error);
    throw error;
  }
};
