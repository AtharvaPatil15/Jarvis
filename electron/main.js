const { app, BrowserWindow, screen } = require('electron');
const path = require('path');

let mainWindow;

// Fix for some Windows GPUs rendering black on transparent windows
app.disableHardwareAcceleration(); 

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: 500,
    height: 600,
    x: width - 520, 
    y: 20,
    frame: false,       // No border
    transparent: true,  // See-through
    backgroundColor: '#00000000', // Fully transparent hex
    alwaysOnTop: true,
    resizable: true,
    hasShadow: false,   // Disable shadow to prevent artifacts
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });

  mainWindow.loadURL('http://localhost:3000');
  
  // Keep mouse events active so you can drag/interact for now
  mainWindow.setIgnoreMouseEvents(false);

  mainWindow.on('closed', () => (mainWindow = null));
}

app.on('ready', () => {
    setTimeout(createWindow, 500); // Slight delay to ensure app is ready
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (mainWindow === null) createWindow();
});