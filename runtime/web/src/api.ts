/** API client for runtime/api/main.py. */

const BASE = (import.meta as any).env?.VITE_API_BASE || "http://localhost:8800";

export interface RunCreated {
  run_id: string;
  decision_summary: {
    detected_target_type: string;
    detected_qualities?: string[];
    confidence: number;
    rationale: string;
    nodes: { id: string; kind: string; name: string }[];
  };
  accepted: boolean;
}

export interface RunStatus {
  run_id: string;
  status: "pending" | "running" | "succeeded" | "failed" | "cancelled";
  succeeded: number;
  failed: number;
  total: number;
  detail?: Record<string, unknown> | null;
}

export interface CatalogResponse {
  experts: { kind: "expert"; name: string; description: string }[];
  skills: { kind: "skill"; name: string; description: string }[];
  counts: { experts: number; skills: number };
}

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail || JSON.stringify(j);
    } catch {
      // ignore
    }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json();
}

export async function postRunText(text: string, extra: Record<string, string> = {}): Promise<RunCreated> {
  const res = await fetch(`${BASE}/run/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, extra }),
  });
  return jsonOrThrow<RunCreated>(res);
}

export async function postRunFile(file: File, extra = ""): Promise<RunCreated> {
  const form = new FormData();
  form.append("file", file);
  if (extra) form.append("extra", extra);
  const res = await fetch(`${BASE}/run/file`, { method: "POST", body: form });
  return jsonOrThrow<RunCreated>(res);
}

export async function postRunUrl(url: string): Promise<RunCreated> {
  const form = new FormData();
  form.append("url", url);
  const res = await fetch(`${BASE}/run/url`, { method: "POST", body: form });
  return jsonOrThrow<RunCreated>(res);
}

export async function getStatus(runId: string): Promise<RunStatus> {
  const res = await fetch(`${BASE}/status/${encodeURIComponent(runId)}`);
  return jsonOrThrow<RunStatus>(res);
}

export async function getReport(runId: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE}/report/${encodeURIComponent(runId)}`);
  return jsonOrThrow<Record<string, unknown>>(res);
}

export async function getCatalog(): Promise<CatalogResponse> {
  const res = await fetch(`${BASE}/catalog`);
  return jsonOrThrow<CatalogResponse>(res);
}
