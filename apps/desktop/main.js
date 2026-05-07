const { app, BrowserWindow } = require("electron");
const path = require("path");

app.commandLine.appendSwitch("enable-transparent-visuals");
app.commandLine.appendSwitch("disable-gpu-driver-bug-workarounds");

let mainWindow;
const webUrl = process.env.JARVIS_WEB_URL || "http://localhost:3000";

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 420,
    height: 700,
    x: 0,
    y: 0,
    frame: false,
    transparent: true,
    backgroundColor: "#00000000",
    resizable: false,
    hasShadow: false,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.js"),
      backgroundThrottling: false,
    },
  });

  mainWindow.loadURL(webUrl);
  mainWindow.setMenu(null);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
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
