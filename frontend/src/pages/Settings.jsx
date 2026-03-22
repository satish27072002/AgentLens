import { useState, useEffect } from 'react';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { Plus, Trash2, Key, Copy, Check } from 'lucide-react';

export default function Settings() {
  const { user } = useAuth();
  const [keys, setKeys] = useState([]);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyValue, setNewKeyValue] = useState('');
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [copied, setCopied] = useState('');

  useEffect(() => {
    loadKeys();
  }, []);

  const loadKeys = () => {
    api.getApiKeys()
      .then(setKeys)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  const createKey = async (e) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    setCreating(true);
    try {
      const result = await api.createApiKey(newKeyName.trim());
      setNewKeyValue(result.key);
      setNewKeyName('');
      loadKeys();
    } catch (err) {
      console.error(err);
    } finally {
      setCreating(false);
    }
  };

  const deleteKey = async (id) => {
    try {
      await api.deleteApiKey(id);
      setKeys(keys.filter((k) => k.id !== id));
    } catch (err) {
      console.error(err);
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    setTimeout(() => setCopied(''), 2000);
  };

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-white mb-6">Settings</h1>

      {/* Profile */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <h2 className="text-lg font-semibold text-white mb-3">Profile</h2>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-400">Name</span>
            <span className="text-white">{user?.name || '—'}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-400">Email</span>
            <span className="text-white">{user?.email}</span>
          </div>
        </div>
      </div>

      {/* Create API Key */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <h2 className="text-lg font-semibold text-white mb-3">Create API Key</h2>
        <form onSubmit={createKey} className="flex gap-2">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key name (e.g. production)"
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={creating || !newKeyName.trim()}
            className="flex items-center gap-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create
          </button>
        </form>

        {newKeyValue && (
          <div className="mt-3 bg-green-500/10 border border-green-500/20 rounded-lg p-3">
            <p className="text-xs text-green-400 mb-2">
              Copy this key now — it won't be shown again.
            </p>
            <div className="flex items-center gap-2">
              <code className="flex-1 text-sm text-green-300 font-mono break-all">{newKeyValue}</code>
              <button
                onClick={() => copyToClipboard(newKeyValue, 'new')}
                className="p-1.5 rounded bg-gray-800 hover:bg-gray-700 transition-colors"
              >
                {copied === 'new' ? (
                  <Check className="w-4 h-4 text-green-400" />
                ) : (
                  <Copy className="w-4 h-4 text-gray-400" />
                )}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Existing API Keys */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-3">API Keys</h2>
        {loading ? (
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500 mx-auto" />
        ) : keys.length === 0 ? (
          <p className="text-sm text-gray-500">No API keys.</p>
        ) : (
          <div className="space-y-2">
            {keys.map((key) => (
              <div
                key={key.id}
                className="flex items-center justify-between bg-gray-800 border border-gray-700 rounded-lg px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <Key className="w-4 h-4 text-gray-500" />
                  <div>
                    <div className="text-sm text-white">{key.name}</div>
                    <div className="text-xs text-gray-500 font-mono">{key.key_preview}</div>
                  </div>
                </div>
                <button
                  onClick={() => deleteKey(key.id)}
                  className="p-1.5 rounded hover:bg-red-500/10 text-gray-500 hover:text-red-400 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
