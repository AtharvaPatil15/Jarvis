import threading
import time

from .stt import SpeechToText
from .wake_word import WakeWordEngine
from .tts import TextToSpeech


class VoiceController:

    def __init__(self, on_event):
        self.on_event = on_event

        self.stt = SpeechToText()
        self.wake = WakeWordEngine()
        self.tts = TextToSpeech()

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

                self.on_event("process_command", command)

                # Small cooldown prevents mic clipping
                time.sleep(0.5)