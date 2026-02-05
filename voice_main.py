import sys
import random
from assistant.orchestrator import Orchestrator
from assistant.voice.stt import SpeechToText
from assistant.voice.tts import TextToSpeech
from assistant.memory.store import MemoryStore
from assistant.voice.mic_selector import auto_select_best_mic
from assistant.voice.wake_word import WakeWordListener

# Access key for Porcupine (Keep your existing key here)
PORCUPINE_ACCESS_KEY = "ycGaIQbL2ZWI8r2MfkZlGZN/huiTFCQwSWNLW0Liu7hilS1fG22VJA=="

def get_wake_response():
    """Returns a random, natural response to being woken up."""
    responses = [
        "I'm listening.",
        "Go ahead.",
        "Ready.",
        "Yes, sir?",
        "Online.",
        "At your service.",
        "Standing by."
    ]
    return random.choice(responses)

def main():
    print("🎙️ Voice Assistant started")
    print("Say 'computer' to wake me up")
    print("Say 'exit' to stop\n")

    # Mic selection
    memory = MemoryStore()
    last_mic_name = memory.get("mic_device_name")
    selected = auto_select_best_mic(last_mic_name)

    if not selected:
        print("❌ No microphone detected.")
        return

    print(f"🎤 Auto-selected microphone: {selected['name']}")
    memory.set("mic_device_name", selected["name"])

    # Initialize components
    wake_listener = WakeWordListener(
        access_key=PORCUPINE_ACCESS_KEY,
        keyword="computer",
        device_index=selected["index"],
        sensitivity=0.9
    )
    stt = SpeechToText(device_index=selected["index"])
    tts = TextToSpeech()
    orchestrator = Orchestrator()

    while True:
        print("\n🟢 Waiting for wake word...")
        
        # 1. Passive Listen (Low Power)
        try:
            detected = wake_listener.listen()
        except KeyboardInterrupt:
            print("⏹️ Voice assistant stopped.")
            break

        if not detected:
            continue

        # 2. Wake Word Detected -> Active Mode
        print("👋 Wake word detected!")
        greeting = get_wake_response()
        tts.speak(greeting)

        active_mode = True
        
        while active_mode:
            print("🎤 Listening for command...")
            try:
                command = stt.listen(duration=8)
            except KeyboardInterrupt:
                active_mode = False
                break

            if not command:
                print("...Silence...")
                active_mode = False 
                continue

            print(f"📝 Command heard: {command}")
            command_lower = command.lower()

            # Natural exit phrases
            if any(phrase in command_lower for phrase in ["exit", "stop", "go to sleep", "that's all", "thank you"]):
                tts.speak("Shutting down active mode.")
                active_mode = False
                break

            # Process Command
            response = orchestrator.handle_input(command)
            print(f"\n🤖 Jarvis: {response}\n")
            tts.speak(response)
            
            # Loop continues automatically (Conversational Mode)

if __name__ == "__main__":
    main()