import { useState, useEffect } from 'react';
import { api } from '../api/client';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts';

export default function Analytics() {
  const [executions, setExecutions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getExecutions({ limit: 500 })
      .then((data) => {
        setExecutions(data.executions || []);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  // Group executions by date for the line chart
  const byDate = {};
  executions.forEach((exec) => {
    const date = new Date(exec.started_at).toLocaleDateString();
    if (!byDate[date]) byDate[date] = { date, total: 0, completed: 0, failed: 0 };
    byDate[date].total++;
    if (exec.status === 'completed') byDate[date].completed++;
    if (exec.status === 'failed') byDate[date].failed++;
  });
  const dailyData = Object.values(byDate).reverse();

  // Group by agent name for the bar chart
  const byAgent = {};
  executions.forEach((exec) => {
    if (!byAgent[exec.agent_name]) byAgent[exec.agent_name] = { agent: exec.agent_name, count: 0 };
    byAgent[exec.agent_name].count++;
  });
  const agentData = Object.values(byAgent).sort((a, b) => b.count - a.count).slice(0, 10);

  const tooltipStyle = {
    contentStyle: { backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' },
    labelStyle: { color: '#9ca3af' },
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Analytics</h1>

      {executions.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <p className="text-sm">No data yet. Send some traces to see analytics.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Executions Over Time */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="text-lg font-semibold text-white mb-4">Executions Over Time</h2>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={dailyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#6b7280" fontSize={12} />
                <YAxis stroke="#6b7280" fontSize={12} />
                <Tooltip {...tooltipStyle} />
                <Line type="monotone" dataKey="total" stroke="#3b82f6" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="completed" stroke="#22c55e" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="failed" stroke="#ef4444" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Success vs Error by Date */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="text-lg font-semibold text-white mb-4">Success vs Error</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={dailyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" stroke="#6b7280" fontSize={12} />
                <YAxis stroke="#6b7280" fontSize={12} />
                <Tooltip {...tooltipStyle} />
                <Bar dataKey="completed" fill="#22c55e" radius={[4, 4, 0, 0]} />
                <Bar dataKey="failed" fill="#ef4444" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Top Agents */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="text-lg font-semibold text-white mb-4">Top Agents</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={agentData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis type="number" stroke="#6b7280" fontSize={12} />
                <YAxis dataKey="agent" type="category" stroke="#6b7280" fontSize={12} width={120} />
                <Tooltip {...tooltipStyle} />
                <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
