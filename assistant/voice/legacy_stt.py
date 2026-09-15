import speech_recognition as sr


class SpeechToText:

    def __init__(self, device_index=None):
        self.device_index = device_index
        self.recognizer = sr.Recognizer()

        # Better real-world tuning
        self.recognizer.pause_threshold = 0.8
        self.recognizer.energy_threshold = 300

    def listen_until_silence(self):

        try:
            with sr.Microphone(device_index=self.device_index) as source:

                print("🎤 Listening...")

                audio = self.recognizer.listen(
                    source,
                    timeout=5,           # wait for user to begin speaking
                    phrase_time_limit=12 # allow natural speech
                )

                text = self.recognizer.recognize_google(audio)
                print("🗣 User:", text)

                return text

        except sr.WaitTimeoutError:
            print("⏱ No speech detected")
            return None

        except Exception as e:
            print("STT Error:", e)
            return None
