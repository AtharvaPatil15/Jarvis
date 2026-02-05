# assistant/voice/stt.py
import speech_recognition as sr

class SpeechToText:
    def __init__(self, device_index=None):
        self.recognizer = sr.Recognizer()
        self.device_index = device_index
        
        # ⚡ SPEED TUNING ⚡
        # How long of silence (in seconds) counts as "end of sentence"
        # Default is 0.8. Lowering to 0.6 makes it respond faster.
        self.recognizer.pause_threshold = 0.6 
        
        # Minimum length of speaking to consider a phrase (filters noise)
        self.recognizer.phrase_threshold = 0.3
        
        # Non-speaking duration buffers (keep these low)
        self.recognizer.non_speaking_duration = 0.4

        # Dynamic energy adjustment (prevents getting stuck listening to background noise)
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 400  # Starting baseline

    def listen(self, duration=None) -> str | None:
        """
        Listens to the microphone and converts speech to text.
        Returns: The recognized text (str) or None if failed.
        """
        try:
            with sr.Microphone(device_index=self.device_index) as source:
                # Quick ambient noise adjustment (only 0.5s instead of default 1s)
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                print("🎤 Listening...", end="\r")
                
                # Listen with a timeout so it doesn't hang forever
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=duration)
                except sr.WaitTimeoutError:
                    return None

                if not audio:
                    return None

                print("⏳ Processing...", end="\r")
                text = self.recognizer.recognize_google(audio)  # type: ignore
                return text

        except sr.UnknownValueError:
            return None # Heard sound but couldn't understand
        except sr.RequestError:
            print("❌ STT Error: Internet/API down")
            return None
        except Exception as e:
            # print(f"❌ STT Error: {e}") # Silent fail to keep console clean
            return None
