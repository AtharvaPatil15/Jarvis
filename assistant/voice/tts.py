import asyncio
import edge_tts
import pygame
import uuid
import os

VOICE = "en-GB-RyanNeural"

class TextToSpeech:

    def __init__(self):
        pygame.mixer.init()

    async def _stream_tts(self, text, filename):
        communicate = edge_tts.Communicate(text, VOICE, rate="+20%")

        with open(filename, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])

    def speak(self, text):
        if not text:
            return

        filename = f"response_{uuid.uuid4().hex}.mp3"

        try:
            asyncio.run(self._stream_tts(text, filename))

            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()

        except Exception as e:
            print("TTS Error:", e)

        finally:
            # Cleanup later in background
            asyncio.run(self._cleanup_file(filename))

    async def _cleanup_file(self, filename):
        await asyncio.sleep(5)
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass
