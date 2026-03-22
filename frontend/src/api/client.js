/**
 * API client — wraps fetch calls to the backend.
 *
 * Token management:
 * - OLD: Read JWT from localStorage (self-managed)
 * - NEW: Token is set by AuthContext after Auth0 login via setToken()
 *
 * The token is an Auth0-issued access token (RS256 JWT).
 * The backend validates it using Auth0's public keys.
 */

// In production (DigitalOcean/Azure), frontend and backend share the same domain
// via path-based routing (/api/* → backend). So API_URL can be empty string.
// In local dev, it points to localhost:8000.
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  constructor() {
    this.baseUrl = API_URL;
    this.token = null;
  }

  /**
   * Called by AuthContext after Auth0 login.
   * Sets the access token for all subsequent API requests.
   */
  setToken(token) {
    this.token = token;
  }

  async request(path, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Auth (simplified — no signup/login, Auth0 handles those)
  getMe() {
    return this.request('/api/auth/me');
  }

  updateProfile(data) {
    return this.request('/api/auth/me', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  getFirstApiKey() {
    return this.request('/api/auth/api-key');
  }

  // Executions
  getExecutions(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/api/executions${query ? `?${query}` : ''}`);
  }

  getExecution(id) {
    return this.request(`/api/executions/${id}`);
  }

  // Stats
  getStats() {
    return this.request('/api/stats');
  }

  // API Keys
  getApiKeys() {
    return this.request('/api/keys');
  }

  createApiKey(name) {
    return this.request('/api/keys', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  }

  deleteApiKey(id) {
    return this.request(`/api/keys/${id}`, { method: 'DELETE' });
  }
}

export const api = new ApiClient();
