"""
controller.py — PC action executor for JERRY.

Handles all system actions: browser search, app launching,
game launching (Steam/Ubisoft/Epic/EA), volume control, screenshots.
"""

import os
import re
import subprocess
import threading
import webbrowser
import winreg
from datetime import datetime
from pathlib import Path

import pyautogui

import config

# ── Command History ─────────────────────────────────────────────────────────────
_command_history: list[dict] = []
_HISTORY_MAX = 20


def record_command(command: str, result: str = ""):
    """Record a command to the in-session history."""
    _command_history.append({
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "command": command,
        "result": result,
    })
    if len(_command_history) > _HISTORY_MAX:
        _command_history.pop(0)


def get_command_history() -> list[dict]:
    """Return the last N commands executed this session."""
    return list(_command_history)

# ── App path lookup ───────────────────────────────────────────────────────────

COMMON_APPS = {
    "chrome":       r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "google chrome":r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "spotify":      os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
    "discord":      os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe"),
    "notepad":      "notepad.exe",
    "explorer":     "explorer.exe",
    "file explorer":"explorer.exe",
    "calculator":   "calc.exe",
    "task manager": "taskmgr.exe",
    "steam":        r"C:\Program Files (x86)\Steam\steam.exe",
    "ubisoft":      r"C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\UbisoftConnect.exe",
    "ubisoft connect": r"C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\UbisoftConnect.exe",
    "epic":         r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe",
    "epic games":   r"C:\Program Files (x86)\Epic Games\Launcher\Portal\Binaries\Win32\EpicGamesLauncher.exe",
    "ea":           r"C:\Program Files\Electronic Arts\EA Desktop\EA Desktop\EADesktop.exe",
    "ea app":       r"C:\Program Files\Electronic Arts\EA Desktop\EA Desktop\EADesktop.exe",
    "youtube":      None,   # handled specially — opens in browser
    "youtube music":None,
}


def _launch_exe(path: str, args: list[str] | None = None) -> bool:
    """Launch an executable. Returns True on success."""
    try:
        if path and Path(path).exists():
            subprocess.Popen([path] + (args or []))
            return True
        elif path and not Path(path).is_absolute():
            subprocess.Popen([path] + (args or []))
            return True
        return False
    except Exception as e:
        print(f"[Controller] Launch error: {e}")
        return False


# ── Actions ───────────────────────────────────────────────────────────────────

def search_web(query: str):
    """Open the default browser and search Google."""
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(url)


def open_app(app_name: str) -> bool:
    """Open a named application."""
    key = app_name.lower().strip()

    # YouTube / YouTube Music — open in browser
    if "youtube music" in key:
        webbrowser.open("https://music.youtube.com")
        return True
    if "youtube" in key:
        webbrowser.open("https://www.youtube.com")
        return True

    if key in COMMON_APPS:
        path = COMMON_APPS[key]
        if path:
            if key == "discord":
                return _launch_exe(path, ["--processStart", "Discord.exe"])
            return _launch_exe(path)

    # Fallback: try running it as a command directly
    try:
        subprocess.Popen(app_name)
        return True
    except Exception:
        return False


def get_time() -> str:
    """Return current time and date as a string."""
    now = datetime.now()
    return now.strftime("%I:%M %p on %A, %B %d, %Y")


def take_screenshot() -> str:
    """Take a screenshot, save to Desktop, return the file path."""
    desktop = Path.home() / "Desktop"
    filename = f"jerry_screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = desktop / filename
    pyautogui.screenshot(str(filepath))
    record_command("screenshot", str(filepath))
    return str(filepath)


def set_timer(minutes: float, callback=None):
    """Start a countdown timer. Calls callback(minutes) when done (runs in a thread).

    Args:
        minutes: Duration in minutes.
        callback: Optional callable to invoke when the timer fires.
                  Receives the original minutes value as an argument.
    """
    def _run():
        import time
        time.sleep(minutes * 60)
        if callback:
            callback(minutes)
        record_command(f"timer:{minutes}m", "fired")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    record_command(f"set_timer:{minutes}m", "started")
    return t


