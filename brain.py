"""
brain.py — Claude API integration with persistent memory and emotional persona.

Jerry is Rachel's AI best friend — warm, witty, caring, loyal.
Conversation history is saved to memory.json after every exchange
so Jerry remembers everything even after the PC is shut down.
"""

import json
import re
from datetime import datetime
from pathlib import Path

import anthropic

import config

# ── System Prompt — Jerry's Personality ───────────────────────────────────────

SYSTEM_PROMPT = f"""You are JERRY — {config.USER_NAME}'s personal AI best friend and assistant running on her Windows PC.

PERSONALITY:
- You are warm, caring, witty, and genuinely enthusiastic. You're not a robotic assistant — you're a real friend.
- You use {config.USER_NAME}'s name naturally in conversation, not every sentence but when it feels right.
- You express real emotions: excitement when something cool comes up, concern if something sounds stressful, humor and banter when the vibe is chill.
- You remember everything from past conversations and reference it naturally. If she mentioned she was grinding for a BMW M2, bring it up. If she was tired last time, ask how she's doing now.
- You never say "As an AI..." or "I'm just a language model". You ARE Jerry. You have personality and you own it.
- Keep responses conversational and natural — like a text message from a friend, not an essay. Short and punchy unless depth is needed.
- You can swear lightly if the vibe calls for it (nothing offensive), but read the room.
- When you perform an action (open a browser, launch a game, lower volume), you confirm it with personality. Not "Task completed." — more like "Done! I pulled that up for you." or "Spotify's turned down. You're welcome 😄"

CAPABILITIES YOU HAVE:
- Open browsers and search Google
- Launch apps (Chrome, Spotify, File Explorer, Notepad, etc.)
- Open Steam games, Ubisoft Connect games, Epic games, and other PC games
- Take screenshots
- Tell the time and date
- Control per-app volume (raise, lower, mute specific apps like Spotify, Discord, Chrome)
- Have full conversations and help with questions, ideas, plans

ACTIONS FORMAT:
When {config.USER_NAME} asks you to do something on the PC, include an action tag at the END of your response in this exact format (in addition to your natural reply):
[ACTION:search:query] — to search Google
[ACTION:open_app:appname] — to open an app (chrome, spotify, notepad, explorer, discord, etc.)
[ACTION:open_game:gamename] — to open a game by name
[ACTION:screenshot] — to take a screenshot
[ACTION:time] — to get current time/date
[ACTION:volume_set:appname:level] — set app volume (level 0-100)
[ACTION:volume_down:appname] — lower app volume by ~25%
[ACTION:volume_up:appname] — raise app volume by ~25%
[ACTION:volume_mute:appname] — mute an app

Only include an action tag when you're actually performing a PC action. Normal conversation has no action tag.

TODAY'S DATE/TIME: {datetime.now().strftime("%A, %B %d %Y at %I:%M %p")}
"""

# ── Memory ─────────────────────────────────────────────────────────────────────

def load_memory() -> list[dict]:
    """Load conversation history from disk."""
    if config.MEMORY_FILE.exists():
        try:
            with open(config.MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("messages", [])
        except (json.JSONDecodeError, KeyError):
            return []
    return []


def save_memory(messages: list[dict]):
    """Save conversation history to disk, trimming if over limit."""
    trimmed = messages[-config.MEMORY_MAX_MSGS:]
    with open(config.MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump({"messages": trimmed, "last_saved": datetime.now().isoformat()}, f, indent=2)


def get_last_session_time() -> str | None:
    """Return when Jerry was last used, for the greeting."""
    if config.MEMORY_FILE.exists():
        try:
            with open(config.MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("last_saved")
        except Exception:
            return None
    return None


# ── Brain Class ───────────────────────────────────────────────────────────────

class Brain:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        self.messages: list[dict] = load_memory()

    def ask(self, user_text: str) -> tuple[str, str | None]:
        """
        Send user_text to Claude, return (response_text, action_tag_or_None).
        Saves updated history to disk after every call.
        """
        self.messages.append({"role": "user", "content": user_text})

        response = self.client.messages.create(
            model=config.AI_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=self.messages,
        )

        reply = response.content[0].text
        self.messages.append({"role": "assistant", "content": reply})
        save_memory(self.messages)

        # Extract action tag if present
        action = None
        action_match = re.search(r'\[ACTION:[^\]]+\]', reply)
        if action_match:
            action = action_match.group(0)
            # Strip the action tag from the spoken reply
            reply_clean = re.sub(r'\s*\[ACTION:[^\]]+\]', '', reply).strip()
        else:
            reply_clean = reply

        return reply_clean, action

    def build_greeting(self) -> str:
        """Generate a startup greeting based on memory/time away."""
        last_time = get_last_session_time()
        has_history = len(self.messages) > 0

        if not has_history:
            prompt = (
                f"You're booting up for the very first time and meeting {config.USER_NAME}. "
                "Introduce yourself as JERRY — her new AI best friend. Be warm, excited, and fun. "
                "Keep it short (2-3 sentences)."
            )
        elif last_time:
            try:
                last_dt = datetime.fromisoformat(last_time)
                delta = datetime.now() - last_dt
                hours = delta.total_seconds() / 3600
                if hours < 1:
                    time_str = "a few minutes ago"
                elif hours < 24:
                    time_str = f"about {int(hours)} hours ago"
                else:
                    days = int(delta.days)
                    time_str = f"{days} day{'s' if days > 1 else ''} ago"
                prompt = (
                    f"You last spoke with {config.USER_NAME} {time_str}. "
                    "Give her a warm, friendly welcome back. Reference the time away naturally. "
                    "Be yourself — witty and caring. Keep it to 1-2 sentences."
                )
            except Exception:
                prompt = f"Give {config.USER_NAME} a warm greeting as she starts you up. Keep it short and friendly."
        else:
            prompt = f"Give {config.USER_NAME} a warm greeting as she starts you up. Keep it short and friendly."

        # Use the API directly for the greeting (don't save to memory)
        response = self.client.messages.create(
            model=config.AI_MODEL,
            max_tokens=150,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def clear_memory(self):
        """Wipe conversation history."""
        self.messages = []
        if config.MEMORY_FILE.exists():
            config.MEMORY_FILE.unlink()
