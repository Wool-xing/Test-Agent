import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getStatus } from "@/api";

export default function RunStatusPage() {
  const { run_id } = useParams<{ run_id: string }>();
  const query = useQuery({
    queryKey: ["status", run_id],
    queryFn: () => getStatus(run_id!),
    enabled: !!run_id,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "succeeded" || s === "failed" ? false : 2000;
    },
  });

  if (!run_id) return <p>缺少 run_id</p>;
  const s = query.data;
  const pct = s ? Math.round(((s.succeeded + s.failed) / Math.max(s.total, 1)) * 100) : 0;
  const status = s?.status ?? "loading";

  return (
    <section aria-labelledby="run-heading" className="max-w-3xl">
      <h2 id="run-heading" className="text-2xl font-bold mb-2">
        Run · <code>{run_id}</code>
      </h2>
      <p className="text-sm text-slate-600 mb-4">状态:<strong aria-live="polite">{status}</strong></p>

      {s && (
        <div className="mb-6">
          <div className="flex justify-between text-sm mb-1">
            <span>
              {s.succeeded + s.failed} / {s.total} 节点
            </span>
            <span>{pct}%</span>
          </div>
          <div
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={pct}
            className="w-full h-3 bg-slate-200 rounded overflow-hidden"
          >
            <div className="h-full bg-blue-600 transition-all" style={{ width: `${pct}%` }} />
          </div>
          <div className="text-xs text-slate-500 mt-1">
            succeeded={s.succeeded} · failed={s.failed}
          </div>
        </div>
      )}

      {s?.detail && (
        <details className="mb-4" open={status !== "succeeded"}>
          <summary className="cursor-pointer font-medium">节点详情</summary>
          <pre className="mt-2 text-xs bg-slate-50 p-3 rounded overflow-x-auto">
            {JSON.stringify(s.detail, null, 2)}
          </pre>
        </details>
      )}

      {(status === "succeeded" || status === "failed") && (
        <Link to={`/runs/${run_id}/report`} className="text-blue-600 hover:underline">
          → 查看完整报告
        </Link>
      )}
      {query.isError && (
        <p role="alert" className="text-red-600">
          加载失败:{(query.error as Error).message}
        </p>
      )}
    </section>
  );
}
