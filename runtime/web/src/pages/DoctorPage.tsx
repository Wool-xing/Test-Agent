import { useEffect, useState } from "react";
import { Stethoscope, Check, X, Loader2 } from "lucide-react";

interface CheckItem {
  name: string;
  status: "pending" | "ok" | "skip" | "fail";
  detail: string;
}

export default function DoctorPage() {
  const [checks, setChecks] = useState<CheckItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    runDoctor();
  }, []);

  const runDoctor = async () => {
    setLoading(true);
    const results: CheckItem[] = [];

    // Catalog check
    try {
      const res = await fetch("http://localhost:8800/catalog");
      if (res.ok) {
        const data = await res.json();
        results.push({ name: "Catalog", status: "ok", detail: `${data.counts?.experts || 0} experts + ${data.counts?.skills || 0} skills` });
      } else {
        results.push({ name: "Catalog", status: "fail", detail: `HTTP ${res.status}` });
      }
    } catch {
      results.push({ name: "Catalog", status: "fail", detail: "Backend not reachable" });
    }

    // Health check
    try {
      const res = await fetch("http://localhost:8800/health");
      if (res.ok) {
        const data = await res.json();
        results.push({ name: "Backend", status: "ok", detail: `v${data.version}` });
      } else {
        results.push({ name: "Backend", status: "fail", detail: `HTTP ${res.status}` });
      }
    } catch {
      results.push({ name: "Backend", status: "fail", detail: "Not running — start backend first" });
    }

    // Settings check
    const provider = localStorage.getItem("tagent_provider") || "stub";
    const hasKey = !!localStorage.getItem("tagent_api_key");
    if (provider === "stub") {
      results.push({ name: "LLM Config", status: "skip", detail: "Stub mode (offline demo)" });
    } else if (!hasKey) {
      results.push({ name: "LLM Config", status: "fail", detail: `Provider: ${provider}, no API key set` });
    } else {
      results.push({ name: "LLM Config", status: "ok", detail: `Provider: ${provider}` });
    }

    setChecks(results);
    setLoading(false);
  };

  const statusIcon = (s: string) => {
    switch (s) {
      case "ok": return <Check className="w-4 h-4 text-green-600" />;
      case "fail": return <X className="w-4 h-4 text-red-600" />;
      case "skip": return <span className="text-xs text-slate-400">SKIP</span>;
      default: return <Loader2 className="w-4 h-4 animate-spin text-slate-400" />;
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Stethoscope className="w-5 h-5" /> System Check
        </h2>
        <button onClick={runDoctor} disabled={loading} className="text-sm px-3 py-1.5 border rounded-lg hover:bg-slate-50 disabled:opacity-50">
          {loading ? "Checking..." : "Re-run"}
        </button>
      </div>

      <div className="space-y-2">
        {checks.map((c) => (
          <div key={c.name} className={`flex items-center justify-between px-4 py-3 rounded-lg border ${c.status === "fail" ? "border-red-200 bg-red-50" : c.status === "ok" ? "border-green-200 bg-green-50" : "border-slate-200"}`}>
            <div>
              <div className="font-medium text-sm">{c.name}</div>
              <div className="text-xs text-slate-500">{c.detail}</div>
            </div>
            {statusIcon(c.status)}
          </div>
        ))}
      </div>

      {!loading && checks.length === 0 && (
        <p className="text-sm text-slate-400">No checks run. Click "Re-run".</p>
      )}
    </div>
  );
}
