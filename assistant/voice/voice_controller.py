import threading
import time
from typing import Any, Callable, Optional

from assistant.voice.wake_word import WakeWordListener
from assistant.voice.stt import SpeechToText
from assistant.voice.tts import TextToSpeech
from assistant.voice.mic_selector import auto_select_best_mic
from assistant.memory.store import MemoryStore

# PORCUPINE KEY (Kept from previous context)
PORCUPINE_KEY = "ycGaIQbL2ZWI8r2MfkZlGZN/huiTFCQwSWNLW0Liu7hilS1fG22VJA=="

class VoiceController:
    """
    Background Service: Manages Microphone & Speakers.
    """
    def __init__(self, on_event: Callable[[str, Any], None]):
        self.on_event = on_event
        self.running = False
        self.active_mode = False
        self.thread: Optional[threading.Thread] = None
        
        # Initialize conv_manager placeholder to prevent AttributeError
        self.conv_manager = None 
        
        print("🔧 Initializing Voice Core...")
        self.memory = MemoryStore()
        selected_mic = auto_select_best_mic(self.memory.get("mic_device_name"))
        device_index = selected_mic["index"] if selected_mic else None

        self.wake = WakeWordListener(access_key=PORCUPINE_KEY, device_index=device_index, sensitivity=0.8)
        self.stt = SpeechToText(device_index=device_index)
        self.tts = TextToSpeech()
        print("✅ Voice Core Ready")

    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        self.on_event("system_status", "listening_for_wake_word")
        print("▶️  Voice Service Started")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.on_event("system_status", "offline")
        print("⏹️  Voice Service Stopped")

    def speak(self, text: str):
        self.on_event("state_change", "speaking")
        self.tts.speak(text)
        if self.active_mode:
            self.on_event("state_change", "listening")
        else:
            self.on_event("state_change", "idle")

    def _run_loop(self):
        silence_count = 0
        
        while self.running:
            # 1. Passive Listening (Wake Word)
            if not self.active_mode:
                try:
                    if self.wake.listen():
                        self.active_mode = True
                        self.on_event("wake_word_detected", None)
                        self.on_event("state_change", "listening")
                        self.speak("Yes?")
                except Exception:
                    time.sleep(1)
                    continue

            # 2. Active Command Listening
            if self.active_mode:
                self.on_event("state_change", "listening")
                
                try:
                    command = self.stt.listen_until_silence()
                except Exception as e:
                    print(f"STT Error: {e}")
                    command = None

                if command:
                    silence_count = 0
                    self.on_event("user_transcript", command)
                    
                    if any(w in command.lower() for w in ["exit", "stop", "thank you", "that's all", "good job"]):
                        self.active_mode = False
                        self.speak("Standing by.")
                        self.on_event("state_change", "idle")
                        continue
                    
                    self.on_event("state_change", "thinking")
                    self.on_event("process_command", command)
                
                else:
                    silence_count += 1
                    if silence_count > 2:
                        self.active_mode = False
                        self.on_event("state_change", "idle")
                        print("💤 Timeout: Returning to passive mode.")
                    else:
                        pass