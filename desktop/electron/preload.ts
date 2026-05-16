import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("electronAPI", {
  getBackendPort: () => 8800,
  getAppVersion: () => "1.31.0",
  platform: process.platform,
  isElectron: true,
});
