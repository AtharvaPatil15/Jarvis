const { app, BrowserWindow } = require("electron");
const path = require("path");

// 1. Enable specific flags for Transparent GPU rendering
app.commandLine.appendSwitch('enable-transparent-visuals');
app.commandLine.appendSwitch('disable-gpu-driver-bug-workarounds');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 420,
    height: 700,
    x: 0, // Set position if needed
    y: 0, 

    frame: false,
    // 2. Re-enable Transparency
    transparent: true,
    backgroundColor: "#00000000", // Fully transparent hex

    resizable: false,
    hasShadow: false, // Shadows can sometimes cause artifacts

    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.js"),
      backgroundThrottling: false, // Keep animating in background
    }
  });

  mainWindow.loadURL("http://127.0.0.1:3000");
  if (process.argv.includes("--smoke")) {
    const timeout = setTimeout(() => app.exit(2), 60000);
    mainWindow.webContents.once("did-finish-load", () => {
      clearTimeout(timeout);
      console.log("ELECTRON_SMOKE_OK");
      app.exit(0);
    });
    mainWindow.webContents.once("did-fail-load", (_event, code, description) => {
      clearTimeout(timeout);
      console.error(`ELECTRON_SMOKE_FAILED ${code} ${description}`);
      app.exit(1);
    });
  }
  mainWindow.setMenu(null);
  // mainWindow.webContents.openDevTools({ mode: 'detach' }); // Optional

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  // 3. Small delay to ensure GPU is ready
  setTimeout(createWindow, 300);

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});