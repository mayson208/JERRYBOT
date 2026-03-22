"""
main.py — JERRY AI Assistant — Main application entry point.

PyQt5 dark futuristic UI with:
  - Animated pulsing orb (idle / listening / speaking states)
  - Real-time conversation transcript
  - Always-on-top overlay HUD
  - Startup greeting from Jerry
"""

import sys
import threading
from datetime import datetime

from PyQt5.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QObject, QPoint, QPropertyAnimation,
    QEasingCurve, QRectF, pyqtProperty
)
from PyQt5.QtGui import (
    QColor, QFont, QPainter, QRadialGradient, QPen, QBrush, QPalette, QLinearGradient
)
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QSizePolicy, QFrame, QPushButton
)

import config
from brain import Brain
from voice import speak, is_speaking
from listener import Listener
from controller import execute_action

# ── State constants ────────────────────────────────────────────────────────────

STATE_IDLE      = "idle"
STATE_LISTENING = "listening"
STATE_THINKING  = "thinking"
STATE_SPEAKING  = "speaking"

STATE_LABELS = {
    STATE_IDLE:      "Idle — say 'Hey Jerry' to wake me",
    STATE_LISTENING: "Listening...",
    STATE_THINKING:  "Thinking...",
    STATE_SPEAKING:  "Speaking...",
}

STATE_COLORS = {
    STATE_IDLE:      "#1a4a6b",
    STATE_LISTENING: "#00d4ff",
    STATE_THINKING:  "#ff9900",
    STATE_SPEAKING:  "#00ff88",
}


# ── Signal bridge (thread-safe UI updates) ─────────────────────────────────────

class Signals(QObject):
    set_state       = pyqtSignal(str)
    append_user     = pyqtSignal(str)
    append_jerry    = pyqtSignal(str)
    show_error      = pyqtSignal(str)


# ── Animated Orb Widget ────────────────────────────────────────────────────────

