import { useState, useEffect } from 'react';
import { api } from '../api/client';
import StatCard from '../components/StatCard';
import ExecutionTable from '../components/ExecutionTable';
import { Activity, CheckCircle2, Clock, Cpu } from 'lucide-react';

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [executions, setExecutions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getStats(), api.getExecutions({ limit: 20 })])
      .then(([statsData, execData]) => {
        setStats(statsData);
        setExecutions(execData.executions || []);
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

  return (
    <div>
      <h1 className="text-2xl font-bold text-white mb-6">Dashboard</h1>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={Activity}
          label="Total Executions"
          value={stats?.total_executions ?? 0}
        />
        <StatCard
          icon={CheckCircle2}
          label="Success Rate"
          value={stats?.total_executions ? `${Math.round((stats.successful_executions / stats.total_executions) * 100)}%` : '—'}
          sub={`${stats?.successful_executions ?? 0} successful`}
        />
        <StatCard
          icon={Clock}
          label="Avg Duration"
          value={stats?.avg_duration_ms ? `${(stats.avg_duration_ms / 1000).toFixed(2)}s` : '—'}
        />
        <StatCard
          icon={Cpu}
          label="Total LLM Calls"
          value={stats?.total_llm_calls ?? 0}
          sub={stats?.total_cost ? `$${stats.total_cost.toFixed(4)} total cost` : undefined}
        />
      </div>

      {/* Recent Executions */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
        <h2 className="text-lg font-semibold text-white mb-4">Recent Executions</h2>
        <ExecutionTable executions={executions} />
      </div>
    </div>
  );
}
