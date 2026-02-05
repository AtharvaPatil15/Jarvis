# JARVIS Assistant - Desktop HUD Mode

## 🎯 Quick Start

### Option 1: Automated Startup (Windows)
Double-click `start_jarvis.bat` - This will launch all three components automatically:
1. Python Backend (FastAPI + Voice Controller)
2. Next.js UI Server
3. Electron Desktop Window

### Option 2: Manual Startup

#### Step 1: Start Backend Server
```bash
# Activate Python environment
.venv\Scripts\activate

# Start FastAPI server with voice controller
python start_backend.py
```

#### Step 2: Start Next.js Dev Server
```bash
# In a new terminal
npm run dev
```

#### Step 3: Launch Electron Window
```bash
# In a new terminal
npm run app
```

## 🏗️ Architecture

### 🎤 Backend (Python)
- **FastAPI Server** (`server.py`) - Handles WebSocket connections
- **Voice Controller** (`assistant/voice/voice_controller.py`) - Background service for:
  - Wake word detection (Porcupine)
  - Speech-to-text (Google Speech Recognition)
  - Text-to-speech (Edge-TTS)
- **Orchestrator** - Routes commands to appropriate tools
- **Port**: 8000
- **WebSocket**: `ws://localhost:8000/ws`

### 🎨 Frontend (React + Next.js)
- **Three.js** - 3D holographic visualization
- **Zustand** - Global state management
- **Framer Motion** - Smooth animations
- **Tailwind CSS** - Styling
- **Port**: 3000

### 🖥️ Desktop Wrapper (Electron)
- **Transparent borderless window**
- **Always on top** - Floats over other applications
- **Position**: Top-right corner
- **Resizable**: Yes
- **Click-through**: Disabled (can interact with UI)

## 🔌 WebSocket Events

### From Backend → UI

| Event Type | Payload | Description |
|------------|---------|-------------|
| `wake_word_detected` | `null` | Wake word "computer" detected |
| `state_change` | `"idle" \| "listening" \| "thinking" \| "speaking"` | Voice controller state |
| `user_transcript` | `string` | User's spoken command |
| `ai_response` | `string` | AI's text response |
| `system_status` | `"listening_for_wake_word" \| "offline"` | System status |

### Example Integration in React

```typescript
// In your React component
useEffect(() => {
  const ws = new WebSocket('ws://localhost:8000/ws');
  
  ws.onmessage = (event) => {
    const { type, payload } = JSON.parse(event.data);
    
    switch (type) {
      case 'state_change':
        useAssistantStore.getState().setStatus(payload);
        break;
      case 'user_transcript':
        useAssistantStore.getState().setTranscript(payload);
        break;
      case 'ai_response':
        useAssistantStore.getState().setTranscript(payload);
        break;
    }
  };
  
  return () => ws.close();
}, []);
```

## 🎮 Voice Commands

### Activation
Say **"computer"** to activate the assistant.

### Exit Active Mode
- "exit"
- "stop"
- "thank you"
- "sleep"

When inactive, JARVIS returns to wake word listening mode.

## 🎨 UI States

The holographic visualization responds to voice controller states:

| State | Color | Animation | Trigger |
|-------|-------|-----------|---------|
| **idle** | Blue | Slow breathing | Default state |
| **listening** | Green | Expansion | Microphone active |
| **thinking** | Purple | Chaotic rotation | Processing command |
| **speaking** | Blue | Pulsing | TTS active |
| **executing_tool** | Red | Sharp pulse | Tool execution |

## 🔧 Configuration

### Electron Window Settings
Edit `electron/main.js` to customize:

```javascript
const mainWindow = new BrowserWindow({
  width: 500,           // Window width
  height: 600,          // Window height
  x: width - 520,       // X position
  y: 20,                // Y position
  frame: false,         // Borderless
  transparent: true,    // See-through background
  alwaysOnTop: true,    // Float over apps
  resizable: true,      // Allow resizing
});
```

### Click-Through Mode
To make the window purely visual (no interaction):

```javascript
mainWindow.setIgnoreMouseEvents(true);
```

## 📦 Dependencies

### Python
```
fastapi
uvicorn
websockets
speech_recognition
edge-tts
pvporcupine
pygame
requests
beautifulsoup4
duckduckgo-search
```

### Node.js
```
electron
next
react
react-dom
three
@react-three/fiber
@react-three/drei
@react-three/postprocessing
framer-motion
zustand
tone
leva
tailwindcss
```

## 🐛 Troubleshooting

### Backend won't start
- Ensure Python virtual environment is activated
- Check if port 8000 is available
- Verify Porcupine access key is valid

### UI won't connect
- Ensure Next.js server is running on port 3000
- Check WebSocket connection in browser console
- Verify FastAPI server is running

### Electron window not appearing
- Check if Next.js dev server is running
- Verify `http://localhost:3000` is accessible
- Check Electron logs in terminal

### Voice not working
- Check microphone permissions
- Verify correct microphone is selected
- Test with `python voice_main.py` first

## 📝 Development Tips

1. **Test voice separately**: Use `python voice_main.py` to debug voice issues
2. **Test UI separately**: Use `npm run dev` and open browser to test UI
3. **Monitor WebSocket**: Use browser DevTools → Network → WS tab
4. **Check logs**: Backend logs appear in the "JARVIS Backend" terminal window

## 🚀 Production Build

```bash
# Build Next.js for production
npm run build

# Update electron/main.js to use production build
mainWindow.loadFile('out/index.html');

# Package Electron app
npm install electron-builder --save-dev
npm run dist
```

## 📄 License

Private project - All rights reserved
