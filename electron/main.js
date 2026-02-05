const { app, BrowserWindow } = require("electron");
const path = require("path");

// IMPORTANT: DO NOT disable GPU
// WebGL requires hardware acceleration
// app.disableHardwareAcceleration();  <-- NEVER enable this

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 420,
    height: 700,

    // ⭐ CRITICAL FIXES
    frame: true,                 // Must be true for WebGL stability
    transparent: false,          // Transparent windows break ThreeJS
    backgroundColor: "#050505",  // Matches your UI background

    resizable: false,

    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.js")
    }
  });

  // ⭐ Load Next.js dev server
  mainWindow.loadURL("http://localhost:3000");

  // ⭐ Open DevTools for debugging
  mainWindow.webContents.openDevTools();

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

// ---------- Electron App Lifecycle ----------

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// ---------- Quit Handling ----------

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
