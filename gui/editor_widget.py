"""Entry editor: transcription progress + text editing."""

import time
import threading
import tkinter as tk
import customtkinter as ctk
from pathlib import Path

from core.transcription import Transcriber
from core.database import Database
from core.encryption import EncryptionManager
from utils.constants import COLOR_ACCENT, COLOR_SUCCESS, COLOR_ERROR, COLOR_TEXT_MUTED
from utils.formatters import (
    count_words, format_duration, today_str, now_time_str, now_datetime_str
)

EMOJIS = ["", "😊", "😢", "😤", "🙏", "🔥", "💡", "❤️", "😴", "🎉"]

# Default transcription-seconds per audio-second, per model
_DEFAULT_RATIOS: dict[str, float] = {
    "tiny":                              0.10,
    "base":                              0.25,
    "small":                             0.70,
    "medium":                            2.50,
    "large-v2":                          4.00,
    "large-v3":                          4.50,
    "distil-large-v3":                   1.50,
    "distil-whisper/distil-large-v3":    1.50,
}


class EditorWidget(ctk.CTkFrame):
    """
    Shows transcription progress, then lets user edit the result.
    on_save(entry_id) called after successful save.
    on_cancel() called if user cancels.
    on_background(root, audio_path, duration, title, emoji, tag_ids,
                  remaining_secs, result_holder) called when user wants to
    continue in background.
    """

    def __init__(
        self, master,
        audio_path: Path,
        duration: float,
        db: Database,
        enc: EncryptionManager,
        transcriber: Transcriber,
        settings: dict,
        on_save: callable,
        on_cancel: callable,
        on_background: callable = None,
        entry_id: int | None = None,  # for editing existing
        existing_text: str = "",
        existing_title: str = "",
        existing_emoji: str = "",
        existing_tag_ids: list[int] | None = None,
    ):
        super().__init__(master, fg_color="transparent")
        self.audio_path = audio_path
        self.duration = duration
        self.db = db
        self.enc = enc
        self.transcriber = transcriber
        self.settings = settings
        self.on_save = on_save
        self.on_cancel = on_cancel
        self.on_background = on_background
        self.entry_id = entry_id

        self._current_text = existing_text
        self._transcription_done = existing_text != ""
        self._tag_ids: list[int] = existing_tag_ids or []

        # Background-mode state
        self._bg_mode = False
        self._bg_result_holder: dict = {}   # set: {"text": ..., "done": True} or {"error": ...}
        self._countdown_id: str | None = None
        self._countdown_secs: int = 0
        self._transcription_start: float | None = None

        self._build_ui()

        if existing_text:
            self._text_box.insert("1.0", existing_text)
            self._title_entry.insert(0, existing_title)
            self._set_emoji(existing_emoji)
            self._load_tags()
        elif audio_path and audio_path.exists():
            self._start_transcription()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Header row
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header, text="✏️  Édition de l'entrée",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        # Duration badge
        if self.duration:
            ctk.CTkLabel(
                header,
                text=f"⏱ {format_duration(self.duration)}",
                font=ctk.CTkFont(size=12),
                text_color=COLOR_TEXT_MUTED,
            ).grid(row=0, column=1, sticky="e")

        # Transcription progress frame
        self._progress_frame = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=8)
        self._progress_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self._progress_frame.grid_columnconfigure(0, weight=1)

        self._progress_label = ctk.CTkLabel(
            self._progress_frame,
            text="Transcription en cours...",
            font=ctk.CTkFont(size=13),
            anchor="w",
        )
        self._progress_label.grid(row=0, column=0, pady=(10, 4), padx=16, sticky="ew")

        self._progress_bar = ctk.CTkProgressBar(self._progress_frame, mode="indeterminate")
        self._progress_bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
        self._progress_bar.start()

        # "Continue in background" button — only shown when on_background is set
        if self.on_background:
            bg_row = ctk.CTkFrame(self._progress_frame, fg_color="transparent")
            bg_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(2, 10))
            bg_row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                bg_row,
                text="Vous pouvez continuer à utiliser l'application pendant la transcription.",
                font=ctk.CTkFont(size=10),
                text_color=COLOR_TEXT_MUTED,
                anchor="w",
            ).grid(row=0, column=0, sticky="w")

            self._bg_btn = ctk.CTkButton(
                bg_row,
                text="⏩  Continuer en arrière-plan",
                fg_color="transparent",
                border_width=1,
                border_color="#4444aa",
                hover_color="#1a1a4e",
                height=30,
                font=ctk.CTkFont(size=11),
                command=self._go_background,
            )
            self._bg_btn.grid(row=1, column=0, sticky="w", pady=(6, 0))

        if self._transcription_done:
            self._progress_frame.grid_remove()

        # Title + emoji row
        meta = ctk.CTkFrame(self, fg_color="transparent")
        meta.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        meta.grid_columnconfigure(0, weight=1)

        self._title_entry = ctk.CTkEntry(
            meta, placeholder_text="Titre (optionnel)",
            height=38, font=ctk.CTkFont(size=13),
        )
        self._title_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._emoji_var = tk.StringVar(value="")
        self._emoji_menu = ctk.CTkOptionMenu(
            meta, values=EMOJIS,
            variable=self._emoji_var,
            width=80, height=38,
            font=ctk.CTkFont(size=16),
        )
        self._emoji_menu.grid(row=0, column=1)

        # Text editor
        self._text_box = ctk.CTkTextbox(
            self, font=ctk.CTkFont(size=13), wrap="word",
            undo=True,
        )
        self._text_box.grid(row=3, column=0, sticky="nsew", pady=(0, 8))
        self._text_box.bind("<<Modified>>", self._on_text_change)

        # Word count
        self._wc_label = ctk.CTkLabel(
            self, text="0 mot",
            font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED,
        )
        self._wc_label.grid(row=4, column=0, sticky="e")

        # Tags
        tags_frame = ctk.CTkFrame(self, fg_color="transparent")
        tags_frame.grid(row=5, column=0, sticky="ew", pady=(4, 8))
        self._tags_frame = tags_frame
        self._load_tags()

        # Action buttons
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=6, column=0, sticky="ew")

        ctk.CTkButton(
            actions, text="Annuler",
            fg_color="transparent", hover_color="#2a2a2a",
            border_width=1, border_color="gray",
            width=100, height=40,
            command=self.on_cancel,
        ).pack(side="right", padx=(8, 0))

        self._save_btn = ctk.CTkButton(
            actions, text="💾  Sauvegarder",
            fg_color=COLOR_ACCENT, hover_color="#c73652",
            width=160, height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._save,
        )
        self._save_btn.pack(side="right")

        self._status_label = ctk.CTkLabel(
            actions, text="",
            font=ctk.CTkFont(size=12), text_color=COLOR_SUCCESS,
        )
        self._status_label.pack(side="left")

    # ── Tags ──────────────────────────────────────────────────────────────────

    def _load_tags(self):
        for w in self._tags_frame.winfo_children():
            w.destroy()
        ctk.CTkLabel(
            self._tags_frame, text="Tags:",
            font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED
        ).pack(side="left", padx=(0, 8))

        for tag in self.db.list_tags():
            tid = tag["id"]
            selected = tid in self._tag_ids
            btn = ctk.CTkButton(
                self._tags_frame,
                text=tag["name"],
                width=80, height=26,
                font=ctk.CTkFont(size=11),
                fg_color=tag["color"] if selected else "#2a2a2a",
                hover_color=tag["color"],
                corner_radius=12,
                command=lambda t=tid, tc=tag["color"]: self._toggle_tag(t, tc),
            )
            btn.pack(side="left", padx=3)

    def _toggle_tag(self, tag_id: int, color: str):
        if tag_id in self._tag_ids:
            self._tag_ids.remove(tag_id)
        else:
            self._tag_ids.append(tag_id)
        self._load_tags()

    def _set_emoji(self, emoji: str):
        if emoji in EMOJIS:
            self._emoji_var.set(emoji)

    # ── Transcription ─────────────────────────────────────────────────────────

    def _estimate_secs(self) -> int:
        """Return estimated transcription duration in seconds."""
        model = self.transcriber.model_name
        key = f"whisper_ratio_{model.replace('/', '_')}"
        stored = self.db.get_setting(key)
        ratio = float(stored) if stored else _DEFAULT_RATIOS.get(model, 1.5)
        return max(3, int(self.duration * ratio))

    def _start_transcription(self):
        from gui.download_dialog import DownloadDialog
        from core.model_downloader import is_model_cached

        model_name = self.transcriber.model_name

        if is_model_cached(model_name):
            self._begin_countdown_and_run()
        else:
            self._progress_frame.grid_remove()
            self._progress_bar.stop()
            DownloadDialog(
                self.winfo_toplevel(),
                model_name=model_name,
                on_ready=self._on_model_ready,
                on_cancel=self.on_cancel,
            )

    def _on_model_ready(self):
        """Called by DownloadDialog when the model is available."""
        self._progress_label.configure(text="Transcription en cours…")
        self._progress_bar.configure(mode="indeterminate")
        self._progress_bar.start()
        self._progress_frame.grid()
        self._begin_countdown_and_run()

    def _begin_countdown_and_run(self):
        self._countdown_secs = self._estimate_secs()
        self._transcription_start = time.monotonic()
        self._tick_countdown()
        self._run_transcription()

    def _tick_countdown(self):
        if self._bg_mode or not self.winfo_exists():
            return
        secs = self._countdown_secs
        if secs > 0:
            mins, s = divmod(secs, 60)
            if mins > 0:
                txt = f"Transcription en cours… ~{mins}m{s:02d}s restantes"
            else:
                txt = f"Transcription en cours… ~{secs}s restantes"
            self._progress_label.configure(text=txt)
            self._countdown_secs -= 1
            self._countdown_id = self.after(1000, self._tick_countdown)
        else:
            self._progress_label.configure(text="Transcription en cours… finalisation…")
            self._countdown_id = None

    def _cancel_countdown(self):
        if self._countdown_id:
            try:
                self.after_cancel(self._countdown_id)
            except Exception:
                pass
            self._countdown_id = None

    def _run_transcription(self):
        self.transcriber.transcribe(
            self.audio_path,
            on_progress=self._on_progress,
            on_done=self._on_transcription_done,
            on_error=self._on_transcription_error,
        )

    def _on_progress(self, ratio: float):
        if self._bg_mode:
            return
        def _do(r=ratio):
            try:
                if self.winfo_exists():
                    self._progress_bar.set(r)
            except Exception:
                pass
        try:
            self.after(0, _do)
        except Exception:
            pass

    def _on_transcription_done(self, text: str):
        # Update stored ratio for future estimates
        if self._transcription_start and self.duration > 0:
            elapsed = time.monotonic() - self._transcription_start
            new_ratio = elapsed / self.duration
            model = self.transcriber.model_name
            key = f"whisper_ratio_{model.replace('/', '_')}"
            stored = self.db.get_setting(key)
            if stored:
                ratio = 0.7 * float(stored) + 0.3 * new_ratio
            else:
                ratio = new_ratio
            try:
                self.db.set_setting(key, f"{ratio:.4f}")
            except Exception:
                pass

        if self._bg_mode:
            self._bg_result_holder["text"] = text
            self._bg_result_holder["done"] = True
            return

        def _update():
            if not self.winfo_exists():
                return
            self._cancel_countdown()
            self._progress_frame.grid_remove()
            self._progress_bar.stop()
            self._text_box.insert("1.0", text)
            self._current_text = text
            self._transcription_done = True
            self._update_wc()
            if not self._title_entry.get():
                first = text.strip().split(".")[0][:60].strip()
                if first:
                    self._title_entry.insert(0, first)
        try:
            self.after(0, _update)
        except Exception:
            pass

    def _on_transcription_error(self, err: str):
        if self._bg_mode:
            self._bg_result_holder["error"] = err
            self._bg_result_holder["done"] = True
            return

        def _update():
            if not self.winfo_exists():
                return
            self._cancel_countdown()
            self._progress_bar.stop()
            self._progress_label.configure(
                text=f"Erreur transcription: {err}", text_color=COLOR_ERROR
            )
            self._progress_frame.grid()
        try:
            self.after(0, _update)
        except Exception:
            pass

    # ── Background mode ───────────────────────────────────────────────────────

    def _go_background(self):
        """Switch transcription to background; navigate back to entry list."""
        self._cancel_countdown()
        self._bg_mode = True

        root = self.winfo_toplevel()
        title = self._title_entry.get().strip()
        emoji = self._emoji_var.get()
        tag_ids = list(self._tag_ids)
        remaining = max(0, self._countdown_secs)

        if self.on_background:
            self.on_background(
                root=root,
                audio_path=self.audio_path,
                duration=self.duration,
                title=title,
                emoji=emoji,
                tag_ids=tag_ids,
                remaining=remaining,
                result_holder=self._bg_result_holder,
            )

        self.on_cancel()

    # ── Text editing ──────────────────────────────────────────────────────────

    def _on_text_change(self, event=None):
        self._text_box.edit_modified(False)
        self._update_wc()

    def _update_wc(self):
        text = self._text_box.get("1.0", "end-1c")
        wc = count_words(text)
        self._wc_label.configure(text=f"{wc} mot{'s' if wc != 1 else ''}")

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save(self):
        text = self._text_box.get("1.0", "end-1c").strip()
        title = self._title_entry.get().strip()
        emoji = self._emoji_var.get()
        wc = count_words(text)
        encrypted = self.enc.encrypt(text) if text else b""

        if self.entry_id is not None:
            self.db.update_entry(
                self.entry_id, encrypted, title=title, word_count=wc, emoji=emoji
            )
            eid = self.entry_id
        else:
            eid = self.db.add_entry(
                date=today_str(),
                time=now_time_str(),
                content_encrypted=encrypted,
                title=title,
                audio_path=str(self.audio_path) if self.audio_path else "",
                duration=self.duration,
                word_count=wc,
                emoji=emoji,
            )

        self.db.set_entry_tags(eid, self._tag_ids)
        self._status_label.configure(text="✓ Sauvegardé")
        self.after(800, lambda: self.on_save(eid))
