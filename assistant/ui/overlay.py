# assistant/ui/overlay.py
import sys
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QObject
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

class Bridge(QObject):
    """
    This bridge allows Python to talk to JavaScript (Three.js).
    """
    status_update = pyqtSignal(str)
    set_mode = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()

class HologramWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 1. Window Setup (Frameless, Transparent, Always on Top)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # Hides from taskbar
        )
        
        # 2. Make Background Transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) # Click-through!

        # 3. Geometry (Top Right Corner - Typical HUD location)
        screen = QApplication.primaryScreen().geometry()  # type: ignore
        size = 400
        self.setGeometry(screen.width() - size - 50, 50, size, size)

        # 4. Browser Engine (The "Projector")
        self.browser = QWebEngineView()
        self.browser.page().setBackgroundColor(Qt.GlobalColor.transparent)  # type: ignore
        
        # 5. Connect Python to JS
        self.channel = QWebChannel()
        self.bridge = Bridge()
        self.channel.registerObject("bridge", self.bridge)
        self.browser.page().setWebChannel(self.channel)  # type: ignore

        # 6. Load the HUD
        # Use __file__ for robust path resolution
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        html_path = os.path.join(script_dir, "hud.html")
        self.browser.load(QUrl.fromLocalFile(html_path))

        self.setCentralWidget(self.browser)

    def set_state(self, state):
        """Control animations from Python"""
        # Valid states: 'idle', 'wake', 'speaking'
        print(f"🖥️ UI State: {state}")
        self.bridge.status_update.emit(state)

    def set_skin(self, skin):
        """Toggle between Jarvis (Blue/Orange) and Friday (Red)"""
        self.bridge.set_mode.emit(skin)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = HologramWindow()
    window.show()
    sys.exit(app.exec())
