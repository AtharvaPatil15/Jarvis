import random
from pathlib import Path
import sys


APP_DIR = Path(__file__).resolve().parent
SRC_DIR = APP_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from jarvis_backend.memory.store import MemoryStore
from jarvis_backend.orchestrator import Orchestrator
from jarvis_backend.voice.mic_selector import auto_select_best_mic
from jarvis_backend.voice.stt import SpeechToText
from jarvis_backend.voice.tts import TextToSpeech
from jarvis_backend.voice.wake_word import WakeWordListener


PORCUPINE_ACCESS_KEY = "ycGaIQbL2ZWI8r2MfkZlGZN/huiTFCQwSWNLW0Liu7hilS1fG22VJA=="


def get_wake_response():
    responses = [
        "I'm listening.",
        "Go ahead.",
        "Ready.",
        "Yes, sir?",
        "Online.",
        "At your service.",
        "Standing by.",
    ]
    return random.choice(responses)


def main():
    print("Voice Assistant started")
    print("Say 'computer' to wake me up")
    print("Say 'exit' to stop\n")

    memory = MemoryStore()
    last_mic_name = memory.get("mic_device_name")
    selected = auto_select_best_mic(last_mic_name)

    if not selected:
        print("No microphone detected.")
        return

    print(f"Auto-selected microphone: {selected['name']}")
    memory.set("mic_device_name", selected["name"])

    wake_listener = WakeWordListener(
        access_key=PORCUPINE_ACCESS_KEY,
        keyword="computer",
        device_index=selected["index"],
        sensitivity=0.9,
    )
    stt = SpeechToText(device_index=selected["index"])
    tts = TextToSpeech()
    orchestrator = Orchestrator()

    while True:
        print("\nWaiting for wake word...")

        try:
            detected = wake_listener.listen()
        except KeyboardInterrupt:
            print("Voice assistant stopped.")
            break

        if not detected:
            continue

        print("Wake word detected.")
        tts.speak(get_wake_response())
        active_mode = True

        while active_mode:
            print("Listening for command...")
            try:
                command = stt.listen(duration=8)
            except KeyboardInterrupt:
                active_mode = False
                break

            if not command:
                print("...Silence...")
                active_mode = False
                continue

            print(f"Command heard: {command}")
            command_lower = command.lower()

            if any(phrase in command_lower for phrase in ["exit", "stop", "go to sleep", "that's all", "thank you"]):
                tts.speak("Shutting down active mode.")
                active_mode = False
                break

            response = orchestrator.handle_input(command)
            print(f"\nJarvis: {response}\n")
            tts.speak(response)


if __name__ == "__main__":
    main()
