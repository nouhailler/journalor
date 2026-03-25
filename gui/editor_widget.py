"""Entry editor: transcription progress + text editing."""

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


class EditorWidget(ctk.CTkFrame):
    """
    Shows transcription progress, then lets user edit the result.
    on_save(entry_id) called after successful save.
    on_cancel() called if user cancels.
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
        self.entry_id = entry_id

        self._current_text = existing_text
        self._transcription_done = existing_text != ""
        self._tag_ids: list[int] = existing_tag_ids or []

        self._build_ui()

        if existing_text:
            self._text_box.insert("1.0", existing_text)
            self._title_entry.insert(0, existing_title)
            self._set_emoji(existing_emoji)
            self._load_tags()
        elif audio_path and audio_path.exists():
            self._start_transcription()

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

        # Transcription progress (hidden initially)
        self._progress_frame = ctk.CTkFrame(self, fg_color="#1a1a2e", corner_radius=8)
        self._progress_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        self._progress_frame.grid_columnconfigure(0, weight=1)

        self._progress_label = ctk.CTkLabel(
            self._progress_frame,
            text="Transcription en cours...",
            font=ctk.CTkFont(size=13),
        )
        self._progress_label.grid(row=0, column=0, pady=(10, 4), padx=16, sticky="w")

        self._progress_bar = ctk.CTkProgressBar(self._progress_frame, mode="indeterminate")
        self._progress_bar.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 10))
        self._progress_bar.start()

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

    def _start_transcription(self):
        self.transcriber.transcribe(
            self.audio_path,
            on_progress=self._on_progress,
            on_done=self._on_transcription_done,
            on_error=self._on_transcription_error,
        )

    def _on_progress(self, ratio: float):
        self.after(0, lambda: self._progress_bar.set(ratio))

    def _on_transcription_done(self, text: str):
        def _update():
            self._progress_frame.grid_remove()
            self._progress_bar.stop()
            self._text_box.insert("1.0", text)
            self._current_text = text
            self._transcription_done = True
            self._update_wc()
            # Auto-title from first sentence
            if not self._title_entry.get():
                first = text.strip().split(".")[0][:60].strip()
                if first:
                    self._title_entry.insert(0, first)
        self.after(0, _update)

    def _on_transcription_error(self, err: str):
        def _update():
            self._progress_frame.grid_remove()
            self._progress_bar.stop()
            self._progress_label.configure(
                text=f"Erreur transcription: {err}", text_color=COLOR_ERROR
            )
            self._progress_frame.grid()
        self.after(0, _update)

    def _on_text_change(self, event=None):
        self._text_box.edit_modified(False)
        self._update_wc()

    def _update_wc(self):
        text = self._text_box.get("1.0", "end-1c")
        wc = count_words(text)
        self._wc_label.configure(text=f"{wc} mot{'s' if wc != 1 else ''}")

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
