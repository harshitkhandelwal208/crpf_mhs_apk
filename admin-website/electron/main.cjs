const { app, BrowserWindow, Menu, dialog, session, shell } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const http = require("node:http");
const net = require("node:net");
const path = require("node:path");

const LOOPBACK_HOST = "127.0.0.1";
const CONFIG_FILE_NAME = "desktop-config.json";
const MAX_CONFIG_BYTES = 16 * 1024;
const MAX_SERVER_LOG_BYTES = 16 * 1024;
const FILE_CONFIG_KEYS = new Set(["BACKEND_API_URL"]);

let mainWindow = null;
let localOrigin = null;
let serverProcess = null;
let serverFailure = null;
let serverReady = false;
let serverOutput = "";
let isShuttingDown = false;
let shutdownComplete = false;
let shutdownPromise = null;

function appendServerOutput(streamName, chunk) {
  const text = String(chunk).replace(/\u001b\[[0-9;]*m/g, "");
  serverOutput += `[${streamName}] ${text}`;

  if (Buffer.byteLength(serverOutput, "utf8") > MAX_SERVER_LOG_BYTES) {
    serverOutput = serverOutput.slice(-MAX_SERVER_LOG_BYTES);
  }
}

function isLoopbackHostname(hostname) {
  return hostname === LOOPBACK_HOST || hostname === "localhost" || hostname === "[::1]";
}

function validateBackendApiUrl(value) {
  let parsed;

  try {
    parsed = new URL(value);
  } catch {
    throw new Error("BACKEND_API_URL in desktop-config.json must be a valid URL.");
  }

  const secure = parsed.protocol === "https:";
  const loopbackDevelopment = parsed.protocol === "http:" && isLoopbackHostname(parsed.hostname);

  if (!secure && !loopbackDevelopment) {
    throw new Error(
      "BACKEND_API_URL in desktop-config.json must use HTTPS (loopback HTTP is allowed for development).",
    );
  }

  if (parsed.username || parsed.password) {
    throw new Error("BACKEND_API_URL must not contain credentials.");
  }
}

function loadDesktopConfig() {
  const configPath = path.join(app.getPath("userData"), CONFIG_FILE_NAME);

  if (!fs.existsSync(configPath)) {
    return {};
  }

  const stats = fs.statSync(configPath);
  if (!stats.isFile()) {
    throw new Error(`${configPath} must be a regular file.`);
  }
  if (stats.size > MAX_CONFIG_BYTES) {
    throw new Error(`${configPath} exceeds the ${MAX_CONFIG_BYTES}-byte limit.`);
  }

  let config;
  try {
    config = JSON.parse(fs.readFileSync(configPath, "utf8"));
  } catch (error) {
    throw new Error(`Could not parse ${configPath}: ${error.message}`);
  }

  if (!config || typeof config !== "object" || Array.isArray(config)) {
    throw new Error(`${configPath} must contain a JSON object.`);
  }

  const runtimeConfig = {};
  for (const [key, value] of Object.entries(config)) {
    if (!FILE_CONFIG_KEYS.has(key)) {
      throw new Error(`Unsupported setting in ${configPath}: ${key}`);
    }
    if (typeof value !== "string" || value.length === 0 || value.length > 2048 || value.includes("\0")) {
      throw new Error(`${key} in ${configPath} must be a non-empty string of at most 2048 characters.`);
    }

    if (key === "BACKEND_API_URL") {
      validateBackendApiUrl(value);
    }
    runtimeConfig[key] = value;
  }

  return runtimeConfig;
}

function reserveFreeLoopbackPort() {
  return new Promise((resolve, reject) => {
    const reservation = net.createServer();
    reservation.unref();
    reservation.once("error", reject);
    reservation.listen({ host: LOOPBACK_HOST, port: 0, exclusive: true }, () => {
      const address = reservation.address();
      if (!address || typeof address === "string") {
        reservation.close();
        reject(new Error("Could not select a loopback port."));
        return;
      }

      reservation.close((error) => {
        if (error) {
          reject(error);
        } else {
          resolve(address.port);
        }
      });
    });
  });
}

function serverCommand(port) {
  if (app.isPackaged) {
    const root = path.join(process.resourcesPath, "next-standalone");
    return {
      cwd: root,
      args: [path.join(root, "server.js")],
    };
  }

  const root = path.resolve(__dirname, "..");
  return {
    cwd: root,
    args: [
      path.join(root, "node_modules", "next", "dist", "bin", "next"),
      "dev",
      "--hostname",
      LOOPBACK_HOST,
      "--port",
      String(port),
    ],
  };
}

function startServer(port) {
  const command = serverCommand(port);
  const entryPoint = command.args[0];

  if (!fs.existsSync(entryPoint)) {
    throw new Error(`Local Next server entry point was not found: ${entryPoint}`);
  }

  const fileConfig = loadDesktopConfig();
  const environment = {
    ...fileConfig,
    ...process.env,
    ELECTRON_RUN_AS_NODE: "1",
    HOSTNAME: LOOPBACK_HOST,
    NODE_ENV: app.isPackaged ? "production" : "development",
    NEXT_TELEMETRY_DISABLED: process.env.NEXT_TELEMETRY_DISABLED || "1",
    PORT: String(port),
  };

  serverProcess = spawn(process.execPath, command.args, {
    cwd: command.cwd,
    env: environment,
    shell: false,
    stdio: ["ignore", "pipe", "pipe"],
    windowsHide: true,
  });

  serverProcess.stdout.setEncoding("utf8");
  serverProcess.stderr.setEncoding("utf8");
  serverProcess.stdout.on("data", (chunk) => {
    appendServerOutput("stdout", chunk);
    if (!app.isPackaged) {
      process.stdout.write(chunk);
    }
  });
  serverProcess.stderr.on("data", (chunk) => {
    appendServerOutput("stderr", chunk);
    if (!app.isPackaged) {
      process.stderr.write(chunk);
    }
  });

  serverProcess.once("error", (error) => {
    serverFailure = error;
  });
  serverProcess.once("exit", (code, signal) => {
    if (isShuttingDown) {
      return;
    }

    const reason = signal ? `signal ${signal}` : `exit code ${code}`;
    serverFailure = new Error(`The local Next server stopped with ${reason}.`);

    if (serverReady) {
      dialog.showErrorBox(
        "CRPF MHS Admin server stopped",
        `${serverFailure.message}\n\nClose and restart the application.\n\n${serverOutput}`,
      );
      app.quit();
    }
  });
}

function probeServer(url, timeoutMs) {
  return new Promise((resolve, reject) => {
    const request = http.get(url, { timeout: timeoutMs }, (response) => {
      response.resume();
      resolve();
    });
    request.once("timeout", () => request.destroy(new Error("Readiness request timed out.")));
    request.once("error", reject);
  });
}

async function waitForServer(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;

  while (Date.now() < deadline) {
    if (serverFailure) {
      throw serverFailure;
    }

    try {
      await probeServer(url, Math.min(3000, Math.max(1, deadline - Date.now())));
      return;
    } catch (error) {
      lastError = error;
    }

    await new Promise((resolve) => setTimeout(resolve, 250));
  }

  throw new Error(
    `The local Next server did not become ready within ${Math.round(timeoutMs / 1000)} seconds. ${
      lastError ? lastError.message : ""
    }`.trim(),
  );
}

function isLocalAppUrl(rawUrl) {
  try {
    return localOrigin !== null && new URL(rawUrl).origin === localOrigin;
  } catch {
    return false;
  }
}

function isSafeExternalUrl(rawUrl) {
  try {
    const parsed = new URL(rawUrl);
    return (
      (parsed.protocol === "https:" || parsed.protocol === "http:") &&
      Boolean(parsed.hostname) &&
      !parsed.username &&
      !parsed.password
    );
  } catch {
    return false;
  }
}

function openExternalUrl(rawUrl) {
  if (!isSafeExternalUrl(rawUrl) || isLocalAppUrl(rawUrl)) {
    return;
  }

  shell.openExternal(rawUrl).catch((error) => {
    dialog.showErrorBox("Could not open link", error.message);
  });
}

function handleNavigation(event, targetUrl) {
  if (isLocalAppUrl(targetUrl)) {
    return;
  }

  event.preventDefault();
  openExternalUrl(targetUrl);
}

function configureWebContents(contents) {
  contents.setWindowOpenHandler(({ url }) => {
    openExternalUrl(url);
    return { action: "deny" };
  });
  contents.on("will-navigate", handleNavigation);
  contents.on("will-redirect", handleNavigation);
  contents.on("will-attach-webview", (event) => event.preventDefault());
}

function configurePermissions() {
  const defaultSession = session.defaultSession;
  defaultSession.setPermissionCheckHandler(() => false);
  defaultSession.setPermissionRequestHandler((_webContents, _permission, callback) => callback(false));

  if (typeof defaultSession.setDevicePermissionHandler === "function") {
    defaultSession.setDevicePermissionHandler(() => false);
  }
}

async function createMainWindow(url) {
  const window = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 720,
    show: false,
    backgroundColor: "#111827",
    autoHideMenuBar: app.isPackaged,
    title: "CRPF MHS Admin",
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      webSecurity: true,
      allowRunningInsecureContent: false,
      webviewTag: false,
      spellcheck: false,
      devTools: !app.isPackaged,
      backgroundThrottling: true,
    },
  });

  mainWindow = window;
  window.once("ready-to-show", () => window.show());
  window.on("closed", () => {
    mainWindow = null;
  });

  if (app.isPackaged) {
    window.removeMenu();
  }

  await window.loadURL(url);
}

