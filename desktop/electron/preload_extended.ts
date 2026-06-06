/**
 * Extended preload for Test-Agent Desktop.
 *
 * Exposes 14 IPC methods to the renderer under window.tagendAPI:
 *   runTest, getStatus, getReport, getHistory, getCatalog, getHealth,
 *   selectFile, selectProject, openInShell, getDashboard, sendFeedback,
 *   cancelRun, getBackendPort, getAppVersion, platform, isElectron
 *
 * Usage: replace preload.ts path in electron-builder.yml / main.ts BrowserWindow config
 * with this file for full desktop integration.
 */

import { contextBridge, ipcRenderer } from "electron";
import { APP_VERSION, BACKEND_PORT } from "./version";

contextBridge.exposeInMainWorld("tagendAPI", {
  // ── Backend API ──
  runTest: (payload: { text: string; mode?: string; lang?: string }) =>
    ipcRenderer.invoke("tagent:runTest", payload),

  getStatus: (runId: string) =>
    ipcRenderer.invoke("tagent:getStatus", runId),

  getReport: (runId: string) =>
    ipcRenderer.invoke("tagent:getReport", runId),

  getHistory: () =>
    ipcRenderer.invoke("tagent:getHistory"),

  getCatalog: () =>
    ipcRenderer.invoke("tagent:getCatalog"),

  getHealth: () =>
    ipcRenderer.invoke("tagent:getHealth"),

  getDashboard: () =>
    ipcRenderer.invoke("tagent:getDashboard"),

  sendFeedback: (payload: { runId: string; rating: number; comment: string }) =>
    ipcRenderer.invoke("tagent:sendFeedback", payload),

  cancelRun: (runId: string) =>
    ipcRenderer.invoke("tagent:cancelRun", runId),

  // ── Native dialogs ──
  selectFile: () =>
    ipcRenderer.invoke("tagent:selectFile"),

  selectProject: () =>
    ipcRenderer.invoke("tagent:selectProject"),

  openInShell: (filePath: string) =>
    ipcRenderer.invoke("tagent:openInShell", filePath),

  // ── Metadata ──
  getBackendPort: () => BACKEND_PORT,
  getAppVersion: () => APP_VERSION,
  platform: process.platform,
  isElectron: true,
});

// Backward compat: pages that check window.electronAPI still work
contextBridge.exposeInMainWorld("electronAPI", {
  getBackendPort: () => BACKEND_PORT,
  getAppVersion: () => APP_VERSION,
  platform: process.platform,
  isElectron: true,
});
