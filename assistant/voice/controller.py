"""Hands-free loop: wake word -> utterance -> transcript -> streamed reply spoken aloud, with barge-in."""
from __future__ import annotations

import asyncio
import logging
import math
import threading
from collections.abc import Awaitable, Callable
from typing import Any

import numpy as np

from assistant.events import AssistantState, Emit, EventType
from assistant.voice.audio_io import FRAME_SECONDS, AudioSink, AudioSource
from assistant.voice.echo import EchoGuard
from assistant.voice.tts import SentenceBuffer, split_sentences

log = logging.getLogger("jarvis.voice")

Handler = Callable[[str, Callable[[str], None]], Awaitable[str]]
FAILURE_REPLY = "Sorry, something went wrong."


class VoiceController:
    def __init__(self, source: AudioSource, sink: AudioSink, wake: Any, segmenter: Any, stt: Any, tts: Any,
                 handler: Handler, emit: Emit, follow_up_s: float = 6.0, barge_in_ms: int = 300,
                 echo: EchoGuard | None = None) -> None:
        self._source, self._sink, self._wake, self._segmenter = source, sink, wake, segmenter
        self._stt, self._tts, self._handler, self._emit = stt, tts, handler, emit
        self._follow_up_s = follow_up_s
        self._barge_frames = max(1, math.ceil(barge_in_ms / (FRAME_SECONDS * 1000)))
        self._echo = echo or EchoGuard()
        self._frames: asyncio.Queue[np.ndarray | None] = asyncio.Queue()
        self._listening = False
        self._audio_clock = 0.0
        self._deadline = 0.0

    async def run(self, stop: asyncio.Event) -> None:
        loop = asyncio.get_running_loop()
        self._frames = asyncio.Queue()
        threading.Thread(target=self._read_source, args=(loop, stop), name="voice-source", daemon=True).start()
        self._emit(EventType.STATE_CHANGE, AssistantState.IDLE)
        while True:
            frame = await self._next_frame(stop)
            if frame is None:
                break
            utterance = self._consume(frame)
            if utterance is not None:
                await self._handle_utterance(utterance, stop)

    async def speak(self, text: str) -> None:
        for sentence in split_sentences(text):
            samples, rate = await asyncio.to_thread(self._tts.synthesize, sentence)
            if len(samples):
                self._echo.note_spoken(sentence)
                self._sink.play(samples, rate)
        await asyncio.to_thread(self._sink.wait)

    def _read_source(self, loop: asyncio.AbstractEventLoop, stop: asyncio.Event) -> None:
        try:
            for frame in self._source.frames():
                if stop.is_set():
                    break
                loop.call_soon_threadsafe(self._frames.put_nowait, frame)
        except Exception:
            log.exception("audio source failed")
        finally:
            try:
                loop.call_soon_threadsafe(self._frames.put_nowait, None)
            except RuntimeError:
                pass

    async def _next_frame(self, stop: asyncio.Event) -> np.ndarray | None:
        while not stop.is_set():
            try:
                frame = await asyncio.wait_for(self._frames.get(), timeout=0.25)
            except asyncio.TimeoutError:
                continue
            if frame is not None:
                self._audio_clock += FRAME_SECONDS
            return frame
        return None

    def _open_window(self) -> None:
        self._listening = True
        self._deadline = self._audio_clock + self._follow_up_s
        self._emit(EventType.STATE_CHANGE, AssistantState.LISTENING)

    def _consume(self, frame: np.ndarray) -> np.ndarray | None:
        if not self._listening:
            if self._wake.detected(frame):
                self._wake.reset()
                self._segmenter.reset()
                self._emit(EventType.WAKE_WORD_DETECTED, None)
                self._open_window()
            return None
        utterance = self._segmenter.feed(frame)
        if utterance is None and not self._segmenter.speech_active and self._audio_clock > self._deadline:
            self._listening = False
            self._wake.reset()
            self._emit(EventType.STATE_CHANGE, AssistantState.IDLE)
        return utterance

    async def _handle_utterance(self, utterance: np.ndarray, stop: asyncio.Event) -> None:
        text = (await asyncio.to_thread(self._stt.transcribe, utterance)).strip()
        if not text or self._echo.is_echo(text):
            self._deadline = self._audio_clock + self._follow_up_s
            return
        self._emit(EventType.USER_TRANSCRIPT, text)
        interruption = await self._respond(text, stop)
        self._segmenter.reset()
        self._open_window()
        for frame in interruption or []:
            self._segmenter.feed(frame)

    async def _respond(self, text: str, stop: asyncio.Event) -> list[np.ndarray] | None:
        loop = asyncio.get_running_loop()
        sentences: asyncio.Queue[str | None] = asyncio.Queue()
        buffer = SentenceBuffer()
        streamed = False

        def on_delta(chunk: str) -> None:
            nonlocal streamed
            streamed = True
            for sentence in buffer.push(chunk):
                loop.call_soon_threadsafe(sentences.put_nowait, sentence)

        async def produce() -> None:
            try:
                reply = await self._handler(text, on_delta)
                remainder = buffer.flush() if streamed else split_sentences(reply)
            except Exception:
                log.exception("voice handler failed")
                remainder = [*buffer.flush(), FAILURE_REPLY]
            # Use the same scheduling channel as on_delta: a direct put_nowait here would overtake sentences that
            # on_delta scheduled with call_soon_threadsafe but the loop has not run yet.
            for sentence in remainder:
                loop.call_soon_threadsafe(sentences.put_nowait, sentence)
            loop.call_soon_threadsafe(sentences.put_nowait, None)

        producer = asyncio.create_task(produce())
        try:
            while True:
                sentence = await sentences.get()
                if sentence is None:
                    return None
                samples, rate = await asyncio.to_thread(self._tts.synthesize, sentence)
                if not len(samples):
                    continue
                self._echo.note_spoken(sentence)
                self._sink.play(samples, rate)
                interruption = await self._watch_for_barge_in(stop)
                if interruption is not None:
                    self._sink.stop()
                    self._emit(EventType.STATE_CHANGE, AssistantState.LISTENING)
                    log.info("barge-in after %d speech frames", len(interruption))
                    return interruption
        finally:
            if not producer.done():
                producer.add_done_callback(lambda task: None if task.cancelled() else task.exception())

    async def _watch_for_barge_in(self, stop: asyncio.Event) -> list[np.ndarray] | None:
        run: list[np.ndarray] = []
        while self._sink.is_playing and not stop.is_set():
            try:
                frame = await asyncio.wait_for(self._frames.get(), timeout=0.05)
            except asyncio.TimeoutError:
                continue
            if frame is None:
                self._frames.put_nowait(None)
                while self._sink.is_playing and not stop.is_set():
                    await asyncio.sleep(0.02)
                return None
            self._audio_clock += FRAME_SECONDS
            if self._segmenter.is_speech(frame):
                run.append(frame)
                if len(run) >= self._barge_frames:
                    return run
            else:
                run = []
        return None
