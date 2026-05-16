import { useEffect, useState } from "react";
import { BarChart3, TrendingUp, AlertTriangle, CheckCircle2, Clock, Activity } from "lucide-react";

interface RunSummary {
  run_id: string;
  target: string;
  date: string;
  total: number;
  passed: number;
  failed: number;
  confidence: number;
  duration_s: number;
}

interface DashboardData {
  total_runs: number;
  avg_pass_rate: number;
  avg_confidence: number;
  total_test_cases: number;
  recent_runs: RunSummary[];
  top_failures: { expert: string; fail_count: number }[];
}

const BASE = (import.meta as any).env?.VITE_API_BASE || "http://localhost:8800";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${BASE}/dashboard`)
      .then((r) => { if (!r.ok) throw new Error("No data yet"); return r.json(); })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-6"><Activity className="w-5 h-5 animate-spin inline mr-2" />Loading dashboard...</div>;
  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto p-6 space-y-4">
        <h2 className="text-xl font-semibold flex items-center gap-2"><BarChart3 className="w-5 h-5" /> AI Quality Dashboard</h2>
        <div className="p-8 text-center border rounded-lg bg-slate-50">
          <BarChart3 className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500">No test runs yet. Start a test to populate quality metrics.</p>
          <p className="text-xs text-slate-400 mt-2">Metrics are collected from completed test runs in your workspace.</p>
        </div>
      </div>
    );
  }

  const passRate = data.avg_pass_rate * 100;
  const confRate = data.avg_confidence * 100;

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <h2 className="text-xl font-semibold flex items-center gap-2">
        <BarChart3 className="w-5 h-5" /> AI Quality Dashboard
      </h2>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Total Runs", value: data.total_runs, icon: <Activity className="w-4 h-4" />, color: "bg-blue-50 border-blue-200" },
          { label: "Pass Rate", value: `${passRate.toFixed(1)}%`, icon: <CheckCircle2 className="w-4 h-4" />, color: passRate >= 80 ? "bg-green-50 border-green-200" : "bg-yellow-50 border-yellow-200" },
          { label: "Avg Confidence", value: `${confRate.toFixed(1)}%`, icon: <TrendingUp className="w-4 h-4" />, color: confRate >= 70 ? "bg-green-50 border-green-200" : "bg-yellow-50 border-yellow-200" },
          { label: "Test Cases", value: data.total_test_cases, icon: <Clock className="w-4 h-4" />, color: "bg-purple-50 border-purple-200" },
        ].map((kpi) => (
          <div key={kpi.label} className={`p-4 rounded-lg border ${kpi.color}`}>
            <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">{kpi.icon}{kpi.label}</div>
            <div className="text-2xl font-bold">{kpi.value}</div>
          </div>
        ))}
      </div>

      {/* Recent Runs */}
      <section>
        <h3 className="text-sm font-medium text-slate-600 mb-3">Recent Test Runs</h3>
        <div className="space-y-2">
          {data.recent_runs.map((run) => (
            <div key={run.run_id} className="flex items-center justify-between px-4 py-3 border rounded-lg hover:bg-slate-50">
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm truncate">{run.target || run.run_id}</div>
                <div className="text-xs text-slate-400">{run.date}</div>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span className="text-green-600">{run.passed} pass</span>
                {run.failed > 0 && <span className="text-red-600">{run.failed} fail</span>}
                <span className="text-slate-400">{(run.confidence * 100).toFixed(0)}% conf</span>
                <a href={`#/runs/${run.run_id}/report`} className="text-blue-600 hover:underline text-xs">Report →</a>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Top Failures */}
      {data.top_failures.length > 0 && (
        <section>
          <h3 className="text-sm font-medium text-slate-600 mb-3 flex items-center gap-1.5">
            <AlertTriangle className="w-4 h-4 text-amber-500" /> Top Failing Areas
          </h3>
          <div className="space-y-1.5">
            {data.top_failures.map((f) => (
              <div key={f.expert} className="flex items-center justify-between px-3 py-2 border rounded text-sm">
                <span>{f.expert}</span>
                <span className="text-red-600 font-medium">{f.fail_count} failures</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