async function bootstrap() {
  configurePermissions();
  if (app.isPackaged) {
    Menu.setApplicationMenu(null);
  }

  const port = await reserveFreeLoopbackPort();
  localOrigin = `http://${LOOPBACK_HOST}:${port}`;
  startServer(port);
  await waitForServer(localOrigin, app.isPackaged ? 45_000 : 120_000);
  serverReady = true;
  await createMainWindow(localOrigin);
}

function startupErrorDetails(error) {
  const configPath = path.join(app.getPath("userData"), CONFIG_FILE_NAME);
  const output = serverOutput || "No server output was captured.";
  return [
    "The local admin server could not start on 127.0.0.1.",
    "",
    error.message,
    "",
    `Check ${configPath} and verify endpoint security has not blocked the application.`,
    "No public or LAN listener was opened.",
    "",
    output,
  ].join("\n");
}

function forceStopServerTree(child, done) {
  if (process.platform !== "win32" || !child.pid) {
    try {
      child.kill("SIGKILL");
    } finally {
      done();
    }
    return;
  }

  const taskkill = spawn("taskkill.exe", ["/pid", String(child.pid), "/T", "/F"], {
    shell: false,
    stdio: "ignore",
    windowsHide: true,
  });
  taskkill.once("error", done);
  taskkill.once("exit", done);
}

