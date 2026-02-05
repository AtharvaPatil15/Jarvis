# 🤖 JARVIS Assistant

A production-quality voice-controlled AI assistant with an advanced holographic UI inspired by Iron Man's J.A.R.V.I.S.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Node](https://img.shields.io/badge/node-18+-green.svg)

## ✨ Features

- 🎤 **Voice Control** - Wake word detection, speech-to-text, and natural language understanding
- 🎨 **3D Holographic UI** - Real-time animated sphere with state-responsive effects
- 🧠 **Intelligent Planning** - Multi-step task execution with LLM-powered reasoning
- 🔧 **Extensible Tools** - Web search, messaging, smart search, and more
- 💾 **Memory System** - Persistent memory and context awareness
- 🔒 **Safety Layer** - Permission system for sensitive operations

## 🏗️ Architecture

### Frontend (React + Next.js)
- **Three.js** - 3D graphics and particle systems
- **Zustand** - State management
- **Framer Motion** - Animations
- **Tailwind CSS** - Styling
- **Tone.js** - Audio analysis

### Backend (Python)
- **LM Studio** - Local LLM (Qwen 2.5 14B)
- **Porcupine** - Wake word detection
- **SpeechRecognition** - Speech-to-text
- **Edge-TTS** - Text-to-speech

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Node.js 18 or higher
- LM Studio (or compatible OpenAI API endpoint)
- Microphone for voice input

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/jarvis-assistant.git
   cd jarvis-assistant
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # source .venv/bin/activate  # Linux/Mac
   pip install -r requirements.txt
   ```

3. **Install Node.js dependencies**
   ```bash
   npm install
   ```

4. **Configure environment**
   ```bash
   # Copy example env file
   cp .env.example .env
   
   # Add your API key to key.txt or .env file
   # Get a free Gemini API key from: https://makersuite.google.com/app/apikey
   ```

5. **Start LM Studio**
   - Download from: https://lmstudio.ai/
   - Load a model (recommended: Qwen 2.5 14B)
   - Start the server on port 1234

## 🎮 Usage

### Frontend Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the UI.

### Backend (Python Voice Assistant)

```bash
# Activate virtual environment
.venv\Scripts\activate

# Run voice mode
python voice_main.py

# Run CLI mode
python main.py
```

## UI States

The holographic interface responds to different assistant states:

- **idle** - Slow breathing animation (Blue)
- **listening** - Expansion effect (Green)
- **thinking** - Chaotic rotation (Purple)
- **responding** - Normal state (Blue)
- **executing_tool** - Sharp pulsing (Red)

## Project Structure

```
jarvis-assistant/
├── app/                    # Next.js app router
│   ├── page.tsx           # Main UI page
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles
├── components/            # React components
│   ├── ai-core/          # 3D scene components
│   │   ├── CoreSphere.tsx
│   │   ├── ParticleField.tsx
│   │   └── BeamNetwork.tsx
│   └── overlay/          # UI overlays
│       ├── AssistantText.tsx
│       └── ToolIndicator.tsx
├── hooks/                # Custom React hooks
│   └── useAudioAnalyzer.ts
├── store/                # Zustand stores
│   └── assistantStore.ts
├── assistant/            # Python backend
│   ├── orchestrator.py   # Main coordinator
│   ├── brain/           # LLM logic
│   ├── tools/           # Tool implementations
│   ├── voice/           # Voice components
│   └── ui/              # PyQt6 UI (legacy)
├── main.py              # CLI entry point
└── voice_main.py        # Voice entry point
```

## Development

### Testing UI States

Use the Leva controls (top-right) to test different states:
- Change status (idle/listening/thinking/executing_tool)
- Update transcript text
- Simulate tool execution

### Connecting to Python Backend

To connect the React UI to the Python backend, you'll need to:
1. Add WebSocket support to the Python orchestrator
2. Update the Zustand store to listen for WebSocket messages

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Important Notes

- **API Keys**: Never commit your API keys. Use `.env` files and add them to `.gitignore`
- **Local LLM**: For privacy, consider using LM Studio with local models
- **Wake Word**: Porcupine requires a free access key from [Picovoice Console](https://console.picovoice.ai/)

## 🙏 Acknowledgments

- Inspired by J.A.R.V.I.S. from the Marvel Cinematic Universe
- Built with amazing open-source technologies
- Special thanks to the AI and web development communities

## 📞 Support

If you encounter issues or have questions:
- Open an [issue](https://github.com/YOUR_USERNAME/jarvis-assistant/issues)
- Check existing issues for solutions
- Read the [CONTRIBUTING.md](CONTRIBUTING.md) guide
3. Map Python states to UI states

## License

Private project - All rights reserved
