"""
listener.py — Wake word detection and speech-to-text for JERRY.

Uses pvporcupine for "Hey Jerry" wake word detection (requires free Picovoice key).
After wake word, records audio and transcribes with OpenAI Whisper (runs locally, no API cost).
Runs entirely on a background thread — never blocks the UI.
"""

import io
import struct
import threading
import time
import wave
from pathlib import Path

import numpy as np
import pyaudio

import config

TEMP_WAV = Path(__file__).parent / "_tmp_recording.wav"


class Listener:
    """
    Continuously listens for the wake word, then records and transcribes speech.

    Callbacks:
        on_wake_word()              — fired when "Hey Jerry" is detected
        on_transcribed(text: str)   — fired with transcribed command text
        on_error(msg: str)          — fired on errors
    """

    def __init__(self, on_wake_word=None, on_transcribed=None, on_error=None):
        self.on_wake_word   = on_wake_word   or (lambda: None)
        self.on_transcribed = on_transcribed or (lambda t: None)
        self.on_error       = on_error       or (lambda e: None)

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._whisper_model = None
        self._porcupine = None

    def start(self):
        """Start the listener thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        """Signal the listener to stop."""
        self._stop_event.set()

    def _load_whisper(self):
        if self._whisper_model is None:
            import whisper
            self._whisper_model = whisper.load_model(config.WHISPER_MODEL)

    def _run(self):
        try:
            import pvporcupine
        except ImportError:
            self.on_error("pvporcupine not installed. Run: pip install pvporcupine")
            return

        try:
            porcupine = pvporcupine.create(
                access_key=config.PORCUPINE_ACCESS_KEY,
                keywords=["hey siri"],   # closest built-in; see note below
            )
        except Exception as e:
            self.on_error(f"Porcupine init error: {e}")
            return

        # NOTE: Picovoice free tier has built-in keywords like "hey siri", "alexa", "ok google",
        # "porcupine", "bumblebee", "blueberry", "grapefruit", "grasshopper", "americano".
        # For a custom "Hey Jerry" wake word you need a custom .ppn model from console.picovoice.ai.
        # By default we use "bumblebee" as a stand-in — change to your custom .ppn file path.
        # To use custom model: pvporcupine.create(access_key=..., keyword_paths=["hey_jerry.ppn"])

        audio = pyaudio.PyAudio()
        stream = audio.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length,
        )

        print("[Listener] Waiting for wake word...")

        try:
            while not self._stop_event.is_set():
                pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm)
                result = porcupine.process(pcm_unpacked)

                if result >= 0:
                    print("[Listener] Wake word detected!")
                    self.on_wake_word()
                    self._record_and_transcribe(audio)
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
            porcupine.delete()

    def _record_and_transcribe(self, audio: pyaudio.PyAudio):
        """Record until silence, then transcribe with Whisper."""
        print("[Listener] Recording...")

        stream = audio.open(
            rate=config.SAMPLE_RATE,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=1024,
        )

        frames = []
        silent_chunks = 0
        max_silent_chunks = 20   # ~1.3s of silence stops recording
        max_chunks = int(config.SAMPLE_RATE / 1024 * config.RECORD_SECONDS)

        for _ in range(max_chunks):
            if self._stop_event.is_set():
                break
            data = stream.read(1024, exception_on_overflow=False)
            frames.append(data)
            amplitude = max(struct.unpack("h" * (len(data) // 2), data), key=abs)
            if abs(amplitude) < config.SILENCE_THRESHOLD:
                silent_chunks += 1
                if silent_chunks >= max_silent_chunks:
                    break
            else:
                silent_chunks = 0

        stream.stop_stream()
        stream.close()

        if not frames:
            return

        # Save to temp WAV
        with wave.open(str(TEMP_WAV), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(config.SAMPLE_RATE)
            wf.writeframes(b"".join(frames))

        # Transcribe
        try:
            self._load_whisper()
            result = self._whisper_model.transcribe(str(TEMP_WAV), language="en")
            text = result.get("text", "").strip()
            if text:
                print(f"[Listener] Transcribed: {text}")
                self.on_transcribed(text)
            else:
                print("[Listener] Empty transcription.")
        except Exception as e:
            self.on_error(f"Whisper transcription error: {e}")
        finally:
            if TEMP_WAV.exists():
                TEMP_WAV.unlink()
