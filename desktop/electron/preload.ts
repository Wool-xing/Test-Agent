import { contextBridge, ipcRenderer } from "electron";
import { APP_VERSION, BACKEND_PORT } from "./version";

contextBridge.exposeInMainWorld("electronAPI", {
  getBackendPort: () => BACKEND_PORT,
  getAppVersion: () => APP_VERSION,
  platform: process.platform,
  isElectron: true,
});
