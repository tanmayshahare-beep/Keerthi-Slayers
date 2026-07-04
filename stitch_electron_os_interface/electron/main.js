const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("child_process");
const http = require("http");
const path = require("path");

const BACKEND_DIR = path.join(__dirname, "..", "aros_backend");
const BACKEND_URL = "http://127.0.0.1:8000";
const HEALTH_CHECK_TIMEOUT_MS = 15000;
const HEALTH_CHECK_INTERVAL_MS = 300;

let backendProcess = null;

function startBackend() {
  backendProcess = spawn("python3", ["-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8000"], {
    cwd: BACKEND_DIR,
    stdio: "inherit",
  });
  backendProcess.on("error", (err) => {
    dialog.showErrorBox("AROS backend failed to start", err.message);
  });
}

function waitForHealth() {
  const deadline = Date.now() + HEALTH_CHECK_TIMEOUT_MS;
  return new Promise((resolve, reject) => {
    const attempt = () => {
      http
        .get(`${BACKEND_URL}/health`, (res) => {
          if (res.statusCode === 200) {
            resolve();
          } else if (Date.now() > deadline) {
            reject(new Error(`Backend health check failed with status ${res.statusCode}`));
          } else {
            setTimeout(attempt, HEALTH_CHECK_INTERVAL_MS);
          }
        })
        .on("error", () => {
          if (Date.now() > deadline) {
            reject(new Error("Backend did not become healthy in time"));
          } else {
            setTimeout(attempt, HEALTH_CHECK_INTERVAL_MS);
          }
        });
    };
    attempt();
  });
}

async function createWindow() {
  startBackend();
  try {
    await waitForHealth();
  } catch (err) {
    dialog.showErrorBox("AROS backend unavailable", err.message);
    app.quit();
    return;
  }

  const win = new BrowserWindow({
    width: 900,
    height: 720,
  });
  win.loadURL(BACKEND_URL);
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  app.quit();
});

app.on("will-quit", () => {
  if (backendProcess) backendProcess.kill();
});
