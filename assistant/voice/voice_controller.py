import threading
import time

from .conversation_manager import ConversationManager
from .legacy_stt import SpeechToText
from .wake_word import WakeWordEngine
from .legacy_tts import TextToSpeech


class VoiceController:

    def __init__(self, on_event):
        self.on_event = on_event

        self.stt = SpeechToText()
        self.wake = WakeWordEngine()
        self.tts = TextToSpeech()
        self.conv_manager = ConversationManager()

        self.running = False

    def start(self):
        self.running = True
        threading.Thread(target=self._loop, daemon=True).start()
        print("🎙 Voice Controller Started")

    def stop(self):
        self.running = False

    def speak(self, text):
        self.tts.speak(text)

    def _loop(self):

        while self.running:

            print("🛑 Waiting for wake word...")
            self.wake.wait_for_wake()

            self.on_event("wake_word_detected", None)

            # Conversation mode
            while self.running:

                command = self.stt.listen_until_silence()

                if not command:
                    print("No command captured, continue listening")
                    continue

                self.conv_manager.is_processing = True
                self.on_event("process_command", command)

                # Small cooldown prevents mic clipping
                time.sleep(0.5)