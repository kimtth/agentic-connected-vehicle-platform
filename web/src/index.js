import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import AppRouter from './AppRouter';
import { MsalProvider } from '@azure/msal-react';
import { PublicClientApplication, EventType } from '@azure/msal-browser';
import { msalConfig, isClientIdConfigured } from './auth/msalConfig';

const root = ReactDOM.createRoot(document.getElementById('root'));

// Check if client ID is configured
if (!isClientIdConfigured()) {
  root.render(
    <div style={{ padding: 32, fontFamily: 'system-ui, sans-serif', color: '#444', maxWidth: 560 }}>
      <h3 style={{ marginTop: 0 }}>Authentication not configured</h3>
      <p style={{ fontSize: 14, lineHeight: 1.5 }}>
        The application requires valid Azure AD configuration to function.
      </p>
      <ul style={{ fontSize: 13, marginTop: 16, paddingLeft: 18 }}>
        <li>Set REACT_APP_AZURE_CLIENT_ID to your SPA App Registration client GUID</li>
        <li>Set REACT_APP_AZURE_TENANT_ID to your tenant ID</li>
        <li>Optionally set REACT_APP_AZURE_SCOPE for API access (e.g., api://YOUR-API-APP-ID-URI/access_as_user)</li>
        <li>Restart the development server after updating .env</li>
      </ul>
    </div>
  );
} else {
  /**
   * MSAL should be instantiated outside of the component tree to prevent it from being re-instantiated on re-renders.
   * For more, visit: https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-react/docs/getting-started.md
   */
  const msalInstance = new PublicClientApplication(msalConfig);

  // Default to using the first account if no account is active on page load
  if (!msalInstance.getActiveAccount() && msalInstance.getAllAccounts().length > 0) {
    // Account selection logic is app dependent. Adjust as needed for different use cases.
    msalInstance.setActiveAccount(msalInstance.getAllAccounts()[0]);
  }

  // Listen for sign-in event and set active account
  msalInstance.addEventCallback((event) => {
    if (event.eventType === EventType.LOGIN_SUCCESS && event.payload?.account) {
      const account = event.payload.account;
      msalInstance.setActiveAccount(account);
    }

    if (event.eventType === EventType.LOGIN_FAILURE) {
      console.error('Login failed:', event.error);
    }
  });

  root.render(
    <React.StrictMode>
      <MsalProvider instance={msalInstance}>
        <AppRouter />
      </MsalProvider>
    </React.StrictMode>
  );
}