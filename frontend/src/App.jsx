import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Onboarding from './pages/Onboarding';
import Dashboard from './pages/Dashboard';
import ExecutionPage from './pages/ExecutionPage';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';

/**
 * App routing.
 *
 * Auth0 flow:
 * 1. User visits any protected route → ProtectedRoute redirects to Auth0 login
 * 2. Auth0 authenticates → redirects back to the app with a token
 * 3. AuthContext syncs with backend (/api/auth/me) → JIT creates user if new
 * 4. User lands on Dashboard (or Onboarding if first time)
 *
 * No /signup route needed — Auth0's login page handles both login and signup.
 */
export default function App() {
  return (
    <Routes>
      {/* Public route */}
      <Route path="/login" element={<Login />} />

      {/* Protected routes — wrapped in Layout for sidebar */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/executions/:id" element={<ExecutionPage />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/settings" element={<Settings />} />
      </Route>

      {/* Default redirect — send unauthenticated users to login page */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
