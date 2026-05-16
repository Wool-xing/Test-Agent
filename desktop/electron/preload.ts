import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("electronAPI", {
  getBackendPort: () => 8800,
  getAppVersion: () => "1.32.0",
  platform: process.platform,
  isElectron: true,
});
