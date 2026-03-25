"""Main application window."""

import threading
import tkinter as tk
import customtkinter as ctk
from pathlib import Path

from core.database import Database
from core.encryption import EncryptionManager
from core.transcription import Transcriber
from core.export import Exporter
from gui.entry_list import EntryList
from gui.recorder_widget import RecorderWidget
from gui.editor_widget import EditorWidget
from gui.stats_view import StatsView
from utils.constants import (
    COLOR_ACCENT, COLOR_BG, COLOR_SURFACE, COLOR_TEXT_MUTED,
    WINDOW_MIN_W, WINDOW_MIN_H, WINDOW_DEFAULT_W, WINDOW_DEFAULT_H,
    APP_NAME,
)
from utils.formatters import format_date_display, today_str


# ── Panel names ────────────────────────────────────────────────────────────────
PANEL_LIST    = "list"
PANEL_RECORD  = "record"
PANEL_EDITOR  = "editor"
PANEL_STATS   = "stats"
PANEL_DETAIL  = "detail"


class MainWindow(ctk.CTk):
    def __init__(self, db: Database, enc: EncryptionManager, data_dir: Path,
                 log_path: Path = None):
        super().__init__()
        self.db = db
        self.enc = enc
        self.data_dir = data_dir
        self.log_path = log_path
        self.audio_dir = data_dir / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)

        self._settings = self._load_settings()
        self._transcriber = Transcriber(
            model_name=self._settings.get("whisper_model", "base"),
            language=self._settings.get("language", "fr"),
        )
        self._exporter = Exporter(db, enc)

        self.title(APP_NAME)
        self.geometry(f"{WINDOW_DEFAULT_W}x{WINDOW_DEFAULT_H}")
        self.minsize(WINDOW_MIN_W, WINDOW_MIN_H)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self._build_layout()
        self._bind_shortcuts()
        self._show_list()

    def _load_settings(self) -> dict:
        keys = ["whisper_model", "language", "silence_duration",
                 "silence_threshold", "save_dir"]
        return {k: self.db.get_setting(k) for k in keys if self.db.get_setting(k)}

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left sidebar
        self._sidebar = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color="#0f0f1a")
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_rowconfigure(10, weight=1)
        self._sidebar.grid_propagate(False)

        self._build_sidebar()

        # Right content area
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self._content.grid_columnconfigure(0, weight=1)
        self._content.grid_rowconfigure(0, weight=1)

        self._current_panel: ctk.CTkFrame | None = None

    def _build_sidebar(self):
        s = self._sidebar

        # Logo
        ctk.CTkLabel(
            s, text="🎙️", font=ctk.CTkFont(size=32)
        ).grid(row=0, column=0, pady=(24, 0))
        ctk.CTkLabel(
            s, text=APP_NAME,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=1, column=0, pady=(0, 24))

        # Record button (prominent)
        self._rec_btn = ctk.CTkButton(
            s, text="+ Enregistrer",
            fg_color=COLOR_ACCENT, hover_color="#c73652",
            height=44, font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start_recording,
        )
        self._rec_btn.grid(row=2, column=0, padx=16, sticky="ew", pady=(0, 16))

        # Nav buttons
        self._nav_btns = {}
        nav_items = [
            ("📋  Journal", PANEL_LIST),
            ("📊  Statistiques", PANEL_STATS),
        ]
        for i, (label, panel) in enumerate(nav_items):
            btn = ctk.CTkButton(
                s, text=label, anchor="w",
                fg_color="transparent", hover_color="#1a1a3e",
                height=36, font=ctk.CTkFont(size=12),
                command=lambda p=panel: self._nav_to(p),
            )
            btn.grid(row=3 + i, column=0, padx=8, sticky="ew", pady=2)
            self._nav_btns[panel] = btn

        # Separator spacer
        ctk.CTkFrame(s, height=1, fg_color="#2a2a3a").grid(
            row=8, column=0, sticky="ew", padx=16, pady=8
        )

        # Settings + export at bottom
        for i, (label, cmd) in enumerate([
            ("⚙️  Paramètres", self._open_settings),
            ("📤  Exporter", self._open_export),
        ]):
            ctk.CTkButton(
                s, text=label, anchor="w",
                fg_color="transparent", hover_color="#1a1a3e",
                height=34, font=ctk.CTkFont(size=11),
                command=cmd,
            ).grid(row=9 + i, column=0, padx=8, sticky="ew", pady=2)

        # Date display at very bottom
        ctk.CTkLabel(
            s, text=format_date_display(today_str()),
            font=ctk.CTkFont(size=10),
            text_color=COLOR_TEXT_MUTED,
            wraplength=170, justify="center",
        ).grid(row=12, column=0, pady=(8, 16))

    def _set_nav_active(self, panel: str):
        for p, btn in self._nav_btns.items():
            btn.configure(
                fg_color=COLOR_SURFACE if p == panel else "transparent"
            )

    # ── Panel management ───────────────────────────────────────────────────────

    def _clear_content(self):
        if self._current_panel:
            self._current_panel.destroy()
            self._current_panel = None

    def _show_list(self):
        self._clear_content()
        self._set_nav_active(PANEL_LIST)
        panel = ctk.CTkFrame(self._content, fg_color="transparent")
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, weight=1)

        self._entry_list = EntryList(
            panel, self.db, self.enc,
            on_select=self._open_entry_detail,
        )
        self._entry_list.grid(row=0, column=0, sticky="nsew")
        self._current_panel = panel

    def _nav_to(self, panel: str):
        if panel == PANEL_LIST:
            self._show_list()
        elif panel == PANEL_STATS:
            self._show_stats()

    # ── Recording ─────────────────────────────────────────────────────────────

    def _start_recording(self):
        self._clear_content()
        panel = ctk.CTkFrame(self._content, fg_color="transparent")
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, weight=1)

        RecorderWidget(
            panel,
            audio_dir=self.audio_dir,
            settings=self._settings,
            on_done=self._on_recording_done,
            on_cancel=self._show_list,
        ).grid(row=0, column=0, sticky="nsew")

        self._current_panel = panel

    def _on_recording_done(self, audio_path: Path, duration: float):
        self._show_editor(
            audio_path=audio_path,
            duration=duration,
            entry_id=None,
            existing_text="",
        )

    # ── Editor ─────────────────────────────────────────────────────────────────

    def _show_editor(
        self,
        audio_path: Path,
        duration: float,
        entry_id: int | None,
        existing_text: str = "",
        existing_title: str = "",
        existing_emoji: str = "",
        existing_tag_ids: list[int] | None = None,
    ):
        self._clear_content()
        panel = ctk.CTkFrame(self._content, fg_color="transparent")
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(0, weight=1)

        EditorWidget(
            panel,
            audio_path=audio_path,
            duration=duration,
            db=self.db,
            enc=self.enc,
            transcriber=self._transcriber,
            settings=self._settings,
            on_save=self._on_entry_saved,
            on_cancel=self._show_list,
            entry_id=entry_id,
            existing_text=existing_text,
            existing_title=existing_title,
            existing_emoji=existing_emoji,
            existing_tag_ids=existing_tag_ids,
        ).grid(row=0, column=0, sticky="nsew")

        self._current_panel = panel

    def _on_entry_saved(self, entry_id: int):
        self._show_list()
        self.after(100, lambda: self._entry_list.refresh(select_id=entry_id))

    # ── Detail view ────────────────────────────────────────────────────────────

    def _open_entry_detail(self, entry_id: int):
        row = self.db.get_entry(entry_id)
        if not row:
            return
        self._clear_content()
        panel = ctk.CTkFrame(self._content, fg_color="transparent")
        panel.grid(row=0, column=0, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)

        # Toolbar
        toolbar = ctk.CTkFrame(panel, fg_color="transparent")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        ctk.CTkButton(
            toolbar, text="← Retour",
            fg_color="transparent", hover_color="#2a2a2a",
            border_width=1, border_color="gray",
            width=90, height=32,
            command=self._show_list,
        ).pack(side="left")

        ctk.CTkButton(
            toolbar, text="✏️  Modifier",
            fg_color=COLOR_ACCENT, hover_color="#c73652",
            width=100, height=32,
            command=lambda: self._edit_entry(entry_id),
        ).pack(side="right", padx=(8, 0))

        ctk.CTkButton(
            toolbar, text="🗑  Supprimer",
            fg_color="#3a1a1a", hover_color="#5a2a2a",
            width=100, height=32,
            command=lambda: self._delete_entry(entry_id),
        ).pack(side="right")

        # Content
        content_frame = ctk.CTkScrollableFrame(panel, fg_color="transparent")
        content_frame.grid(row=1, column=0, sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=1)

        emoji = row["emoji"] or "📝"
        title = row["title"] or "Sans titre"
        date_str = f"{format_date_display(row['date'])}  {row['time'][:5]}"

        ctk.CTkLabel(
            content_frame, text=f"{emoji}  {title}",
            font=ctk.CTkFont(size=22, weight="bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        ctk.CTkLabel(
            content_frame, text=date_str,
            font=ctk.CTkFont(size=12), text_color=COLOR_TEXT_MUTED, anchor="w",
        ).grid(row=1, column=0, sticky="w", pady=(0, 8))

        # Tags
        tags = self.db.get_entry_tags(entry_id)
        if tags:
            tag_row = ctk.CTkFrame(content_frame, fg_color="transparent")
            tag_row.grid(row=2, column=0, sticky="w", pady=(0, 16))
            for t in tags:
                ctk.CTkLabel(
                    tag_row, text=t["name"],
                    font=ctk.CTkFont(size=11), text_color="white",
                    fg_color=t["color"], corner_radius=8, padx=8, pady=3,
                ).pack(side="left", padx=2)

        # Decrypted text
        text = ""
        if row["content_encrypted"] and self.enc.is_unlocked():
            try:
                text = self.enc.decrypt(row["content_encrypted"])
            except Exception:
                text = "[Impossible de déchiffrer le contenu]"

        text_widget = ctk.CTkTextbox(
            content_frame, font=ctk.CTkFont(size=13), wrap="word",
            fg_color="transparent", height=400,
        )
        text_widget.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        text_widget.insert("1.0", text)
        text_widget.configure(state="disabled")

        self._current_panel = panel

    def _edit_entry(self, entry_id: int):
        row = self.db.get_entry(entry_id)
        if not row:
            return
        text = ""
        if row["content_encrypted"] and self.enc.is_unlocked():
            try:
                text = self.enc.decrypt(row["content_encrypted"])
            except Exception:
                pass
        tags = self.db.get_entry_tags(entry_id)
        tag_ids = [t["id"] for t in tags]
        audio_path = Path(row["audio_path"]) if row["audio_path"] else None
        self._show_editor(
            audio_path=audio_path,
            duration=row["duration"] or 0,
            entry_id=entry_id,
            existing_text=text,
            existing_title=row["title"] or "",
            existing_emoji=row["emoji"] or "",
            existing_tag_ids=tag_ids,
        )

    def _delete_entry(self, entry_id: int):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirmer la suppression")
        dialog.geometry("320x140")
        dialog.resizable(False, False)

        ctk.CTkLabel(
            dialog, text="Supprimer cette entrée ?",
            font=ctk.CTkFont(size=14)
        ).pack(pady=(24, 8))
        ctk.CTkLabel(
            dialog, text="Cette action est irréversible.",
            text_color=COLOR_TEXT_MUTED, font=ctk.CTkFont(size=11)
        ).pack()

        btns = ctk.CTkFrame(dialog, fg_color="transparent")
        btns.pack(pady=16)
        ctk.CTkButton(
            btns, text="Annuler", width=100,
            fg_color="transparent", border_width=1, border_color="gray",
            command=dialog.destroy,
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btns, text="Supprimer", width=100,
            fg_color="#c0392b", hover_color="#e74c3c",
            command=lambda: self._confirm_delete(entry_id, dialog),
        ).pack(side="left", padx=8)
        dialog.after(100, dialog.grab_set)

    def _confirm_delete(self, entry_id: int, dialog):
        self.db.delete_entry(entry_id)
        dialog.destroy()
        self._show_list()

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _show_stats(self):
        self._clear_content()
        self._set_nav_active(PANEL_STATS)
        panel = StatsView(self._content, self.db)
        panel.grid(row=0, column=0, sticky="nsew")
        self._current_panel = panel

    # ── Settings ──────────────────────────────────────────────────────────────

    def _open_settings(self):
        from gui.settings_window import SettingsWindow
        SettingsWindow(
            self, self.db, self.enc,
            log_path=self.log_path,
            on_settings_changed=self._reload_settings,
        )

    def _reload_settings(self):
        self._settings = self._load_settings()
        self._transcriber.reload_model(
            self._settings.get("whisper_model", "base"),
            self._settings.get("language", "fr"),
        )

    # ── Export ─────────────────────────────────────────────────────────────────

    def _open_export(self):
        from gui.export_window import ExportWindow
        # Export all entries or selected
        if hasattr(self, "_entry_list") and self._entry_list.get_selected_id():
            ids = [self._entry_list.get_selected_id()]
        else:
            ids = [row["id"] for row in self.db.list_entries(limit=10000)]

        if not ids:
            return
        ExportWindow(self, self._exporter, ids)

    # ── Keyboard shortcuts ─────────────────────────────────────────────────────

    def _bind_shortcuts(self):
        self.bind("<F5>", lambda e: self._start_recording())
        self.bind("<Control-r>", lambda e: self._start_recording())
        self.bind("<Control-f>", lambda e: self._focus_search())
        self.bind("<Control-comma>", lambda e: self._open_settings())
        self.bind("<Control-e>", lambda e: self._open_export())
        self.bind("<Escape>", lambda e: self._show_list())

    def _focus_search(self):
        self._show_list()
        # Entry list will have a search box; give it focus
        if hasattr(self, "_entry_list"):
            for w in self._entry_list.winfo_children():
                if isinstance(w, ctk.CTkFrame):
                    for c in w.winfo_children():
                        if isinstance(c, ctk.CTkEntry):
                            c.focus()
                            return