# ── Game Launching ─────────────────────────────────────────────────────────────

def _get_steam_library_paths() -> list[Path]:
    """Return all Steam library folders from libraryfolders.vdf."""
    paths = []
    default = Path(r"C:\Program Files (x86)\Steam\steamapps")
    if default.exists():
        paths.append(default)

    vdf_path = default / "libraryfolders.vdf"
    if vdf_path.exists():
        try:
            text = vdf_path.read_text(encoding="utf-8")
            for match in re.finditer(r'"path"\s+"([^"]+)"', text):
                p = Path(match.group(1)) / "steamapps"
                if p.exists():
                    paths.append(p)
        except Exception:
            pass
    return paths


def _find_steam_game(name: str) -> str | None:
    """
    Search Steam libraries for a game matching the name.
    Returns steam://rungameid/XXXX URI if found.
    """
    name_lower = name.lower()
    for lib in _get_steam_library_paths():
        for acf in lib.glob("appmanifest_*.acf"):
            try:
                text = acf.read_text(encoding="utf-8")
                match = re.search(r'"name"\s+"([^"]+)"', text)
                appid_match = re.search(r'"appid"\s+"(\d+)"', text)
                if match and appid_match:
                    game_name = match.group(1).lower()
                    if name_lower in game_name or game_name in name_lower:
                        return f"steam://rungameid/{appid_match.group(1)}"
            except Exception:
                continue
    return None


def _find_ubisoft_game(name: str) -> str | None:
    """Try to find a Ubisoft game EXE in common install paths."""
    name_lower = name.lower()
    ubisoft_dirs = [
        Path(r"C:\Program Files (x86)\Ubisoft\Ubisoft Game Launcher\games"),
        Path(r"C:\Program Files\Ubisoft\Ubisoft Game Launcher\games"),
    ]
    for base in ubisoft_dirs:
        if not base.exists():
            continue
        for game_dir in base.iterdir():
            if game_dir.is_dir() and name_lower in game_dir.name.lower():
                for exe in game_dir.rglob("*.exe"):
                    if name_lower in exe.stem.lower() or exe.stem.lower() in name_lower:
                        return str(exe)
    return None


def _find_epic_game(name: str) -> str | None:
    """Try to locate an Epic game via registry manifests."""
    name_lower = name.lower()
    manifests_dir = Path(r"C:\ProgramData\Epic\EpicGamesLauncher\Data\Manifests")
    if not manifests_dir.exists():
        return None
    for manifest in manifests_dir.glob("*.item"):
        try:
            import json
            data = json.loads(manifest.read_text(encoding="utf-8"))
            display_name = data.get("DisplayName", "").lower()
            if name_lower in display_name or display_name in name_lower:
                exe = data.get("LaunchExecutable", "")
                install_dir = data.get("InstallLocation", "")
                if exe and install_dir:
                    full = Path(install_dir) / exe
                    if full.exists():
                        return str(full)
        except Exception:
            continue
    return None


def open_game(name: str) -> bool:
    """Try to open a game by name across Steam, Ubisoft, Epic, and Program Files."""
    # 1. Steam
    steam_uri = _find_steam_game(name)
    if steam_uri:
        try:
            subprocess.Popen(["steam", steam_uri])
            return True
        except Exception:
            webbrowser.open(steam_uri)
            return True

    # 2. Ubisoft
    ubi_exe = _find_ubisoft_game(name)
    if ubi_exe:
        return _launch_exe(ubi_exe)

    # 3. Epic
    epic_exe = _find_epic_game(name)
    if epic_exe:
        return _launch_exe(epic_exe)

    # 4. Fuzzy search through Program Files
    for base in [Path(r"C:\Program Files"), Path(r"C:\Program Files (x86)")]:
        if not base.exists():
            continue
        name_lower = name.lower()
        for folder in base.iterdir():
            if folder.is_dir() and name_lower in folder.name.lower():
                for exe in folder.rglob("*.exe"):
                    if name_lower in exe.stem.lower():
                        return _launch_exe(str(exe))

    return False


# ── Volume Control ─────────────────────────────────────────────────────────────

