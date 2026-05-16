import { app, BrowserWindow, dialog, shell } from "electron";
import { ChildProcess, spawn } from "child_process";
import * as path from "path";
import * as http from "http";

let backendProcess: ChildProcess | null = null;
let mainWindow: BrowserWindow | null = null;

const BACKEND_PORT = 8800;
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`;

function getBackendPath(): string {
  const isDev = !app.isPackaged;
  if (isDev) {
    return process.execPath; // fallback: will try tagent CLI in dev
  }
  const base = process.resourcesPath;
  if (process.platform === "win32") {
    return path.join(base, "backend", "tagent-backend.exe");
  }
  return path.join(base, "backend", "tagent-backend");
}

function startBackend(): Promise<void> {
  return new Promise((resolve, reject) => {
    const isDev = !app.isPackaged;
    const cmd = isDev
      ? "python"
      : getBackendPath();
    const args = isDev
      ? ["-m", "runtime.cli.main", "run", "--help"] // dev: use CLI
      : [];

    // In dev mode, start uvicorn directly
    const devArgs = isDev
      ? ["-c", `import uvicorn; uvicorn.run('runtime.api.main:app',host='127.0.0.1',port=${BACKEND_PORT})`]
      : [];

    try {
      if (isDev) {
        backendProcess = spawn("python", devArgs, {
          env: {
            ...process.env,
            TAGENT_API_PORT: String(BACKEND_PORT),
            TAGENT_API_HOST: "127.0.0.1",
            TAGENT_LLM_PROVIDER: "stub",
            PYTHONUNBUFFERED: "1",
          },
          stdio: ["ignore", "pipe", "pipe"],
        });
      } else {
        backendProcess = spawn(cmd, args, {
          env: {
            ...process.env,
            TAGENT_API_PORT: String(BACKEND_PORT),
            TAGENT_API_HOST: "127.0.0.1",
            PYTHONUNBUFFERED: "1",
          },
          stdio: ["ignore", "pipe", "pipe"],
        });
      }

      backendProcess.stdout?.on("data", (data: Buffer) => {
        console.log(`[backend] ${data.toString().trim()}`);
      });
      backendProcess.stderr?.on("data", (data: Buffer) => {
        console.error(`[backend] ${data.toString().trim()}`);
      });

      backendProcess.on("error", (err: Error) => {
        console.error("Failed to start backend:", err.message);
        reject(err);
      });

      backendProcess.on("exit", (code: number | null) => {
        console.log(`Backend exited with code ${code}`);
        backendProcess = null;
      });

      // Poll /health until backend is ready
      let attempts = 0;
      const maxAttempts = 60;
      const check = () => {
        attempts++;
        http
          .get(`${BACKEND_URL}/health`, (res) => {
            if (res.statusCode === 200) {
              resolve();
            } else if (attempts < maxAttempts) {
              setTimeout(check, 500);
            } else {
              reject(new Error("Backend health check failed"));
            }
          })
          .on("error", () => {
            if (attempts < maxAttempts) {
              setTimeout(check, 500);
            } else {
              reject(new Error("Backend not reachable after 30s"));
            }
          });
      };
      setTimeout(check, 1000);
    } catch (err) {
      reject(err);
    }
  });
}

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: "Test-Agent",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
    show: false,
  });

  const isDev = !app.isPackaged;
  if (isDev) {
    mainWindow.loadURL("http://localhost:5173");
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(
      path.join(__dirname, "../../runtime/web/dist/index.html")
    );
  }

  mainWindow.once("ready-to-show", () => {
    mainWindow?.show();
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
}

app.whenReady().then(async () => {
  try {
    await startBackend();
  } catch (err: any) {
    dialog.showErrorBox(
      "Backend Error",
      `Failed to start Test-Agent backend:\n${err.message}\n\nPlease ensure Python 3.10+ is installed.`
    );
    app.quit();
    return;
  }
  createWindow();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
