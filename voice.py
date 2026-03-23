"""
voice.py — ElevenLabs text-to-speech for JERRY.

Converts text to audio using ElevenLabs and plays it back.
Runs in a background thread to avoid blocking the UI.
"""

import io
import threading

import pygame

import config

# ── Init pygame mixer ──────────────────────────────────────────────────────────

pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)

# ── Global speaking state ──────────────────────────────────────────────────────

_speaking = False
_speak_lock = threading.Lock()


def is_speaking() -> bool:
    return _speaking


def speak(text: str, on_start=None, on_done=None):
    """
    Convert text to speech via ElevenLabs and play it.
    Non-blocking — runs on a background thread.

    Args:
        text:     The text to speak.
        on_start: Optional callback fired when audio starts playing.
        on_done:  Optional callback fired when audio finishes.
    """
    t = threading.Thread(target=_speak_worker, args=(text, on_start, on_done), daemon=True)
    t.start()


def _speak_worker(text: str, on_start=None, on_done=None):
    global _speaking
    with _speak_lock:
        _speaking = True
        if on_start:
            on_start()
        try:
            if config.ELEVENLABS_API_KEY and config.ELEVENLABS_VOICE_ID:
                _speak_elevenlabs(text)
            else:
                _speak_system_fallback(text)
        except Exception as e:
            print(f"[Voice] TTS error: {e}")
            _speak_system_fallback(text)
        finally:
            _speaking = False
            if on_done:
                on_done()


def _speak_elevenlabs(text: str):
    """Play audio via ElevenLabs TTS."""
    from elevenlabs import ElevenLabs
    client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)
    audio_generator = client.text_to_speech.convert(
        voice_id=config.ELEVENLABS_VOICE_ID,
        text=text,
        model_id="eleven_monolingual_v1",
        voice_settings={
            "stability": 0.4,
            "similarity_boost": 0.85,
            "style": 0.3,
            "use_speaker_boost": True,
        },
    )
    audio_bytes = b"".join(audio_generator)
    audio_file = io.BytesIO(audio_bytes)
    pygame.mixer.music.load(audio_file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.wait(100)


def _speak_system_fallback(text: str):
    """Fallback TTS using Windows SAPI (pyttsx3) when ElevenLabs is unavailable."""
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", 175)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except Exception as e:
        print(f"[Voice] Fallback TTS also failed: {e}")


def stop():
    """Stop any currently playing audio."""
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass
