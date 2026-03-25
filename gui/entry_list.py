"""Chronological list of journal entries."""

import tkinter as tk
import customtkinter as ctk

from core.database import Database
from core.encryption import EncryptionManager
from utils.constants import COLOR_ACCENT, COLOR_TEXT_MUTED, COLOR_SURFACE, COLOR_SURFACE2
from utils.formatters import format_date_display, format_time_display, format_word_count, truncate_text


class EntryCard(ctk.CTkFrame):
    """A single entry card in the list."""

    def __init__(self, master, row, tags, content_preview: str, on_click: callable, **kwargs):
        super().__init__(master, corner_radius=10, cursor="hand2", **kwargs)
        self._on_click = on_click
        self._build(row, tags, content_preview)
        self.bind("<Button-1>", lambda e: on_click())
        for child in self.winfo_children():
            child.bind("<Button-1>", lambda e: on_click())

    def _build(self, row, tags, preview: str):
        self.grid_columnconfigure(1, weight=1)

        # Emoji / date column
        emoji = row["emoji"] or "📝"
        ctk.CTkLabel(
            self, text=emoji,
            font=ctk.CTkFont(size=24), width=44,
        ).grid(row=0, column=0, rowspan=2, padx=(12, 8), pady=12, sticky="n")

        # Top row: title + time
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=1, sticky="ew", pady=(10, 0), padx=(0, 12))
        top.grid_columnconfigure(0, weight=1)

        title = row["title"] or "Sans titre"
        ctk.CTkLabel(
            top, text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        date_str = f"{format_date_display(row['date'])}  {format_time_display(row['time'])}"
        ctk.CTkLabel(
            top, text=date_str,
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED, anchor="e",
        ).grid(row=0, column=1, sticky="e", padx=(8, 0))

        # Preview text
        if preview:
            ctk.CTkLabel(
                self, text=truncate_text(preview, 100),
                font=ctk.CTkFont(size=11),
                text_color=COLOR_TEXT_MUTED, anchor="w", wraplength=420,
            ).grid(row=1, column=1, sticky="w", padx=(0, 12), pady=(0, 4))

        # Tags row
        if tags:
            tag_row = ctk.CTkFrame(self, fg_color="transparent")
            tag_row.grid(row=2, column=1, sticky="w", padx=(0, 12), pady=(0, 8))
            for t in tags[:5]:
                ctk.CTkLabel(
                    tag_row, text=t["name"],
                    font=ctk.CTkFont(size=10),
                    text_color="white",
                    fg_color=t["color"],
                    corner_radius=8,
                    padx=6, pady=2,
                ).pack(side="left", padx=2)

        # Word count
        ctk.CTkLabel(
            self,
            text=format_word_count(row["word_count"]),
            font=ctk.CTkFont(size=10),
            text_color=COLOR_TEXT_MUTED,
        ).grid(row=0, column=2, padx=(0, 12), pady=(12, 0), sticky="ne")


class EntryList(ctk.CTkFrame):
    """
    Scrollable list of journal entries.
    on_select(entry_id) called when user clicks an entry.
    """

    def __init__(self, master, db: Database, enc: EncryptionManager,
                 on_select: callable, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.db = db
        self.enc = enc
        self.on_select = on_select

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._on_search_change())

        self._build_toolbar()
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=1, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

        self._selected_id: int | None = None
        self.refresh()

    def _build_toolbar(self):
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        bar.grid_columnconfigure(0, weight=1)

        ctk.CTkEntry(
            bar,
            textvariable=self._search_var,
            placeholder_text="🔍  Rechercher...",
            height=36,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._count_label = ctk.CTkLabel(
            bar, text="",
            font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED
        )
        self._count_label.grid(row=0, column=1)

    def _on_search_change(self):
        self.refresh()

    def refresh(self, select_id: int | None = None):
        for w in self._scroll.winfo_children():
            w.destroy()

        query = self._search_var.get().strip()

        if query and self.enc.is_unlocked():
            from core.search import SearchEngine
            se = SearchEngine(self.db, self.enc)
            results = se.search(query)
            entries = [self.db.get_entry(r["id"]) for r in results]
            entries = [e for e in entries if e]
        else:
            entries = self.db.list_entries()

        self._count_label.configure(
            text=f"{len(entries)} entrée{'s' if len(entries) != 1 else ''}"
        )

        if not entries:
            ctk.CTkLabel(
                self._scroll,
                text="Aucune entrée trouvée." if query else "Aucune entrée.\nCommencez à enregistrer!",
                font=ctk.CTkFont(size=14),
                text_color=COLOR_TEXT_MUTED,
                justify="center",
            ).grid(row=0, column=0, pady=60)
            return

        for i, row in enumerate(entries):
            # Decrypt preview
            preview = ""
            if row["content_encrypted"] and self.enc.is_unlocked():
                try:
                    preview = self.enc.decrypt(row["content_encrypted"])
                except Exception:
                    pass

            tags = self.db.get_entry_tags(row["id"])
            card = EntryCard(
                self._scroll, row, tags, preview,
                on_click=lambda eid=row["id"]: self._select(eid),
                fg_color=COLOR_SURFACE2 if row["id"] == self._selected_id else COLOR_SURFACE,
            )
            card.grid(row=i, column=0, sticky="ew", pady=3, padx=2)

        if select_id is not None:
            self._selected_id = select_id

    def _select(self, entry_id: int):
        self._selected_id = entry_id
        self.refresh(select_id=entry_id)
        self.on_select(entry_id)

    def get_selected_id(self) -> int | None:
        return self._selected_id
