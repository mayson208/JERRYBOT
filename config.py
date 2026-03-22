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

# ── Jerry Settings ────────────────────────────────────────────────────────────

JERRY_NAME        = "Jerry"
USER_NAME         = "Rachel"
AI_MODEL          = "claude-sonnet-4-20250514"
MEMORY_FILE       = BASE_DIR / "memory.json"
MEMORY_MAX_MSGS   = 200        # max messages to keep in memory.json
WHISPER_MODEL     = "base"     # tiny / base / small / medium / large
WAKE_WORD         = "hey jerry"

# ── Audio ─────────────────────────────────────────────────────────────────────

SAMPLE_RATE       = 16000
RECORD_SECONDS    = 8          # max seconds to record after wake word
SILENCE_THRESHOLD = 500        # amplitude threshold to detect silence

# ── UI ────────────────────────────────────────────────────────────────────────

BG_COLOR          = "#0a0a1a"
ACCENT_COLOR      = "#00d4ff"
TEXT_COLOR        = "#ffffff"
JERRY_TEXT_COLOR  = "#00d4ff"
FONT_FAMILY       = "Segoe UI"

# ── Validation ────────────────────────────────────────────────────────────────

def validate_keys():
    """Warn at startup if any API keys are missing."""
    missing = []
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not ELEVENLABS_API_KEY:
        missing.append("ELEVENLABS_API_KEY")
    if not ELEVENLABS_VOICE_ID:
        missing.append("ELEVENLABS_VOICE_ID")
    if not PORCUPINE_ACCESS_KEY:
        missing.append("PORCUPINE_ACCESS_KEY")
    return missing
