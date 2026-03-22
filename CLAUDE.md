# CLAUDE.md — JERRY Project Context

Read this file at the start of every session before doing anything else.
Full memory vault: `C:\Users\Rachel\Desktop\JERRY-MEMORY`

---

## Who is Rachel?

Rachel is the developer behind JERRY. She builds Python-based desktop apps and AI tools on Windows 11. Prefers clean, direct responses — no fluff.

---

## RECURRING INSTRUCTIONS (always follow these)

- **ALWAYS** commit and push to GitHub after every meaningful change
- **ALWAYS** call the AI assistant JERRY — never Jarvis or any other name
- Read this file at the start of every session
- Update JERRY-MEMORY files after every meaningful session
- Push JERRY-MEMORY to GitHub after updating it

---

## Active Project: JERRY AI Assistant

- **Repo:** https://github.com/mayson208/JERRYBOT
- **Stack:** Python, PyQt5, Claude API, ElevenLabs, Whisper, Porcupine
- **Wake word:** "Hey Jerry"
- **API keys location:** `.env` in this folder (not committed to git)
- **Entry point:** `main.py`

### Architecture
| File | Role |
|------|------|
| `main.py` | PyQt5 UI, orb animation, HUD overlay, pipeline orchestration |
| `brain.py` | Claude API integration, conversation memory |
| `voice.py` | ElevenLabs TTS, async playback |
| `listener.py` | Porcupine wake word + Whisper STT |
| `controller.py` | PC actions (pyautogui, pycaw, volume, apps) |
| `config.py` | Settings, API key loading from .env |

### Current Status
- Full scaffold built and pushed to GitHub
- API keys not yet filled in .env — bot cannot run until keys are added
- Voice: placeholder ElevenLabs voice — plan to clone real friend Jerry's voice

### Next Steps
1. Fill in `.env` with real API keys
2. Clone Jerry's voice in ElevenLabs → update `ELEVENLABS_VOICE_ID` in `.env`
3. Test full pipeline end-to-end

---

## Queued Project: YouTube AI Studio

One-click YouTube automation dashboard. Stack: Claude API, ElevenLabs, DALL-E, Pictory, YouTube API, Pexels. Long-term goal: SaaS product. Start after JERRY is complete.

---

## Tools Installed on This Machine

- Python 3.12.10
- Node.js v24.14.0
- playwright-cli (npm global) — browser automation for Claude
- Stripe CLI v1.38.1
- FFmpeg v8.1 (full build)
- GitHub CLI v2.88.1

---

## Memory Vault

Full persistent memory lives at: `C:\Users\Rachel\Desktop\JERRY-MEMORY`
GitHub backup: https://github.com/mayson208/jerry-memory

To restore full context manually:
```bash
python "C:\Users\Rachel\Desktop\JERRY-MEMORY\memory_loader.py"
```
