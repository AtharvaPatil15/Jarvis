import os
import pvporcupine
import sounddevice as sd
import numpy as np
import sys

class WakeWordListener:
    def __init__(self, access_key: str, keyword="computer", device_index=None, sensitivity=0.9):
        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=[keyword],
            sensitivities=[sensitivity] # Increased sensitivity (0.0 to 1.0)
        )
        self.device_index = device_index
        self.sample_rate = self.porcupine.sample_rate
        self.frame_length = self.porcupine.frame_length
        self.frame_count = 0
        self.keyword = keyword

        print(f"🔧 Wake word engine initialized")
        print(f"🔧 Keyword        : {self.keyword}")
        print(f"🔧 Sensitivity    : {sensitivity}")
        print(f"🔧 Device index   : {self.device_index}")

    def listen(self) -> bool:
        """
        Opens the stream ONCE and loops internally until the wake word is detected.
        Returns True when 'computer' is heard.
        """
        print(f"👂 Listening for '{self.keyword}'...") 
        
        try:
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self.frame_length,
                device=self.device_index
            ) as stream:
                
                while True:
                    audio, _ = stream.read(self.frame_length)
                    self.frame_count += 1

                    # 1. Check Amplitude (Debug)
                    max_amplitude = float(np.max(np.abs(audio)))
                    
                    if self.frame_count % 20 == 0:
                        print(f"🎧 Amp: {max_amplitude:.4f}", end="\r")

                    # 2. Process with Porcupine
                    pcm = np.clip(audio[:, 0], -1.0, 1.0)
                    pcm = (pcm * 32767).astype(np.int16)

                    result = self.porcupine.process(pcm.tolist())

                    if result >= 0:
                        print(f"\n✅ WAKE WORD DETECTED (Index: {result})")
                        return True

        except KeyboardInterrupt:
            print("\n🛑 Stopping listener...")
            return False
        except Exception as e:
            print(f"\n❌ Wake-word audio error: {e}")
            return False


# Simplified engine for the new voice controller
class WakeWordEngine:
    def __init__(self):
        # This is a simplified stub that uses the same wake word listener
        self.listener = WakeWordListener(
            access_key=os.environ.get("JARVIS_PORCUPINE_ACCESS_KEY", ""),
            keyword="computer"
        )
    
    def wait_for_wake(self):
        """Waits for wake word to be detected"""
        return self.listener.listen()
