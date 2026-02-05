import os
import asyncio
import edge_tts
import pygame
import uuid
import threading

# VOICE CONFIGURATION
VOICE = "en-GB-RyanNeural"    # JARVIS

class TextToSpeech:
    def __init__(self):
        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(8)
        except Exception as e:
            print(f"⚠️ Audio driver warning: {e}")

    async def _generate_audio(self, text, output_file):
        communicate = edge_tts.Communicate(text, VOICE, rate="+20%") 
        await communicate.save(output_file)

    def speak(self, text):
        if not text: return

        filename = f"response_{uuid.uuid4().hex}.mp3"
        
        try:
            # CRITICAL FIX: Loop Detection
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # We are trapped in a loop! Spawn a thread to escape.
                t = threading.Thread(target=self._run_async_gen, args=(text, filename))
                t.start()
                t.join()
            else:
                # Safe to run normally
                asyncio.run(self._generate_audio(text, filename))

            # Play Audio
            if os.path.exists(filename):
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                pygame.mixer.music.unload()

        except Exception as e:
            print(f"❌ TTS Error: {e}")
        
        finally:
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except:
                pass

    def _run_async_gen(self, text, filename):
        """Helper to run async code in a fresh thread"""
        asyncio.run(self._generate_audio(text, filename))