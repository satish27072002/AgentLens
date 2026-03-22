import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * Redirects unauthenticated users to /login landing page.
 *
 * Does NOT auto-call loginWithRedirect() here — that causes blank pages
 * because Auth0 SDK may still be initializing when this first renders.
 * Instead, redirect to /login where the user clicks the button explicitly.
 */
export default function ProtectedRoute({ children }) {
  const { user, loading, isAuthenticated } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  // Not authenticated → go to login landing page
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Authenticated but backend sync still loading
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-3" />
          <p className="text-sm text-gray-400">Setting up your account...</p>
        </div>
      </div>
    );
  }

  return children;
}
