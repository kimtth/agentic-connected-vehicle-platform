import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import AppRouter from './AppRouter';
import { MsalProvider } from '@azure/msal-react';
import { EventType } from '@azure/msal-browser';
import { isClientIdConfigured, msalInstance, clientIdIssue } from './auth/msalConfig';

const root = ReactDOM.createRoot(document.getElementById('root'));
let errorRendered = false; // prevent double renders

function renderAuthError(title, body, extra) {
  if (errorRendered) return;
  errorRendered = true;
  root.render(
    <div style={{ padding: 32, fontFamily: 'system-ui, sans-serif', color: '#333', maxWidth: 680 }}>
      <h3 style={{ marginTop: 0, color: '#b00020' }}>{title}</h3>
      <div style={{ fontSize: 14, lineHeight: 1.5 }}>{body}</div>
      {extra}
    </div>
  );
}

// Check if client ID is configured
if (!isClientIdConfigured()) {
  root.render(
    <div style={{ padding: 32, fontFamily: 'system-ui, sans-serif', color: '#444', maxWidth: 560 }}>
      <h3 style={{ marginTop: 0 }}>Authentication not configured</h3>
      <p style={{ fontSize: 14, lineHeight: 1.5 }}>
        {clientIdIssue}
      </p>
      <ul style={{ fontSize: 13, marginTop: 16, paddingLeft: 18 }}>
        <li>Frontend must use the SPA App Registration client GUID (not the api:// Application ID URI).</li>
        <li>Set REACT_APP_AZURE_CLIENT_ID and (optionally) REACT_APP_AZURE_SCOPE in web/.env then restart dev server.</li>
        <li>Example scope format: api://YOUR-API-APP-ID-URI/access_as_user</li>
      </ul>
      <code style={{ display: 'block', background: '#f5f5f5', padding: 8, fontSize: 12, marginTop: 12 }}>
        REACT_APP_AZURE_CLIENT_ID=&lt;spa-client-guid&gt;{'\n'}
        REACT_APP_AZURE_SCOPE=api://&lt;api-app-id-uri&gt;/access_as_user
      </code>
    </div>
  );
} else {
  msalInstance.addEventCallback((event) => {
    if (event.eventType === EventType.LOGIN_SUCCESS && event.payload?.account) {
      msalInstance.setActiveAccount(event.payload.account);
    }
    if (event.eventType === EventType.LOGIN_FAILURE) {
      const msg = (event.error?.errorMessage || event.error?.message || '').toLowerCase();
      const isInvalidClient = msg.includes('invalid_client');
      if (isInvalidClient) {
        renderAuthError(
          'Sign-in failed: invalid_client',
          <>
            The Azure AD authorization server rejected the application (invalid_client). This usually means:
            <ul style={{ marginTop: 12, paddingLeft: 18 }}>
              <li>Incorrect SPA Client ID (must be the GUID of the Public client app registration, not the API Application ID URI).</li>
              <li>Mismatched redirect URI (must exactly match one in the SPA app registration, including port and trailing slash).</li>
              <li>Environment variable not loaded (verify REACT_APP_AZURE_CLIENT_ID at build/runtime).</li>
              <li>App registration not granted (app might be disabled or deleted).</li>
            </ul>
          </>,
          <div style={{ marginTop: 16 }}>
            <code style={{ whiteSpace: 'pre', background: '#f5f5f5', padding: 8, fontSize: 12, display: 'block' }}>
              {`Ensure .env contains:
              REACT_APP_AZURE_CLIENT_ID=<spa-client-guid>
              REACT_APP_AZURE_SCOPE=api://<api-app-id-uri>/access_as_user

              Azure Portal > App registrations > (Your SPA) > Overview:
              - Copy "Application (client) ID" into REACT_APP_AZURE_CLIENT_ID
              Azure Portal > App registrations > (Your API) > Expose an API:
              - Use its Application ID URI in REACT_APP_AZURE_SCOPE
              `}
            </code>
            <details style={{ marginTop: 12 }}>
              <summary style={{ cursor: 'pointer' }}>Raw error</summary>
              <pre style={{ background: '#fafafa', padding: 8, fontSize: 12 }}>{event.error?.errorMessage || event.error?.message}</pre>
            </details>
          </div>
        );
      } else {
        renderAuthError(
          'Sign-in failed',
          <div>
            An authentication error occurred. Review details below and browser console.
            <details style={{ marginTop: 12 }}>
              <summary style={{ cursor: 'pointer' }}>Error details</summary>
              <pre style={{ background: '#fafafa', padding: 8, fontSize: 12 }}>
                {(event.error?.name || 'Error') + ': ' + (event.error?.errorMessage || event.error?.message || 'Unknown')}
              </pre>
            </details>
          </div>
        );
      }
    }
  });

  function renderApp() {
    if (errorRendered) return; // don't mount app if a fatal auth error already rendered
    root.render(
      <React.StrictMode>
        <MsalProvider instance={msalInstance}>
          <AppRouter />
        </MsalProvider>
      </React.StrictMode>
    );
  }

  // Initialize MSAL
  msalInstance.initialize()
    .then(() => {
      const accounts = msalInstance.getAllAccounts();
      if (accounts.length && !msalInstance.getActiveAccount()) {
        msalInstance.setActiveAccount(accounts[0]);
      }
      renderApp();
    })
    .catch((e) => {
      console.error('MSAL initialization failed:', e);
      root.render(
        <div style={{ padding: 24, fontFamily: 'sans-serif' }}>
          <h3 style={{ color: '#c00' }}>MSAL initialization failed</h3>
          <p>Check browser console for details.</p>
          <details>
            <summary>Error details</summary>
            <pre style={{ background: '#f5f5f5', padding: '8px', fontSize: '12px' }}>
              {e.toString()}
            </pre>
          </details>
        </div>
      );
    });
}