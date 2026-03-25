"""Statistics view with usage charts."""

import tkinter as tk
import customtkinter as ctk
from datetime import datetime, timedelta

from core.database import Database
from utils.constants import COLOR_ACCENT, COLOR_TEXT_MUTED, COLOR_SUCCESS
from utils.formatters import format_duration


class StatsView(ctk.CTkScrollableFrame):
    """Display usage statistics."""

    def __init__(self, master, db: Database, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.db = db
        self.grid_columnconfigure(0, weight=1)
        self._build()

    def _build(self):
        for w in self.winfo_children():
            w.destroy()

        ctk.CTkLabel(
            self, text="Statistiques",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 20))

        # Summary cards
        cards_frame = ctk.CTkFrame(self, fg_color="transparent")
        cards_frame.grid(row=1, column=0, sticky="ew", pady=(0, 24))

        total = self.db.count_entries()
        words = self.db.total_words()
        dur = self.db.total_duration()
        streak = self._compute_streak()

        stats = [
            ("📝", str(total), "entrées totales"),
            ("💬", f"{words:,}", "mots écrits"),
            ("⏱️", format_duration(dur), "enregistrés"),
            ("🔥", str(streak), "jours consécutifs"),
        ]

        for i, (icon, value, label) in enumerate(stats):
            self._stat_card(cards_frame, icon, value, label, i)

        # Activity bar chart (last 30 days)
        ctk.CTkLabel(
            self, text="Activité — 30 derniers jours",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=2, column=0, sticky="w", pady=(0, 8))

        self._draw_activity_chart()

    def _stat_card(self, parent, icon, value, label, col):
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color="#16213e")
        card.grid(row=0, column=col, padx=6, sticky="ew")
        parent.grid_columnconfigure(col, weight=1)

        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(size=28)).pack(pady=(16, 4))
        ctk.CTkLabel(card, text=value,
                     font=ctk.CTkFont(size=24, weight="bold")).pack()
        ctk.CTkLabel(card, text=label,
                     font=ctk.CTkFont(size=11), text_color=COLOR_TEXT_MUTED).pack(pady=(0, 16))

    def _draw_activity_chart(self):
        """Draw a simple canvas bar chart for the last 30 days."""
        today = datetime.now().date()
        dates = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(29, -1, -1)]

        counts = {}
        for row in self.db.list_entries(limit=500):
            d = row["date"]
            counts[d] = counts.get(d, 0) + 1

        max_count = max((counts.get(d, 0) for d in dates), default=1) or 1

        frame = ctk.CTkFrame(self, fg_color="#16213e", corner_radius=12)
        frame.grid(row=3, column=0, sticky="ew", pady=(0, 24))

        canvas = tk.Canvas(frame, height=100, bg="#16213e", highlightthickness=0)
        canvas.pack(fill="x", padx=16, pady=12)

        def _draw(event=None):
            canvas.delete("all")
            w = canvas.winfo_width()
            h = canvas.winfo_height()
            if w < 10:
                return
            n = len(dates)
            bar_w = max(2, (w - 20) // n - 2)
            gap = (w - 20) // n

            for i, d in enumerate(dates):
                c = counts.get(d, 0)
                ratio = c / max_count
                bh = max(4, int(ratio * (h - 20)))
                x = 10 + i * gap
                color = COLOR_ACCENT if c > 0 else "#2a2a4a"
                canvas.create_rectangle(
                    x, h - bh - 4,
                    x + bar_w, h - 4,
                    fill=color, outline="",
                )

        canvas.bind("<Configure>", _draw)
        canvas.after(100, _draw)

    def _compute_streak(self) -> int:
        dates = set(self.db.dates_with_entries())
        if not dates:
            return 0
        streak = 0
        today = datetime.now().date()
        cur = today
        while cur.strftime("%Y-%m-%d") in dates:
            streak += 1
            cur -= timedelta(days=1)
        return streak

    def refresh(self):
        self._build()
