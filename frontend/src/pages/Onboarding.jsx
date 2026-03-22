import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Copy, Check, ArrowRight } from 'lucide-react';

export default function Onboarding() {
  const navigate = useNavigate();
  const [apiKey, setApiKey] = useState('');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // Fetch the full API key (only shown during onboarding)
    api.getFirstApiKey().then((data) => {
      if (data.api_key) setApiKey(data.api_key);
    });
  }, []);

  const copyKey = () => {
    navigator.clipboard.writeText(apiKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const setupCode = `pip install agentlens

# In your agent code:
from agentlens import AgentLens

AgentLens.init(
    api_key="${apiKey || 'your-api-key'}",
    endpoint="http://localhost:8000"
)

with AgentLens.execution("MyAgent"):
    # Your agent logic here
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Hello"}]
    )

AgentLens.shutdown()`;

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-bold text-white mb-2">Welcome to AgentLens</h1>
      <p className="text-gray-400 mb-8">Get started by integrating the SDK into your AI agent.</p>

      {/* API Key */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <h2 className="text-sm font-medium text-gray-300 mb-3">Your API Key</h2>
        <div className="flex items-center gap-2">
          <code className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-green-400 font-mono">
            {apiKey || 'Loading...'}
          </code>
          <button
            onClick={copyKey}
            className="p-2 rounded-lg bg-gray-800 border border-gray-700 hover:border-gray-600 transition-colors"
          >
            {copied ? (
              <Check className="w-4 h-4 text-green-400" />
            ) : (
              <Copy className="w-4 h-4 text-gray-400" />
            )}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          This key was auto-generated for you. You can manage keys in Settings.
        </p>
      </div>

      {/* Setup Instructions */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <h2 className="text-sm font-medium text-gray-300 mb-3">Quick Setup</h2>
        <pre className="bg-gray-800 border border-gray-700 rounded-lg p-4 text-sm text-gray-300 font-mono overflow-x-auto whitespace-pre">
          {setupCode}
        </pre>
      </div>

      <button
        onClick={() => navigate('/dashboard')}
        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
      >
        Go to Dashboard
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}
