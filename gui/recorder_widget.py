"""Recording widget with level meter, timer, pause/stop controls."""

import threading
import time
import tkinter as tk
import customtkinter as ctk
from pathlib import Path

from core.audio_recorder import AudioRecorder
from utils.constants import (
    COLOR_ACCENT, COLOR_RECORD, COLOR_RECORD_ACTIVE,
    COLOR_SUCCESS, COLOR_WARNING, COLOR_TEXT_MUTED,
    SILENCE_DURATION_DEFAULT,
)
from utils.formatters import format_duration


class LevelMeter(ctk.CTkFrame):
    """Simple horizontal level bar."""

    BARS = 20

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self._bars = []
        for i in range(self.BARS):
            color = self._bar_color(i)
            bar = ctk.CTkFrame(self, width=10, height=28, corner_radius=3, fg_color="#2a2a2a")
            bar.grid(row=0, column=i, padx=1)
            self._bars.append((bar, color))

    def _bar_color(self, i: int) -> str:
        if i < self.BARS * 0.6:
            return COLOR_SUCCESS
        if i < self.BARS * 0.85:
            return COLOR_WARNING
        return COLOR_RECORD

    def set_level(self, rms: float) -> None:
        active = int(min(rms / 0.05, 1.0) * self.BARS)
        for i, (bar, color) in enumerate(self._bars):
            try:
                bar.configure(fg_color=color if i < active else "#2a2a2a")
            except Exception:
                return


class RecorderWidget(ctk.CTkFrame):
    """
    Full recording panel.
    on_done(audio_path, duration) called after user confirms.
    on_cancel() called if user cancels.
    """

    def __init__(self, master, audio_dir: Path, settings: dict,
                 on_done: callable, on_cancel: callable):
        super().__init__(master, fg_color="transparent")
        self.audio_dir = audio_dir
        self.settings = settings
        self.on_done = on_done
        self.on_cancel = on_cancel

        self._recorder: AudioRecorder | None = None
        self._timer_running = False
        self._audio_path: Path | None = None

        self._build_ui()
        self._start_recording()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)

        # Title
        ctk.CTkLabel(
            self, text="Nouvel enregistrement",
            font=ctk.CTkFont(size=20, weight="bold")
        ).grid(row=0, column=0, pady=(0, 20))

        # Status indicator
        self._status_label = ctk.CTkLabel(
            self, text="● Enregistrement en cours...",
            font=ctk.CTkFont(size=13),
            text_color=COLOR_RECORD_ACTIVE,
        )
        self._status_label.grid(row=1, column=0, pady=(0, 12))

        # Timer
        self._timer_label = ctk.CTkLabel(
            self, text="0:00",
            font=ctk.CTkFont(size=48, weight="bold"),
        )
        self._timer_label.grid(row=2, column=0, pady=(0, 20))

        # Level meter
        self._meter = LevelMeter(self)
        self._meter.grid(row=3, column=0, pady=(0, 24))

        # Controls
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.grid(row=4, column=0, pady=(0, 16))

        self._pause_btn = ctk.CTkButton(
            ctrl, text="⏸  Pause",
            width=130, height=40,
            fg_color="#2a2a4a", hover_color="#3a3a5a",
            command=self._toggle_pause,
        )
        self._pause_btn.grid(row=0, column=0, padx=8)

        self._stop_btn = ctk.CTkButton(
            ctrl, text="⏹  Arrêter",
            width=130, height=40,
            fg_color=COLOR_RECORD, hover_color="#c73652",
            command=self._stop,
        )
        self._stop_btn.grid(row=0, column=1, padx=8)

        self._cancel_btn = ctk.CTkButton(
            ctrl, text="Annuler",
            width=100, height=40,
            fg_color="transparent", hover_color="#2a2a2a",
            border_width=1, border_color="gray",
            command=self._cancel,
        )
        self._cancel_btn.grid(row=0, column=2, padx=8)

        # Silence hint
        silence_sec = int(float(self.settings.get("silence_duration", SILENCE_DURATION_DEFAULT)))
        ctk.CTkLabel(
            self,
            text=f"Arrêt automatique après {silence_sec}s de silence",
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
        ).grid(row=5, column=0)

    def _start_recording(self):
        silence_dur = float(self.settings.get("silence_duration", SILENCE_DURATION_DEFAULT))
        silence_thresh = float(self.settings.get("silence_threshold", 0.01))

        self._recorder = AudioRecorder(
            output_dir=self.audio_dir,
            silence_threshold=silence_thresh,
            silence_duration=silence_dur,
        )
        self._recorder.on_level = self._on_level
        self._recorder.on_auto_stop = self._on_auto_stop

        self._audio_path = self._recorder.start()
        self._timer_running = True
        self._tick()

    def _tick(self):
        if not self._timer_running:
            return
        if self._recorder and not self._recorder.is_paused:
            elapsed = self._recorder.elapsed
            self._timer_label.configure(text=format_duration(elapsed))
        self.after(200, self._tick)

    def _on_level(self, rms: float):
        try:
            if self.winfo_exists():
                self.after(0, lambda: self._meter.set_level(rms))
        except Exception:
            pass

    def _on_auto_stop(self):
        self.after(0, self._finalize)

    def _toggle_pause(self):
        if not self._recorder:
            return
        if self._recorder.is_paused:
            self._recorder.resume()
            self._pause_btn.configure(text="⏸  Pause")
            self._status_label.configure(
                text="● Enregistrement en cours...", text_color=COLOR_RECORD_ACTIVE
            )
        else:
            self._recorder.pause()
            self._pause_btn.configure(text="▶  Reprendre")
            self._status_label.configure(
                text="⏸  En pause", text_color=COLOR_TEXT_MUTED
            )

    def _stop(self):
        self._finalize()

    def _finalize(self):
        self._timer_running = False
        if self._recorder:
            self._recorder.on_level = None
            self._recorder.on_auto_stop = None
        if self._recorder and self._recorder.is_recording:
            self._audio_path = self._recorder.stop()
        duration = self._recorder.get_duration() if self._recorder else 0
        self._meter.set_level(0)
        self._status_label.configure(
            text="✓ Enregistrement terminé", text_color=COLOR_SUCCESS
        )
        self._pause_btn.configure(state="disabled")
        self._stop_btn.configure(state="disabled")

        if self._audio_path and self._audio_path.exists():
            self.on_done(self._audio_path, duration)
        else:
            self.on_cancel()

    def _cancel(self):
        self._timer_running = False
        if self._recorder:
            self._recorder.on_level = None
            self._recorder.on_auto_stop = None
        if self._recorder and self._recorder.is_recording:
            self._recorder.stop()
        if self._audio_path and self._audio_path.exists():
            self._audio_path.unlink(missing_ok=True)
        self.on_cancel()
