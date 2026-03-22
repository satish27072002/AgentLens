import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Auth0Provider } from '@auth0/auth0-react';
import { AuthProvider } from './context/AuthContext';
import App from './App';
import './index.css';

/**
 * Auth0Provider wraps the entire app.
 *
 * NOTE: StrictMode removed — it causes Auth0Provider to double-initialize
 * in development, which can break the OAuth redirect flow.
 */
const domain = import.meta.env.VITE_AUTH0_DOMAIN;
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID;
const audience = import.meta.env.VITE_AUTH0_AUDIENCE;

// Debug: verify env vars are loaded (visible in browser console)
console.log('[AgentLens] Auth0 domain:', domain);
console.log('[AgentLens] Auth0 clientId:', clientId ? clientId.slice(0, 6) + '...' : 'MISSING');
console.log('[AgentLens] Auth0 audience:', audience);

// Catch Auth0 error/callback params in the URL
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.get('error')) {
  console.error('[AgentLens] Auth0 redirect error:', urlParams.get('error'));
  console.error('[AgentLens] Error description:', urlParams.get('error_description'));
}
if (urlParams.get('code')) {
  console.log('[AgentLens] Auth0 authorization code received ✅');
}

if (!domain || !clientId) {
  document.getElementById('root').innerHTML = `
    <div style="color: red; padding: 40px; font-family: monospace;">
      <h2>Auth0 configuration missing!</h2>
      <p>VITE_AUTH0_DOMAIN: ${domain || 'NOT SET'}</p>
      <p>VITE_AUTH0_CLIENT_ID: ${clientId || 'NOT SET'}</p>
      <p>Check frontend/.env file</p>
    </div>
  `;
} else {
  createRoot(document.getElementById('root')).render(
    <BrowserRouter>
      <Auth0Provider
        domain={domain}
        clientId={clientId}
        authorizationParams={{
          redirect_uri: window.location.origin + '/login',
          audience: audience,
        }}
        cacheLocation="localstorage"
      >
        <AuthProvider>
          <App />
        </AuthProvider>
      </Auth0Provider>
    </BrowserRouter>
  );
}
