"""Export dialog."""

import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk

from core.export import Exporter
from utils.constants import COLOR_ACCENT, COLOR_SUCCESS, COLOR_ERROR


class ExportWindow(ctk.CTkToplevel):
    def __init__(self, master, exporter: Exporter, entry_ids: list[int]):
        super().__init__(master)
        self.title("Exporter")
        self.geometry("400x300")
        self.resizable(False, False)
        self.exporter = exporter
        self.entry_ids = entry_ids
        self.grab_set()
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text=f"Exporter {len(self.entry_ids)} entrée(s)",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, pady=(20, 16))

        self._fmt_var = tk.StringVar(value="txt")
        for i, (label, val) in enumerate([
            ("Texte brut (.txt)", "txt"),
            ("Markdown (.md)", "markdown"),
            ("PDF (.pdf)", "pdf"),
            ("JSON (backup)", "json"),
        ]):
            ctk.CTkRadioButton(
                self, text=label, variable=self._fmt_var, value=val
            ).grid(row=i + 1, column=0, sticky="w", padx=32, pady=3)

        self._status = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12))
        self._status.grid(row=6, column=0, pady=8)

        ctk.CTkButton(
            self, text="Choisir destination et exporter",
            fg_color=COLOR_ACCENT, hover_color="#c73652",
            height=40, command=self._export,
        ).grid(row=7, column=0, padx=32, sticky="ew", pady=(0, 16))

    def _export(self):
        fmt = self._fmt_var.get()
        ext_map = {"txt": ".txt", "markdown": ".md", "pdf": ".pdf", "json": ".json"}
        ext = ext_map[fmt]
        default_name = f"journal_export{ext}"

        path = filedialog.asksaveasfilename(
            defaultextension=ext,
            initialfile=default_name,
            filetypes=[(f"Fichier {ext}", f"*{ext}"), ("Tous", "*.*")],
        )
        if not path:
            return

        from pathlib import Path
        output = Path(path)
        try:
            if fmt == "txt":
                self.exporter.export_txt(self.entry_ids, output)
            elif fmt == "markdown":
                self.exporter.export_markdown(self.entry_ids, output)
            elif fmt == "pdf":
                self.exporter.export_pdf(self.entry_ids, output)
            elif fmt == "json":
                self.exporter.export_json(self.entry_ids, output)
            self._status.configure(text=f"✓ Exporté : {output.name}", text_color=COLOR_SUCCESS)
        except Exception as exc:
            self._status.configure(text=f"Erreur : {exc}", text_color=COLOR_ERROR)
