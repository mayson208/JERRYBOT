"""
config.py — Centralised settings and environment variable loader for JERRY.

All modules import from here. Never hardcode keys anywhere else.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env ─────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

# ── API Keys ──────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY    = os.getenv("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY   = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID  = os.getenv("ELEVENLABS_VOICE_ID", "")
PORCUPINE_ACCESS_KEY = os.getenv("PORCUPINE_ACCESS_KEY", "")
OPENAI_API_KEY       = os.getenv("OPENAI_API_KEY", "")     # optional — for Whisper API fallback

# ── Jerry Settings ────────────────────────────────────────────────────────────

JERRY_NAME        = "Jerry"
USER_NAME         = "Rachel"
AI_MODEL          = os.getenv("AI_MODEL", "claude-sonnet-4-20250514")
MEMORY_FILE       = BASE_DIR / "memory.json"
MEMORY_MAX_MSGS   = int(os.getenv("MEMORY_MAX_MSGS", "200"))
WHISPER_MODEL     = os.getenv("WHISPER_MODEL", "base")   # tiny/base/small/medium/large
WAKE_WORD         = os.getenv("WAKE_WORD", "hey jerry")

# ── Audio ─────────────────────────────────────────────────────────────────────

SAMPLE_RATE       = int(os.getenv("SAMPLE_RATE", "16000"))
RECORD_SECONDS    = int(os.getenv("RECORD_SECONDS", "8"))
SILENCE_THRESHOLD = int(os.getenv("SILENCE_THRESHOLD", "500"))

# ── UI ────────────────────────────────────────────────────────────────────────

BG_COLOR          = "#0a0a1a"
ACCENT_COLOR      = "#00d4ff"
TEXT_COLOR        = "#ffffff"
JERRY_TEXT_COLOR  = "#00d4ff"
FONT_FAMILY       = "Segoe UI"

# ── Validation ────────────────────────────────────────────────────────────────

def validate_keys() -> list[str]:
    """Return list of missing required API keys."""
    required = {
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
        "ELEVENLABS_API_KEY": ELEVENLABS_API_KEY,
        "ELEVENLABS_VOICE_ID": ELEVENLABS_VOICE_ID,
        "PORCUPINE_ACCESS_KEY": PORCUPINE_ACCESS_KEY,
    }
    return [name for name, value in required.items() if not value]