class OrbWidget(QWidget):
    """Animated glowing orb that pulses based on Jerry's current state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 220)
        self._state = STATE_IDLE
        self._pulse = 0.0
        self._pulse_dir = 1
        self._rings = []   # [(radius, alpha)] for speaking rings

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(30)

    def set_state(self, state: str):
        self._state = state
        if state == STATE_SPEAKING:
            self._rings = [(60, 1.0), (80, 0.6), (100, 0.3)]
        else:
            self._rings = []

    def _animate(self):
        speeds = {
            STATE_IDLE:      0.012,
            STATE_LISTENING: 0.04,
            STATE_THINKING:  0.025,
            STATE_SPEAKING:  0.05,
        }
        speed = speeds.get(self._state, 0.015)
        self._pulse += speed * self._pulse_dir
        if self._pulse >= 1.0:
            self._pulse = 1.0
            self._pulse_dir = -1
        elif self._pulse <= 0.0:
            self._pulse = 0.0
            self._pulse_dir = 1

        # Animate rings outward
        if self._state == STATE_SPEAKING:
            new_rings = []
            for r, a in self._rings:
                r += 1.5
                a -= 0.015
                if a > 0 and r < 160:
                    new_rings.append((r, a))
            if len(new_rings) < 3:
                new_rings.append((55, 1.0))
            self._rings = new_rings

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        color_hex = STATE_COLORS.get(self._state, "#00d4ff")
        base_color = QColor(color_hex)

        # Outer glow rings (speaking state)
        for r, a in self._rings:
            ring_color = QColor(base_color)
            ring_color.setAlphaF(a * 0.4)
            pen = QPen(ring_color, 2)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # Glow halo
        glow_radius = 70 + self._pulse * 20
        gradient = QRadialGradient(cx, cy, glow_radius)
        glow_color = QColor(base_color)
        glow_color.setAlphaF(0.15 + self._pulse * 0.1)
        gradient.setColorAt(0, glow_color)
        gradient.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(cx - glow_radius, cy - glow_radius,
                                   glow_radius * 2, glow_radius * 2))

        # Core orb
        core_r = 45 + self._pulse * 8
        core_gradient = QRadialGradient(cx - core_r * 0.3, cy - core_r * 0.3, core_r * 1.2)
        bright = QColor(base_color)
        bright.setAlphaF(0.9)
        dark = QColor(base_color)
        dark.setAlphaF(0.4)
        core_gradient.setColorAt(0, bright)
        core_gradient.setColorAt(1, dark)
        painter.setBrush(QBrush(core_gradient))

        # Outer ring
        pen = QPen(base_color, 2)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.drawEllipse(QRectF(cx - core_r, cy - core_r, core_r * 2, core_r * 2))

        # Inner highlight
        highlight = QColor(255, 255, 255, int(60 + self._pulse * 40))
        painter.setBrush(QBrush(highlight))
        painter.setPen(Qt.NoPen)
        hl_r = core_r * 0.3
        painter.drawEllipse(QRectF(cx - core_r * 0.5 - hl_r / 2,
                                   cy - core_r * 0.6 - hl_r / 2,
                                   hl_r, hl_r))

        # JERRY label in center
        painter.setPen(QColor(255, 255, 255, 200))
        font = QFont(config.FONT_FAMILY, 9, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRectF(cx - 40, cy - 8, 80, 16), Qt.AlignCenter, "J E R R Y")


# ── Main Window ────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, signals: Signals, brain: Brain):
        super().__init__()
        self.signals = signals
        self.brain = brain
        self._current_state = STATE_IDLE

        self.setWindowTitle("JERRY — AI Assistant")
        self.setMinimumSize(700, 600)
        self.resize(750, 680)
        self._apply_theme()
        self._build_ui()
        self._connect_signals()

    def _apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {config.BG_COLOR};
                color: {config.TEXT_COLOR};
                font-family: '{config.FONT_FAMILY}';
            }}
            QTextEdit {{
                background-color: #0d0d20;
                color: {config.TEXT_COLOR};
                border: 1px solid #1a3a55;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                font-family: '{config.FONT_FAMILY}';
            }}
            QScrollBar:vertical {{
                background: #0d0d20;
                width: 8px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: #1a3a55;
                border-radius: 4px;
            }}
            QPushButton {{
                background-color: #0d1a2e;
                color: {config.ACCENT_COLOR};
                border: 1px solid {config.ACCENT_COLOR};
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #1a2e45;
            }}
        """)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # ── Top bar ──
        top_bar = QHBoxLayout()
        title = QLabel("J E R R Y")
        title.setStyleSheet(f"color: {config.ACCENT_COLOR}; font-size: 22px; font-weight: bold; letter-spacing: 6px;")
        subtitle = QLabel("AI ASSISTANT")
        subtitle.setStyleSheet("color: #445566; font-size: 10px; letter-spacing: 4px;")
        top_bar.addWidget(title)
        top_bar.addWidget(subtitle)
        top_bar.addStretch()

        # Clear memory button
        clear_btn = QPushButton("Clear Memory")
        clear_btn.setFixedWidth(110)
        clear_btn.clicked.connect(self._clear_memory)
        top_bar.addWidget(clear_btn)

        root.addLayout(top_bar)

        # ── Divider ──
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"color: #1a3a55;")
        root.addWidget(divider)

        # ── Orb + Status ──
        orb_row = QHBoxLayout()
        orb_row.addStretch()

        orb_col = QVBoxLayout()
        orb_col.setAlignment(Qt.AlignCenter)

        self.orb = OrbWidget()
        self.orb.setFixedSize(220, 220)
        orb_col.addWidget(self.orb, alignment=Qt.AlignCenter)

        self.status_label = QLabel(STATE_LABELS[STATE_IDLE])
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"color: {config.ACCENT_COLOR}; font-size: 12px; letter-spacing: 1px;")
        orb_col.addWidget(self.status_label)

        orb_row.addLayout(orb_col)
        orb_row.addStretch()
        root.addLayout(orb_row)

        # ── Transcript ──
        transcript_label = QLabel("CONVERSATION")
        transcript_label.setStyleSheet("color: #445566; font-size: 10px; letter-spacing: 3px;")
        root.addWidget(transcript_label)

        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setMinimumHeight(200)
        root.addWidget(self.transcript)

    def _connect_signals(self):
        self.signals.set_state.connect(self._on_state_change)
        self.signals.append_user.connect(self._on_user_message)
        self.signals.append_jerry.connect(self._on_jerry_message)
        self.signals.show_error.connect(self._on_error)

    def _on_state_change(self, state: str):
        self._current_state = state
        self.orb.set_state(state)
        self.status_label.setText(STATE_LABELS.get(state, state))
        color = STATE_COLORS.get(state, config.ACCENT_COLOR)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 12px; letter-spacing: 1px;")

    def _on_user_message(self, text: str):
        time_str = datetime.now().strftime("%H:%M")
        self.transcript.append(
            f'<span style="color:#aaaaaa; font-size:10px;">[{time_str}]</span> '
            f'<span style="color:#ffffff; font-weight:bold;">You:</span> '
            f'<span style="color:#dddddd;">{text}</span>'
        )

    def _on_jerry_message(self, text: str):
        time_str = datetime.now().strftime("%H:%M")
        self.transcript.append(
            f'<span style="color:#aaaaaa; font-size:10px;">[{time_str}]</span> '
            f'<span style="color:{config.ACCENT_COLOR}; font-weight:bold;">Jerry:</span> '
            f'<span style="color:#c8f0ff;">{text}</span>'
        )
        self.transcript.append("")

    def _on_error(self, msg: str):
        self.transcript.append(
            f'<span style="color:#ff4444;">[Error] {msg}</span>'
        )

    def _clear_memory(self):
        self.brain.clear_memory()
        self.transcript.clear()
        self.transcript.append(
            f'<span style="color:#ff9900;">Memory cleared. Jerry starts fresh.</span>'
        )


# ── Always-on-top HUD Overlay ──────────────────────────────────────────────────

