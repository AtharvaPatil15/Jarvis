import os
import asyncio
import edge_tts
import pygame
import uuid
import threading
import time

# VOICE CONFIGURATION
VOICE = "en-GB-RyanNeural"  # Jarvis Voice
# VOICE = "en-IE-EmilyNeural" # Friday Voice

class TextToSpeech:
    def __init__(self):
        try:
            # 1. Force higher quality buffer to match EdgeTTS (24kHz)
            # This often fixes the "Chipmunk" or "Silent" glitch
            pygame.mixer.pre_init(24000, -16, 2, 2048)
            pygame.mixer.init()
            pygame.mixer.music.set_volume(1.0) # Force Max Volume
            print("🔊 Audio System Initialized")
        except Exception as e:
            print(f"❌ Audio Driver Error: {e}")

    async def _generate_audio(self, text, output_file):
        try:
            # +20% speed for snappier responses
            communicate = edge_tts.Communicate(text, VOICE, rate="+20%") 
            await communicate.save(output_file)
            return True
        except Exception as e:
            print(f"❌ EdgeTTS Generation Error: {e}")
            return False

    def speak(self, text):
        if not text: return

        # Unique filename to prevent file locking issues
        filename = f"speech_{uuid.uuid4().hex}.mp3"
        file_generated = False

        print(f"🗣️ Jarvis Saying: {text}")

        try:
            # A. GENERATION (Thread-Safe Wrapper)
            # Check if we are already in an Async Loop (FastAPI crash fix)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # We are in a loop (Server), so spawn a thread to run the async generator
                t = threading.Thread(target=self._run_async_gen, args=(text, filename))
                t.start()
                t.join()
                file_generated = os.path.exists(filename)
            else:
                # We are in a normal thread (Voice Controller), run normally
                file_generated = asyncio.run(self._generate_audio(text, filename))

            # B. PLAYBACK
            if file_generated and os.path.exists(filename):
                print(f"🔊 Playing Audio ({os.path.getsize(filename)} bytes)...")
                
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()
                
                # Wait for audio to finish
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                
                # Cleanup
                pygame.mixer.music.unload()
                print("✅ Audio Finished")
            else:
                print("❌ Audio File Generation Failed (Check Internet?)")

        except Exception as e:
            print(f"❌ Playback Error: {e}")
        
        finally:
            # Clean up the temp file
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except:
                pass

    def _run_async_gen(self, text, filename):
        """Helper to run async code in a fresh thread"""
        asyncio.run(self._generate_audio(text, filename))