function stopServer() {
  const child = serverProcess;
  serverProcess = null;

  if (!child || child.exitCode !== null) {
    return Promise.resolve();
  }

  return new Promise((resolve) => {
    let settled = false;
    let forceTimer;
    let finishTimer;

    const done = () => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(forceTimer);
      clearTimeout(finishTimer);
      resolve();
    };

    child.once("exit", done);

    try {
      child.kill("SIGTERM");
    } catch {
      done();
      return;
    }

    forceTimer = setTimeout(() => forceStopServerTree(child, done), 2500);
    finishTimer = setTimeout(done, 5000);
  });
}

const hasSingleInstanceLock = app.requestSingleInstanceLock();

if (!hasSingleInstanceLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
    if (!mainWindow) {
      return;
    }
    if (mainWindow.isMinimized()) {
      mainWindow.restore();
    }
    mainWindow.show();
    mainWindow.focus();
  });

  app.on("web-contents-created", (_event, contents) => configureWebContents(contents));
  app.on("window-all-closed", () => app.quit());
  app.on("before-quit", (event) => {
    if (shutdownComplete) {
      return;
    }

    event.preventDefault();
    if (shutdownPromise) {
      return;
    }

    isShuttingDown = true;
    shutdownPromise = stopServer().finally(() => {
      shutdownComplete = true;
      app.quit();
    });
  });

  app.whenReady().then(bootstrap).catch((error) => {
    dialog.showErrorBox("CRPF MHS Admin could not start", startupErrorDetails(error));
    app.quit();
  });
}
