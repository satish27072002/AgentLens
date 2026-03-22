import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { ArrowLeft, CheckCircle2, XCircle, Clock, Cpu, Wrench } from 'lucide-react';

const statusConfig = {
  completed: { icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-400/10', label: 'Completed' },
  failed: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-400/10', label: 'Failed' },
  running: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-400/10', label: 'Running' },
};

export default function ExecutionPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [execution, setExecution] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    api.getExecution(id)
      .then(setExecution)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-red-400 mb-4">{error}</p>
        <button onClick={() => navigate('/dashboard')} className="text-blue-400 text-sm hover:underline">
          Back to Dashboard
        </button>
      </div>
    );
  }

  const config = statusConfig[execution.status] || statusConfig.running;
  const StatusIcon = config.icon;

  return (
    <div>
      {/* Header */}
      <button
        onClick={() => navigate('/dashboard')}
        className="flex items-center gap-1 text-sm text-gray-400 hover:text-white mb-4 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back
      </button>

      <div className="flex items-center gap-4 mb-6">
        <h1 className="text-2xl font-bold text-white">{execution.agent_name}</h1>
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${config.color} ${config.bg}`}>
          <StatusIcon className="w-3 h-3" />
          {config.label}
        </span>
      </div>

      {/* Metadata */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <MetaCard label="Duration" value={execution.duration_ms ? `${(execution.duration_ms / 1000).toFixed(2)}s` : '—'} />
        <MetaCard label="Started" value={new Date(execution.started_at).toLocaleString()} />
        <MetaCard label="LLM Calls" value={execution.llm_calls?.length ?? 0} />
        <MetaCard label="Tool Calls" value={execution.tool_calls?.length ?? 0} />
      </div>

      {/* Error */}
      {execution.error_message && (
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 mb-6">
          <h3 className="text-sm font-medium text-red-400 mb-1">Error</h3>
          <pre className="text-xs text-red-300 font-mono whitespace-pre-wrap">{execution.error_message}</pre>
        </div>
      )}

      {/* LLM Calls */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 mb-6">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-white mb-4">
          <Cpu className="w-4 h-4 text-blue-400" />
          LLM Calls ({execution.llm_calls?.length ?? 0})
        </h2>
        {execution.llm_calls?.length > 0 ? (
          <div className="space-y-3">
            {execution.llm_calls.map((call, i) => (
              <div key={call.id || i} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-white">{call.model}</span>
                  <span className="text-xs text-gray-500">{call.duration_ms ? `${(call.duration_ms / 1000).toFixed(2)}s` : ''}</span>
                </div>
                <div className="flex gap-4 text-xs text-gray-400">
                  <span>Prompt: {call.prompt_tokens ?? '—'} tokens</span>
                  <span>Completion: {call.completion_tokens ?? '—'} tokens</span>
                  {call.cost != null && <span>Cost: ${call.cost.toFixed(6)}</span>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">No LLM calls recorded.</p>
        )}
      </div>

      {/* Tool Calls */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="flex items-center gap-2 text-lg font-semibold text-white mb-4">
          <Wrench className="w-4 h-4 text-purple-400" />
          Tool Calls ({execution.tool_calls?.length ?? 0})
        </h2>
        {execution.tool_calls?.length > 0 ? (
          <div className="space-y-3">
            {execution.tool_calls.map((call, i) => (
              <div key={call.id || i} className="bg-gray-800 border border-gray-700 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-white">{call.tool_name}</span>
                  <span className="text-xs text-gray-500">{call.duration_ms ? `${(call.duration_ms / 1000).toFixed(2)}s` : ''}</span>
                </div>
                {call.error_message && (
                  <p className="text-xs text-red-400 mt-1">{call.error_message}</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-500">No tool calls recorded.</p>
        )}
      </div>
    </div>
  );
}

function MetaCard({ label, value }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-lg p-3">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      <div className="text-sm text-white font-medium">{value}</div>
    </div>
  );
}
