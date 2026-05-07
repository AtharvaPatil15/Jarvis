import asyncio
import os
import threading
import uuid

import edge_tts
import pygame

from jarvis_backend.paths import AUDIO_DIR, ensure_runtime_dirs


VOICE = "en-GB-RyanNeural"


class TextToSpeech:
    def __init__(self):
        try:
            pygame.mixer.pre_init(24000, -16, 2, 2048)
            pygame.mixer.init()
            pygame.mixer.music.set_volume(1.0)
        except Exception as exc:
            print(f"Audio driver error: {exc}")

    async def _generate_audio(self, text, output_file):
        try:
            communicate = edge_tts.Communicate(text, VOICE, rate="+20%")
            await communicate.save(output_file)
            return True
        except Exception as exc:
            print(f"EdgeTTS generation error: {exc}")
            return False

    def speak(self, text):
        if not text:
            return

        ensure_runtime_dirs()
        filename = str(AUDIO_DIR / f"speech_{uuid.uuid4().hex}.mp3")
        file_generated = False

        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                thread = threading.Thread(target=self._run_async_gen, args=(text, filename))
                thread.start()
                thread.join()
                file_generated = os.path.exists(filename)
            else:
                file_generated = asyncio.run(self._generate_audio(text, filename))

            if file_generated and os.path.exists(filename):
                pygame.mixer.music.load(filename)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                pygame.mixer.music.unload()
            else:
                print("Audio file generation failed.")
        except Exception as exc:
            print(f"Playback error: {exc}")
        finally:
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except OSError:
                pass

    def _run_async_gen(self, text, filename):
        asyncio.run(self._generate_audio(text, filename))
