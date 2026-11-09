"use strict";

// Ventana nativa de PDF Local. Arranca el backend (empaquetado con PyInstaller) en un
// puerto libre, espera a que responda y muestra la interfaz. Al cerrar, mata el backend
// para no dejar procesos huérfanos.

const { app, BrowserWindow, shell } = require("electron");
const { spawn, spawnSync } = require("node:child_process");
const http = require("node:http");
const net = require("node:net");
const path = require("node:path");

const { isAllowedExternalUrl, isTrustedAppUrl } = require("./navigation-policy");

const BACKEND_HOST = "127.0.0.1";
const HEALTH_PATH = "/api/v1/health";
const STARTUP_TIMEOUT_MS = 40_000;
const POLL_EVERY_MS = 300;

/** @type {import("node:child_process").ChildProcess | null} */
let backend = null;
let backendExited = false;
let stopping = false;

/** Pide al sistema un puerto libre y lo devuelve. */
function findFreePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on("error", reject);
    server.listen(0, BACKEND_HOST, () => {
      const { port } = server.address();
      server.close(() => resolve(port));
    });
  });
}

/** Ruta al ejecutable del backend, según esté empaquetado o en desarrollo. */
function backendBinaryPath() {
  const exe = process.platform === "win32" ? "pdf-local-backend.exe" : "pdf-local-backend";
  const folder = app.isPackaged
    ? path.join(process.resourcesPath, "backend")
    : path.join(__dirname, "..", "dist-desktop", "backend");
  return path.join(folder, exe);
}

function startBackend(port) {
  const binary = backendBinaryPath();
  stopping = false;
  backendExited = false;
  backend = spawn(binary, [], {
    env: {
      ...process.env,
      PDFEDITOR_HOST: BACKEND_HOST,
      PDFEDITOR_PORT: String(port),
      PDFEDITOR_PARENT_PIPE: "1",
    },
    // Mantener stdin abierto crea un canal de vida. Si Electron muere antes de ejecutar sus
    // handlers de cierre, el EOF hace que el backend PyInstaller también termine.
    stdio: ["pipe", "ignore", "ignore"],
    windowsHide: true,
  });
  backend.on("exit", (code) => {
    backendExited = true;
    if (code && !app.isPackaged) console.error(`El backend terminó con código ${code}`);
  });
  backend.on("error", (err) => {
    backendExited = true;
    console.error("No se pudo arrancar el backend:", err.message);
  });
}

/** Resuelve cuando el backend responde 200 en /health, o rechaza al agotar el tiempo. */
function waitForBackend(port) {
  const deadline = Date.now() + STARTUP_TIMEOUT_MS;
  return new Promise((resolve, reject) => {
    const attempt = () => {
      if (backendExited) return reject(new Error("El backend se cerró durante el arranque."));
      const request = http.get({ host: BACKEND_HOST, port, path: HEALTH_PATH, timeout: 2_000 }, (res) => {
        res.resume();
        if (res.statusCode === 200) return resolve();
        retry();
      });
      request.on("error", retry);
      request.on("timeout", () => request.destroy());
    };
    const retry = () => {
      if (Date.now() > deadline) return reject(new Error("El backend no respondió a tiempo."));
      setTimeout(attempt, POLL_EVERY_MS);
    };
    attempt();
  });
}

function createWindow(port) {
  const window = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 960,
    minHeight: 640,
    backgroundColor: "#1a1714",
    icon: path.join(__dirname, "build", "icon-256.png"),
    show: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webviewTag: false,
      devTools: !app.isPackaged,
    },
  });

  // EPDF no necesita cámara, micrófono, USB, ubicación ni otros permisos Chromium.
  window.webContents.session.setPermissionCheckHandler(() => false);
  window.webContents.session.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false));

  const keepOnAppOrigin = (event, url) => {
    if (!isTrustedAppUrl(url, port)) event.preventDefault();
  };
  window.webContents.on("will-navigate", keepOnAppOrigin);
  window.webContents.on("will-redirect", keepOnAppOrigin);

  // Los enlaces web se abren en el navegador del sistema. Otros protocolos se descartan.
  window.webContents.setWindowOpenHandler(({ url }) => {
    if (isAllowedExternalUrl(url)) {
      void shell.openExternal(url).catch(() => console.error("No se pudo abrir el enlace externo."));
    }
    return { action: "deny" };
  });

  window.once("ready-to-show", () => window.show());
  void window.loadURL(`http://${BACKEND_HOST}:${port}/`);
}

/** Mata el backend y TODO su árbol de procesos al cerrar la app. Síncrono a propósito:
 *  debe completarse antes de que Electron termine, para no dejar Uvicorn/Python zombie en RAM. */
function stopBackend() {
  if (stopping || !backend || backend.pid === undefined) return;
  stopping = true;
  const pid = backend.pid;
  backend = null;
  try {
    if (process.platform === "win32") {
      // /T incluye a los hijos (worker COM de Office); /F fuerza el cierre.
      spawnSync("taskkill", ["/pid", String(pid), "/t", "/f"], { stdio: "ignore" });
    } else {
      process.kill(pid, "SIGTERM");
    }
  } catch {
    // Si el proceso ya no existe, no hay nada que cerrar.
  }
}

function quitFromSignal() {
  stopBackend();
  app.quit();
}

async function boot() {
  try {
    const port = await findFreePort();
    startBackend(port);
    await waitForBackend(port);
    createWindow(port);
  } catch (err) {
    console.error("Arranque fallido:", err instanceof Error ? err.message : err);
    stopBackend();
    app.quit();
  }
}

// Una sola instancia: si ya hay una abierta, enfocarla en vez de abrir otra.
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on("second-instance", () => {
    const [existing] = BrowserWindow.getAllWindows();
    if (existing) {
      if (existing.isMinimized()) existing.restore();
      existing.focus();
    }
  });

  app.whenReady().then(boot);

  app.on("activate", () => {
    // En macOS se puede reactivar la app sin ventanas. Reiniciamos limpio (matando el backend
    // anterior antes) para no dejar dos servidores vivos.
    if (BrowserWindow.getAllWindows().length === 0) {
      stopBackend();
      void boot();
    }
  });

  app.on("window-all-closed", () => {
    stopBackend();
    app.quit();
  });

  app.on("will-quit", stopBackend);
  process.on("exit", stopBackend);
  process.once("SIGINT", quitFromSignal);
  process.once("SIGTERM", quitFromSignal);
}
