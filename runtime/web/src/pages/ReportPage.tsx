import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { getReport } from "@/api";

function downloadJSON(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ReportPage() {
  const { run_id } = useParams<{ run_id: string }>();
  const query = useQuery({
    queryKey: ["report", run_id],
    queryFn: () => getReport(run_id!),
    enabled: !!run_id,
  });

  if (!run_id) return <p>缺少 run_id</p>;
  if (query.isLoading) return <p>加载中...</p>;
  if (query.isError)
    return (
      <p role="alert" className="text-red-600">
        加载失败:{(query.error as Error).message}
      </p>
    );

  const report = (query.data || {}) as Record<string, unknown>;
  const results = (report.results || {}) as Record<string, Record<string, unknown>>;

  return (
    <section aria-labelledby="report-heading" className="max-w-4xl">
      <div className="flex items-center justify-between mb-2">
        <h2 id="report-heading" className="text-2xl font-bold">
          Report · <code>{run_id}</code>
        </h2>
        <button
          onClick={() => downloadJSON(report, `tagent-report-${run_id}.json`)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-lg hover:bg-slate-50"
        >
          <Download className="w-4 h-4" /> Export JSON
        </button>
      </div>
      <div className="flex gap-4 text-sm text-slate-600 mb-6">
        <span>
          succeeded=<strong>{String(report.succeeded ?? 0)}</strong>
        </span>
        <span>
          failed=<strong>{String(report.failed ?? 0)}</strong>
        </span>
        <span>
          total=<strong>{String(report.total ?? 0)}</strong>
        </span>
      </div>

      <h3 className="text-lg font-semibold mb-2">节点结果</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border" role="table">
          <thead className="bg-slate-50">
            <tr>
              <th scope="col" className="text-left p-2 border">
                ID
              </th>
              <th scope="col" className="text-left p-2 border">
                Name
              </th>
              <th scope="col" className="text-left p-2 border">
                Kind
              </th>
              <th scope="col" className="text-left p-2 border">
                Script
              </th>
              <th scope="col" className="text-left p-2 border">
                OK
              </th>
              <th scope="col" className="text-left p-2 border">
                Duration(ms)
              </th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(results).map(([nid, r]) => (
              <tr key={nid} className="border">
                <td className="p-2 border">{nid}</td>
                <td className="p-2 border">{String(r.name ?? "?")}</td>
                <td className="p-2 border">{String(r.kind ?? "?")}</td>
                <td className="p-2 border text-xs">{String(r.executed_script ?? "—")}</td>
                <td className="p-2 border">
                  <span aria-label={r.ok ? "通过" : "失败"} className={r.ok ? "text-green-600" : "text-red-600"}>
                    {r.ok ? "✓" : "✗"}
                  </span>
                </td>
                <td className="p-2 border">{String(r.duration_ms ?? 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-6">
        <Link to={`/runs/${run_id}`} className="text-blue-600 hover:underline">
          ← 返回状态页
        </Link>
      </div>
    </section>
  );
}
