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
    <div style={{ padding: 32, fontFamily: 'system-ui, sans-serif', color: '#555' }}>
      <h3 style={{ marginTop: 0 }}>Application not configured.</h3>
      <p style={{ fontSize: 14 }}>Authentication temporarily unavailable.</p>
    </div>
  );
} else {
  const msalInstance = new PublicClientApplication(msalConfig);

  msalInstance.addEventCallback((event) => {
    if (event.eventType === EventType.LOGIN_SUCCESS && event.payload?.account) {
      msalInstance.setActiveAccount(event.payload.account);
    }
  });

  function renderApp() {
    root.render(
      <React.StrictMode>
        <MsalProvider instance={msalInstance}>
          <AppRouter />
        </MsalProvider>
      </React.StrictMode>
    );
  }

  // Initialize MSAL first (required for newer msal-browser versions)
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
