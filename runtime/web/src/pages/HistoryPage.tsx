import { useEffect, useState } from "react";
import { Clock, Search, Eye, Download, Share2 } from "lucide-react";

interface RunMeta {
  run_id: string;
  target: string;
  date: string;
  total: number;
  passed: number;
  failed: number;
  duration_s: number;
  confidence: number;
}

const BASE = (import.meta as any).env?.VITE_API_BASE || "http://localhost:8800";

export default function HistoryPage() {
  const [runs, setRuns] = useState<RunMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetch(`${BASE}/history`)
      .then((r) => r.json())
      .then((data) => setRuns(data.runs || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = runs.filter(
    (r) => !search || r.target?.toLowerCase().includes(search.toLowerCase()) || r.run_id.includes(search)
  );

  const toggleSelect = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id); else next.add(id);
    if (next.size > 2) return; // max 2 for compare
    setSelected(next);
  };

  const exportBundle = async () => {
    const toExport = Array.from(selected);
    const bundle: Record<string, any> = {};
    for (const id of toExport) {
      try {
        const r = await fetch(`${BASE}/report/${id}`);
        if (r.ok) bundle[id] = await r.json();
      } catch {}
    }
    const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `tagent-bundle-${toExport.join("-")}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Clock className="w-5 h-5" /> Test History
        </h2>
        <div className="flex gap-2">
          {selected.size === 2 && (
            <button onClick={exportBundle} className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg hover:bg-slate-50">
              <Share2 className="w-4 h-4" /> Export & Compare
            </button>
          )}
        </div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by target or run ID..."
          className="w-full pl-9 pr-4 py-2 border rounded-lg text-sm"
        />
      </div>

      {loading ? (
        <p className="text-sm text-slate-400">Loading history...</p>
      ) : filtered.length === 0 ? (
        <div className="p-8 text-center border rounded-lg bg-slate-50">
          <Clock className="w-10 h-10 text-slate-300 mx-auto mb-2" />
          <p className="text-slate-500">No test history yet</p>
          <p className="text-xs text-slate-400">Completed test runs will appear here automatically</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((run) => (
            <div
              key={run.run_id}
              className={`flex items-center gap-3 px-4 py-3 border rounded-lg hover:bg-slate-50 cursor-pointer transition ${selected.has(run.run_id) ? "border-blue-400 bg-blue-50 ring-1 ring-blue-400" : ""}`}
              onClick={() => toggleSelect(run.run_id)}
            >
              <input type="checkbox" checked={selected.has(run.run_id)} onChange={() => {}} className="shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-sm truncate">{run.target || "Untitled"}</div>
                <div className="text-xs text-slate-400">{run.date} · {run.duration_s}s</div>
              </div>
              <div className="flex items-center gap-3 text-sm shrink-0">
                <span className="text-green-600">{run.passed}/{run.total} pass</span>
                {run.failed > 0 && <span className="text-red-600">{run.failed} fail</span>}
                <a
                  href={`#/runs/${run.run_id}/report`}
                  onClick={(e) => e.stopPropagation()}
                  className="text-blue-600 hover:underline flex items-center gap-1"
                >
                  <Eye className="w-3.5 h-3.5" /> View
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      {filtered.length > 0 && (
        <p className="text-xs text-slate-400">
          {selected.size === 0 ? "Select 2 runs to compare and export" : selected.size === 2 ? "2 selected — click Export & Compare" : `Select 1 more to compare (${2 - selected.size()} left)`}
        </p>
      )}
    </div>
  );
}
