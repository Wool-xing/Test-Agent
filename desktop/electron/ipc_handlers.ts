/**
 * IPC handlers for Test-Agent Desktop.
 * Register in main.ts: import { registerIpcHandlers } from "./ipc_handlers";
 */

import { ipcMain, dialog, shell } from "electron";
import { spawn } from "child_process";
import { readFile, writeFile } from "fs/promises";
import { join } from "path";

const BACKEND_PORT = 8800;
const BASE_URL = `http://127.0.0.1:${BACKEND_PORT}`;

export function registerIpcHandlers(): void {
  /** Run a test via the backend API */
  ipcMain.handle("tagent:runTest", async (_event, payload: { text: string; mode?: string; lang?: string }) => {
    try {
      const resp = await fetch(`${BASE_URL}/run/text?mode=${payload.mode || "exec"}&lang=${payload.lang || "zh"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: payload.text }),
      });
      return await resp.json();
    } catch (e: any) {
      return { error: `Backend unreachable: ${e.message}` };
    }
  });

  /** Get run status */
  ipcMain.handle("tagent:getStatus", async (_event, runId: string) => {
    try {
      const resp = await fetch(`${BASE_URL}/status/${runId}`);
      return await resp.json();
    } catch (e: any) {
      return { error: `Backend unreachable: ${e.message}` };
    }
  });

  /** Get run report */
  ipcMain.handle("tagent:getReport", async (_event, runId: string) => {
    try {
      const resp = await fetch(`${BASE_URL}/report/${runId}`);
      return await resp.json();
    } catch (e: any) {
      return { error: `Backend unreachable: ${e.message}` };
    }
  });

  /** Get run history */
  ipcMain.handle("tagent:getHistory", async () => {
    try {
      const resp = await fetch(`${BASE_URL}/history`);
      return await resp.json();
    } catch (e: any) {
      return { error: `Backend unreachable: ${e.message}` };
    }
  });

  /** Get catalog (experts + skills) */
  ipcMain.handle("tagent:getCatalog", async () => {
    try {
      const resp = await fetch(`${BASE_URL}/catalog`);
      return await resp.json();
    } catch (e: any) {
      return { error: `Backend unreachable: ${e.message}` };
    }
  });

  /** Get health status */
  ipcMain.handle("tagent:getHealth", async () => {
    try {
      const resp = await fetch(`${BASE_URL}/health`);
      return await resp.json();
    } catch (e: any) {
      return { status: "error", error: e.message };
    }
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

  /** Open file in system default app */
  ipcMain.handle("tagent:openInShell", async (_event, filePath: string) => {
    await shell.openPath(filePath);
  });

  /** Get dashboard data */
  ipcMain.handle("tagent:getDashboard", async () => {
    try {
      const resp = await fetch(`${BASE_URL}/dashboard`);
      return await resp.json();
    } catch (e: any) {
      return { error: `Backend unreachable: ${e.message}` };
    }
  });

  /** Send user feedback */
  ipcMain.handle("tagent:sendFeedback", async (_event, payload: { runId: string; rating: number; comment: string }) => {
    try {
      const resp = await fetch(`${BASE_URL}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      return await resp.json();
    } catch (e: any) {
      return { error: `Backend unreachable: ${e.message}` };
    }
  });

  /** Cancel a running test */
  ipcMain.handle("tagent:cancelRun", async (_event, runId: string) => {
    try {
      const resp = await fetch(`${BASE_URL}/run/${runId}/cancel`, { method: "POST" });
      return await resp.json();
    } catch (e: any) {
      return { error: `Backend unreachable: ${e.message}` };
    }
  });
}
