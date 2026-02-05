import threading
import queue
import time
import pygame
from typing import Any, Callable, Optional

from assistant.voice.wake_word import WakeWordListener
from assistant.voice.stt import SpeechToText
from assistant.voice.tts import TextToSpeech
from assistant.voice.mic_selector import auto_select_best_mic
from assistant.memory.store import MemoryStore
from assistant.voice.conversation_manager import ConversationManager

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
        self.conv_manager = ConversationManager()
        self.current_task = None
        
        print("🔧 Initializing Voice Core...")
        self.memory = MemoryStore()
        selected_mic = auto_select_best_mic(self.memory.get("mic_device_name"))
        device_index = selected_mic["index"] if selected_mic else None

        self.wake = WakeWordListener(access_key=PORCUPINE_KEY, device_index=device_index, sensitivity=0.9)
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
        # CRITICAL CHANGE: If we are in active mode, go back to listening, NOT idle
        if self.active_mode:
            self.on_event("state_change", "listening")
        else:
            self.on_event("state_change", "idle")

    def _run_loop(self):
        silence_count = 0

        while self.running:

            # Passive Wake Listening
            if not self.active_mode:
                try:
                    if self.wake.listen():
                        self.active_mode = True

                        # UI FIRST → instant response feel
                        self.on_event("wake_word_detected", None)
                        self.on_event("state_change", "listening")

                        # Speak asynchronously (no blocking)
                        threading.Thread(
                            target=self.speak,
                            args=("Yes?",),
                            daemon=True
                        ).start()

                except Exception:
                    time.sleep(0.5)
                    continue

            # Active Command Mode
            if self.active_mode:

                self.on_event("state_change", "listening")

                # ⚡ INTERRUPT SUPPORT: Stop any ongoing TTS
                pygame.mixer.music.stop()

                # ⚡ REDUCED listening window
                command = self.stt.listen(duration=4)

                if command:
                    silence_count = 0
                    self.on_event("user_transcript", command)

                    # Check if this is an interrupt during processing
                    if self.conv_manager.is_processing:
                        action, cmd = self.conv_manager.interrupt(command)

                        if action == "merge":
                            self.on_event("merge_command", cmd)
                            continue

                        if action == "queue":
                            print("📥 Queued new command")
                            continue

                    if any(w in command.lower() for w in ["exit", "stop", "thank you", "that's all", "good job"]):
                        self.active_mode = False
                        threading.Thread(target=self.speak, args=("Standing by.",), daemon=True).start()
                        self.on_event("state_change", "idle")
                        continue

                    self.conv_manager.is_processing = True
                    self.on_event("state_change", "thinking")
                    self.on_event("process_command", command)

                else:
                    silence_count += 1

                    if silence_count > 2:
                        self.active_mode = False
                        self.on_event("state_change", "idle")
                        print("💤 Timeout: Returning to passive mode.")