def _get_audio_sessions():
    """Return list of (session, process_name) tuples for active audio sessions."""
    try:
        from pycaw.pycaw import AudioUtilities
        sessions = AudioUtilities.GetAllSessions()
        result = []
        for s in sessions:
            if s.Process:
                result.append((s, s.Process.name().lower()))
        return result
    except Exception as e:
        print(f"[Volume] pycaw error: {e}")
        return []


def _find_session(app_name: str):
    """Find the audio session matching an app name."""
    app_lower = app_name.lower().strip()
    for session, proc_name in _get_audio_sessions():
        if app_lower in proc_name or proc_name.startswith(app_lower):
            return session
    return None


def set_volume(app_name: str, level: int) -> bool:
    """Set a specific app's volume (0–100)."""
    try:
        from pycaw.pycaw import ISimpleAudioVolume
        session = _find_session(app_name)
        if not session:
            return False
        volume = session._ctl.QueryInterface(ISimpleAudioVolume)
        volume.SetMasterVolume(max(0.0, min(1.0, level / 100)), None)
        volume.SetMute(0, None)
        return True
    except Exception as e:
        print(f"[Volume] set_volume error: {e}")
        return False


def adjust_volume(app_name: str, delta: int) -> tuple[bool, int]:
    """Raise or lower app volume by delta (e.g. +25 or -25). Returns (success, new_level)."""
    try:
        from pycaw.pycaw import ISimpleAudioVolume
        session = _find_session(app_name)
        if not session:
            return False, 0
        volume = session._ctl.QueryInterface(ISimpleAudioVolume)
        current = volume.GetMasterVolume()
        new_level = max(0.0, min(1.0, current + delta / 100))
        volume.SetMasterVolume(new_level, None)
        return True, int(new_level * 100)
    except Exception as e:
        print(f"[Volume] adjust_volume error: {e}")
        return False, 0


def mute_app(app_name: str) -> bool:
    """Mute a specific app."""
    try:
        from pycaw.pycaw import ISimpleAudioVolume
        session = _find_session(app_name)
        if not session:
            return False
        volume = session._ctl.QueryInterface(ISimpleAudioVolume)
        volume.SetMute(1, None)
        return True
    except Exception as e:
        print(f"[Volume] mute error: {e}")
        return False


# ── Action Dispatcher ──────────────────────────────────────────────────────────

def execute_action(action_tag: str) -> str | None:
    """
    Parse and execute an [ACTION:...] tag from brain.py.
    Returns extra context string if needed (e.g. current time).
    """
    inner = action_tag.strip("[]").replace("ACTION:", "", 1)
    parts = inner.split(":")

    cmd = parts[0].lower()

    if cmd == "search" and len(parts) >= 2:
        query = ":".join(parts[1:])
        search_web(query)

    elif cmd == "open_app" and len(parts) >= 2:
        app = ":".join(parts[1:])
        open_app(app)

    elif cmd == "open_game" and len(parts) >= 2:
        game = ":".join(parts[1:])
        open_game(game)

    elif cmd == "screenshot":
        path = take_screenshot()
        return f"Screenshot saved to {path}"

    elif cmd == "time":
        return get_time()

    elif cmd == "volume_set" and len(parts) >= 3:
        app = parts[1]
        level = int(parts[2])
        set_volume(app, level)

    elif cmd == "volume_down" and len(parts) >= 2:
        app = parts[1]
        adjust_volume(app, -25)

    elif cmd == "volume_up" and len(parts) >= 2:
        app = parts[1]
        adjust_volume(app, 25)

    elif cmd == "volume_mute" and len(parts) >= 2:
        app = parts[1]
        mute_app(app)

    elif cmd == "timer" and len(parts) >= 2:
        try:
            minutes = float(parts[1])
            return f"TIMER:{minutes}"  # main.py handles the callback to speak when done
        except ValueError:
            pass

    elif cmd == "history":
        history = get_command_history()
        if not history:
            return "No commands recorded yet this session."
        lines = [f"{h['timestamp']} — {h['command']}" for h in history[-10:]]
        return "Recent commands:\n" + "\n".join(lines)

    record_command(action_tag)
    return None
