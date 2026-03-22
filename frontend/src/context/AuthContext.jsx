/**
 * Auth context — bridges Auth0 with our app.
 *
 * Flow:
 * 1. Auth0 authenticates the user (Google/GitHub/Email)
 * 2. We try to sync with the backend (/api/auth/me)
 * 3. If backend is unavailable, we fall back to Auth0 user data
 *    so the frontend still works during development
 */

import { createContext, useContext, useEffect, useState } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { api } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const {
    isAuthenticated,
    isLoading: auth0Loading,
    user: auth0User,
    loginWithRedirect,
    logout: auth0Logout,
    getAccessTokenSilently,
    error: auth0Error,
  } = useAuth0();

  const [backendUser, setBackendUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Debug logging
  useEffect(() => {
    console.log('[AuthContext] auth0Loading:', auth0Loading);
    console.log('[AuthContext] isAuthenticated:', isAuthenticated);
    console.log('[AuthContext] auth0Error:', auth0Error);
    console.log('[AuthContext] auth0User:', auth0User?.name || auth0User?.email);
  }, [auth0Loading, isAuthenticated, auth0Error, auth0User]);

  // Sync authenticated user with backend
  useEffect(() => {
    async function syncUser() {
      if (auth0Loading) return;

      if (auth0Error) {
        console.error('[AuthContext] Auth0 error:', auth0Error);
        setError(auth0Error.message);
        setLoading(false);
        return;
      }

      if (isAuthenticated && auth0User) {
        try {
          const token = await getAccessTokenSilently();
          api.setToken(token);
          const me = await api.getMe();
          setBackendUser(me);
          console.log('[AuthContext] Backend sync successful:', me.email);

          // Sync Auth0 profile data (name, email) to backend if missing
          if (auth0User.email && me.email?.endsWith('@auth0.user')) {
            const updated = await api.updateProfile({
              name: auth0User.name,
              email: auth0User.email,
            });
            setBackendUser(updated);
            console.log('[AuthContext] Profile synced:', updated.email);
          }
        } catch (err) {
          // Backend not available — use Auth0 user data as fallback
          console.warn('[AuthContext] Backend sync failed, using Auth0 data:', err.message);
          setBackendUser(null);
        }
      }

      setLoading(false);
    }

    syncUser();
  }, [isAuthenticated, auth0Loading, auth0Error, auth0User, getAccessTokenSilently]);

  const login = () => {
    console.log('[AuthContext] login() called');
    loginWithRedirect();
  };

  const loginWithGoogle = () => {
    console.log('[AuthContext] loginWithGoogle() called');
    loginWithRedirect({
      authorizationParams: { connection: 'google-oauth2' },
    });
  };

  const loginWithGitHub = () => {
    console.log('[AuthContext] loginWithGitHub() called');
    loginWithRedirect({
      authorizationParams: { connection: 'github' },
    });
  };

  const logout = () => {
    api.setToken(null);
    setBackendUser(null);
    auth0Logout({ logoutParams: { returnTo: window.location.origin + '/login' } });
  };

  // Merge backend user data with Auth0 profile data.
  // Backend has: id (database UUID), created_at
  // Auth0 has: name, email, picture (from Google/GitHub profile)
  // Auth0 profile is the source of truth for display fields.
  const user = isAuthenticated && auth0User ? {
    id: backendUser?.id || auth0User.sub,
    email: auth0User.email || backendUser?.email || auth0User.sub,
    name: auth0User.name || backendUser?.name,
    picture: auth0User.picture,
    created_at: backendUser?.created_at,
  } : null;

  // Show Auth0 errors on screen (only if not authenticated)
  if (error && !isAuthenticated) {
    return (
      <div style={{ color: '#ef4444', padding: '40px', fontFamily: 'monospace', background: '#0a0a0a', minHeight: '100vh' }}>
        <h2>Auth Error</h2>
        <p>{error}</p>
        <button
          onClick={() => { setError(null); window.location.href = '/login'; }}
          style={{ color: '#3b82f6', cursor: 'pointer', marginTop: '16px', background: 'none', border: 'none', fontSize: '14px' }}
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{
      user,
      loading: loading || auth0Loading,
      login,
      loginWithGoogle,
      loginWithGitHub,
      logout,
      isAuthenticated,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
}