class HudOverlay(QWidget):
    """Small frameless overlay that stays on top of all windows."""

    def __init__(self, signals: Signals):
        super().__init__()
        self.signals = signals
        self._state = STATE_IDLE
        self._drag_pos = None
        self._pulse = 0.0
        self._pulse_dir = 1

        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(180, 52)

        # Position bottom-right corner
        screen = QApplication.primaryScreen().geometry()
        self.move(screen.width() - 200, screen.height() - 100)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(40)

        self.signals.set_state.connect(self._on_state)

    def _on_state(self, state: str):
        self._state = state

    def _tick(self):
        speed = 0.04 if self._state != STATE_IDLE else 0.015
        self._pulse += speed * self._pulse_dir
        if self._pulse >= 1.0:
            self._pulse_dir = -1
        elif self._pulse <= 0.0:
            self._pulse_dir = 1
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background pill
        bg = QColor(10, 10, 26, 210)
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(QColor(config.ACCENT_COLOR), 1))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 12, 12)

        # Dot
        color = QColor(STATE_COLORS.get(self._state, config.ACCENT_COLOR))
        alpha = int(160 + self._pulse * 95)
        color.setAlpha(alpha)
        painter.setBrush(QBrush(color))
        painter.setPen(Qt.NoPen)
        dot_r = 7
        painter.drawEllipse(14 - dot_r, self.height() // 2 - dot_r, dot_r * 2, dot_r * 2)

        # Label
        painter.setPen(QColor(200, 220, 240))
        font = QFont(config.FONT_FAMILY, 10, QFont.Bold)
        painter.setFont(font)
        label = STATE_LABELS.get(self._state, self._state).split("—")[0].strip()
        if len(label) > 18:
            label = label[:18]
        painter.drawText(28, 0, self.width() - 36, self.height(), Qt.AlignVCenter, label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


# ── Jerry Pipeline ─────────────────────────────────────────────────────────────

class JerryPipeline:
    """Ties listener → brain → voice → UI together."""

    def __init__(self, brain: Brain, signals: Signals):
        self.brain   = brain
        self.signals = signals
        self.listener = Listener(
            on_wake_word   = self._on_wake_word,
            on_transcribed = self._on_transcribed,
            on_error       = self._on_error,
        )

    def start(self):
        self.listener.start()

    def stop(self):
        self.listener.stop()

    def _on_wake_word(self):
        self.signals.set_state.emit(STATE_LISTENING)

    def _on_transcribed(self, text: str):
        self.signals.set_state.emit(STATE_THINKING)
        self.signals.append_user.emit(text)

        def process():
            try:
                reply, action = self.brain.ask(text)

                # Execute PC action if present
                extra_context = None
                if action:
                    extra_context = execute_action(action)

                # If the action returned context (e.g. current time), append it to reply
                if extra_context and extra_context not in reply:
                    reply = f"{reply} — {extra_context}"

                self.signals.append_jerry.emit(reply)
                self.signals.set_state.emit(STATE_SPEAKING)

                speak(
                    reply,
                    on_done=lambda: self.signals.set_state.emit(STATE_IDLE)
                )
            except Exception as e:
                self.signals.show_error.emit(str(e))
                self.signals.set_state.emit(STATE_IDLE)

        threading.Thread(target=process, daemon=True).start()

    def _on_error(self, msg: str):
        self.signals.show_error.emit(msg)
        self.signals.set_state.emit(STATE_IDLE)


# ── Entry Point ────────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("JERRY")
    app.setStyle("Fusion")

    # Dark palette fallback
    palette = QPalette()
    palette.setColor(QPalette.Window,       QColor(config.BG_COLOR))
    palette.setColor(QPalette.WindowText,   QColor(config.TEXT_COLOR))
    palette.setColor(QPalette.Base,         QColor("#0d0d20"))
    palette.setColor(QPalette.Text,         QColor(config.TEXT_COLOR))
    palette.setColor(QPalette.Button,       QColor("#0d1a2e"))
    palette.setColor(QPalette.ButtonText,   QColor(config.ACCENT_COLOR))
    app.setPalette(palette)

    # Check for missing API keys
    missing = config.validate_keys()
    if missing:
        print(f"[JERRY] WARNING: Missing API keys in .env: {', '.join(missing)}")

    signals = Signals()
    brain   = Brain()

    # Main window
    window = MainWindow(signals, brain)
    window.show()

    # HUD overlay
    hud = HudOverlay(signals)
    hud.show()

    # Jerry pipeline
    pipeline = JerryPipeline(brain, signals)
    pipeline.start()

    # Startup greeting (async so window shows first)
    def _greet():
        import time
        time.sleep(1.5)
        try:
            greeting = brain.build_greeting()
            signals.append_jerry.emit(greeting)
            signals.set_state.emit(STATE_SPEAKING)
            speak(
                greeting,
                on_done=lambda: signals.set_state.emit(STATE_IDLE)
            )
        except Exception as e:
            print(f"[Greeting] Error: {e}")
            signals.set_state.emit(STATE_IDLE)

    threading.Thread(target=_greet, daemon=True).start()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
