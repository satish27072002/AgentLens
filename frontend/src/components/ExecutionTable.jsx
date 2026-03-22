import { useNavigate } from 'react-router-dom';
import { CheckCircle2, XCircle, Clock } from 'lucide-react';

const statusConfig = {
  completed: { icon: CheckCircle2, color: 'text-green-400', bg: 'bg-green-400/10' },
  failed: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-400/10' },
  running: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
};

function StatusBadge({ status }) {
  const config = statusConfig[status] || statusConfig.running;
  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs ${config.color} ${config.bg}`}>
      <Icon className="w-3 h-3" />
      {status}
    </span>
  );
}

export default function ExecutionTable({ executions }) {
  const navigate = useNavigate();

  if (executions.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p className="text-sm">No executions yet.</p>
        <p className="text-xs mt-1">Send traces from the SDK to see them here.</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-800 text-gray-500 text-left">
            <th className="pb-3 font-medium">Agent</th>
            <th className="pb-3 font-medium">Status</th>
            <th className="pb-3 font-medium">Duration</th>
            <th className="pb-3 font-medium">Tokens</th>
            <th className="pb-3 font-medium">Time</th>
          </tr>
        </thead>
        <tbody>
          {executions.map((exec) => (
            <tr
              key={exec.id}
              onClick={() => navigate(`/executions/${exec.id}`)}
              className="border-b border-gray-800/50 hover:bg-gray-800/30 cursor-pointer transition-colors"
            >
              <td className="py-3 text-white font-medium">{exec.agent_name}</td>
              <td className="py-3">
                <StatusBadge status={exec.status} />
              </td>
              <td className="py-3 text-gray-400">
                {exec.duration_ms ? `${(exec.duration_ms / 1000).toFixed(2)}s` : '—'}
              </td>
              <td className="py-3 text-gray-400">{exec.total_tokens?.toLocaleString() ?? 0}</td>
              <td className="py-3 text-gray-500">
                {new Date(exec.started_at).toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
