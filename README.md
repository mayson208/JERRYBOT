# JERRY — Personal AI Assistant

> Your own personal AI companion. Responds to your voice, controls your PC, remembers everything, and actually has personality.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows%2011-lightgrey)
![AI](https://img.shields.io/badge/AI-Claude%20Sonnet-orange)
![Voice](https://img.shields.io/badge/Voice-ElevenLabs-purple)

---

## Features

- **Wake word** — Say "Hey Jerry" (or your configured wake word) to activate
- **Voice input** — OpenAI Whisper transcribes your speech locally (no API cost)
- **AI brain** — Claude Sonnet powers Jerry's responses with full personality
- **Realistic voice** — ElevenLabs gives Jerry a natural, expressive voice
- **Persistent memory** — Jerry remembers every conversation, even after reboots
- **Emotional personality** — Warm, witty, caring — a real AI best friend
- **PC control**:
  - Open browser and search Google
  - Launch apps (Chrome, Spotify, Discord, File Explorer, etc.)
  - Open games (Steam, Ubisoft Connect, Epic Games, EA App)
  - Take screenshots
  - Tell the time and date
  - Control per-app volume (raise, lower, mute Spotify, Discord, Chrome, etc.)
- **Dark futuristic UI** — Animated glowing orb, real-time transcript
- **Always-on-top HUD** — Small overlay that stays visible while gaming or working
- **Startup greeting** — Jerry greets you every time you launch, referencing how long you've been away

---

## Setup

### 1. Requirements

- Python 3.10+
- Windows 11 (tested) / Windows 10

### 2. Install dependencies

```bash
cd C:\Users\Rachel\Desktop\Coding\jerry
pip install -r requirements.txt
```

> **Note on PyAudio**: If `pip install pyaudio` fails, install it via:
> ```
> pip install pipwin
> pipwin install pyaudio
> ```

### 3. Get your API keys

| Key | Where to get it |
|-----|----------------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com/) |
| `ELEVENLABS_API_KEY` | [elevenlabs.io](https://elevenlabs.io/) → Profile → API Key |
| `ELEVENLABS_VOICE_ID` | ElevenLabs → Voice Library → your voice → Voice ID |
| `PORCUPINE_ACCESS_KEY` | [console.picovoice.ai](https://console.picovoice.ai/) — free account |

### 4. Configure `.env`

Edit the `.env` file and fill in your keys:

```env
ANTHROPIC_API_KEY=sk-ant-...
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...
PORCUPINE_ACCESS_KEY=...
```

### 5. (Optional) Custom wake word

By default Jerry uses `"bumblebee"` as the wake word (a built-in Picovoice keyword).

To use **"Hey Jerry"** specifically:
1. Go to [console.picovoice.ai](https://console.picovoice.ai/)
2. Create a custom wake word model for "Hey Jerry"
3. Download the `.ppn` file and place it in the project folder
4. In `listener.py`, change:
   ```python
   keywords=["bumblebee"]
   ```
   to:
   ```python
   keyword_paths=["hey_jerry.ppn"]
   ```

### 6. Run Jerry

```bash
python main.py
```

---

## Usage Examples

Say these after waking Jerry:

| You say | Jerry does |
|---------|-----------|
| "Search for the weather in New York" | Opens Google with the search |
| "Open Spotify" | Launches Spotify |
| "Open Valorant" | Finds and launches the game |
| "Lower Spotify's volume" | Turns Spotify down by 25% |
| "Mute Discord" | Mutes Discord audio |
| "Take a screenshot" | Saves a screenshot to your Desktop |
| "What time is it?" | Tells you the time and date |
| "Open my files" | Opens File Explorer |
| "Open Ubisoft Connect" | Launches Ubisoft launcher |

---

## Project Structure

```
jerry/
├── main.py         — PyQt5 UI, HUD overlay, startup greeting
├── brain.py        — Claude API + persistent memory + personality
├── voice.py        — ElevenLabs text-to-speech
├── listener.py     — Wake word detection + Whisper transcription
├── controller.py   — All PC actions (apps, games, volume, etc.)
├── config.py       — Settings and .env loader
├── memory.json     — Conversation history (auto-created, persists forever)
├── requirements.txt
├── .env            — Your API keys (never committed)
└── .gitignore
```

---

## Memory

Jerry's memory lives in `memory.json`. It stores the full conversation history and is loaded every time Jerry starts up. Jerry will remember:
- Things you've told him about yourself
- Past conversations and context
- Your preferences and habits

To wipe Jerry's memory: click the **Clear Memory** button in the UI, or delete `memory.json`.

---

## Troubleshooting

**PyAudio won't install**
```bash
pip install pipwin && pipwin install pyaudio
```

**Whisper is slow**
Change `WHISPER_MODEL = "tiny"` in `config.py` for faster (less accurate) transcription.

**ElevenLabs audio not playing**
Make sure `pygame` is installed and your `ELEVENLABS_VOICE_ID` is correct.

**Wake word not triggering**
Check your `PORCUPINE_ACCESS_KEY` is valid and your microphone is set as the default input device.
