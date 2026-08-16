/**
 * IPC handlers for Test-Agent Desktop.
 * Register in main.ts: import { registerIpcHandlers } from "./ipc_handlers";
 */

import { ipcMain, dialog, shell } from "electron";
import { extname } from "path";
import { BACKEND_PORT } from "./version";

const BASE_URL = `http://127.0.0.1:${BACKEND_PORT}`;
const RUN_ID_RE = /^[a-zA-Z0-9-]+$/;
const OPEN_EXT_WHITELIST = new Set([
  ".md", ".txt", ".pdf", ".html", ".json", ".png", ".jpg", ".xlsx", ".csv",
]);

/**
 * Fetch from the localhost backend. Checks resp.ok and parses JSON safely —
 * a non-JSON or non-2xx response is reported as a backend error, never
 * mislabeled "Backend unreachable".
 */
async function backendFetch(path: string, init?: RequestInit): Promise<unknown> {
  try {
    const resp = await fetch(`${BASE_URL}${path}`, init);
    let body: unknown = null;
    try {
      body = await resp.json();
    } catch {
      body = null;
    }
    if (!resp.ok) {
      return { error: `Backend error ${resp.status}`, detail: body };
    }
    return body;
  } catch (e: unknown) {
    return { error: `Backend unreachable: ${(e as Error).message}` };
  }
}

/** runId comes from the renderer — validate before interpolating into a URL. */
function validateRunId(runId: string): string | null {
  return RUN_ID_RE.test(runId) ? runId : null;
}

export function registerIpcHandlers(): void {
  /** Run a test via the backend API */
  ipcMain.handle("tagent:runTest", async (_event, payload: { text: string; mode?: string; lang?: string }) => {
    const mode = encodeURIComponent(payload.mode || "exec");
    const lang = encodeURIComponent(payload.lang || "zh");
    return await backendFetch(`/run/text?mode=${mode}&lang=${lang}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: payload.text }),
    });
  });

  /** Get run status */
  ipcMain.handle("tagent:getStatus", async (_event, runId: string) => {
    const id = validateRunId(runId);
    if (id === null) return { error: "invalid runId" };
    return await backendFetch(`/status/${id}`);
  });

  /** Get run report */
  ipcMain.handle("tagent:getReport", async (_event, runId: string) => {
    const id = validateRunId(runId);
    if (id === null) return { error: "invalid runId" };
    return await backendFetch(`/report/${id}`);
  });

  /** Get run history */
  ipcMain.handle("tagent:getHistory", async () => {
    return await backendFetch("/history");
  });

  /** Get catalog (experts + skills) */
  ipcMain.handle("tagent:getCatalog", async () => {
    return await backendFetch("/catalog");
  });

  /** Get health status */
  ipcMain.handle("tagent:getHealth", async () => {
    return await backendFetch("/health");
  });

  /** Open file dialog to select a PRD file */
  ipcMain.handle("tagent:selectFile", async () => {
    const result = await dialog.showOpenDialog({
      properties: ["openFile"],
      filters: [
        { name: "Documents", extensions: ["md", "txt", "pdf", "docx", "xlsx"] },
        { name: "All Files", extensions: ["*"] },
      ],
    });
    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }
    return result.filePaths[0];
  });

  /** Open directory dialog to select project */
  ipcMain.handle("tagent:selectProject", async () => {
    const result = await dialog.showOpenDialog({
      properties: ["openDirectory"],
    });
    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }
    return result.filePaths[0];
  });

  /** Open file in system default app — document extensions only */
  ipcMain.handle("tagent:openInShell", async (_event, filePath: string) => {
    if (typeof filePath !== "string" || filePath.length === 0) {
      return { error: "invalid path" };
    }
    const ext = extname(filePath).toLowerCase();
    if (!OPEN_EXT_WHITELIST.has(ext)) {
      console.warn("Blocked openInShell for:", filePath);
      return { error: `file type not allowed: ${ext || "(none)"}` };
    }
    const err = await shell.openPath(filePath);
    return err ? { error: err } : { ok: true };
  });

  /** Get dashboard data */
  ipcMain.handle("tagent:getDashboard", async () => {
    return await backendFetch("/dashboard");
  });

  /** Send user feedback */
  ipcMain.handle("tagent:sendFeedback", async (_event, payload: { runId: string; rating: number; comment: string }) => {
    return await backendFetch("/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
  });

  /** Cancel a running test */
  ipcMain.handle("tagent:cancelRun", async (_event, runId: string) => {
    const id = validateRunId(runId);
    if (id === null) return { error: "invalid runId" };
    return await backendFetch(`/run/${id}/cancel`, { method: "POST" });
  });
}
