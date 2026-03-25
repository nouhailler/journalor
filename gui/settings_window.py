"""Settings window."""

import base64
import tkinter as tk
import customtkinter as ctk
from pathlib import Path

from core.database import Database
from core.encryption import EncryptionManager, generate_salt, hash_pin
from utils.constants import (
    MODEL_CATALOG, WHISPER_DEFAULT, COLOR_ACCENT, COLOR_ERROR,
    COLOR_SUCCESS, COLOR_TEXT_MUTED, COLOR_WARNING,
    SILENCE_DURATION_DEFAULT,
)
from utils.validators import validate_pin


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, db: Database, enc: EncryptionManager,
                 on_settings_changed: callable = None):
        super().__init__(master)
        self.title("Paramètres — Journalor")
        self.geometry("560x700")
        self.resizable(False, False)
        self.db = db
        self.enc = enc
        self.on_settings_changed = on_settings_changed
        self.grab_set()
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self)
        scroll.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        scroll.grid_columnconfigure(1, weight=1)

        row = 0

        def section(text):
            nonlocal row
            ctk.CTkLabel(
                scroll, text=text,
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
            ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(16, 4))
            row += 1

        def field(label, widget_factory):
            nonlocal row
            ctk.CTkLabel(scroll, text=label, anchor="w").grid(
                row=row, column=0, sticky="w", padx=(0, 16), pady=4
            )
            w = widget_factory(scroll)
            w.grid(row=row, column=1, sticky="ew", pady=4)
            row += 1
            return w

        # ── Transcription ──────────────────────────────────────────────────
        section("Transcription")

        model_val = self.db.get_setting("whisper_model", WHISPER_DEFAULT)
        # Fallback si l'ancienne valeur n'existe plus dans le catalogue
        if model_val not in MODEL_CATALOG:
            model_val = WHISPER_DEFAULT
        self._model_var = tk.StringVar(value=model_val)

        # Combobox + fiche descriptive sur toute la largeur
        ctk.CTkLabel(scroll, text="Modèle Whisper", anchor="w").grid(
            row=row, column=0, sticky="w", padx=(0, 16), pady=(4, 0)
        )
        display_names = [MODEL_CATALOG[k]["display"] for k in MODEL_CATALOG]
        model_ids     = list(MODEL_CATALOG.keys())
        cur_display   = MODEL_CATALOG[model_val]["display"]
        self._combo_display_var = tk.StringVar(value=cur_display)

        combo = ctk.CTkComboBox(
            scroll,
            values=display_names,
            variable=self._combo_display_var,
            command=self._on_model_changed,
            state="readonly",
            width=280,
        )
        combo.grid(row=row, column=1, sticky="ew", pady=(4, 0))
        row += 1

        # Fiche descriptive (occupe les 2 colonnes)
        self._model_card = ctk.CTkFrame(scroll, fg_color="#0d1b2a", corner_radius=10)
        self._model_card.grid(row=row, column=0, columnspan=2, sticky="ew",
                              pady=(6, 8), padx=0)
        self._model_card.grid_columnconfigure(0, weight=1)
        row += 1
        self._build_model_card(model_val)

        lang_val = self.db.get_setting("language", "fr")
        self._lang_var = tk.StringVar(value=lang_val)
        field("Langue", lambda p: ctk.CTkOptionMenu(
            p, values=["fr", "en", "de", "es", "it", "pt", "auto"],
            variable=self._lang_var,
        ))

        # ── Audio ──────────────────────────────────────────────────────────
        section("Enregistrement audio")

        silence_val = float(self.db.get_setting("silence_duration", str(SILENCE_DURATION_DEFAULT)))
        self._silence_var = tk.DoubleVar(value=silence_val)
        nonlocal_silence_label = {"label": None}

        def make_silence_slider(p):
            sl = ctk.CTkSlider(p, from_=0, to=10, variable=self._silence_var,
                               command=lambda v: lbl.configure(text=f"{v:.0f}s"))
            return sl

        ctk.CTkLabel(scroll, text="Durée silence (auto-stop)", anchor="w").grid(
            row=row, column=0, sticky="w", padx=(0, 16), pady=4
        )
        sl_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        sl_frame.grid(row=row, column=1, sticky="ew", pady=4)
        sl_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkSlider(
            sl_frame, from_=0, to=10, variable=self._silence_var,
        ).grid(row=0, column=0, sticky="ew")
        lbl = ctk.CTkLabel(sl_frame, text=f"{silence_val:.0f}s", width=30)
        lbl.grid(row=0, column=1, padx=(4, 0))
        self._silence_var.trace_add("write", lambda *_: lbl.configure(text=f"{self._silence_var.get():.0f}s"))
        row += 1

        # ── Storage ────────────────────────────────────────────────────────
        section("Stockage")

        save_dir = self.db.get_setting("save_dir", str(Path.home() / "journalor_data"))
        self._save_dir_var = tk.StringVar(value=save_dir)

        ctk.CTkLabel(scroll, text="Dossier de sauvegarde", anchor="w").grid(
            row=row, column=0, sticky="w", padx=(0, 16), pady=4
        )
        dir_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        dir_frame.grid(row=row, column=1, sticky="ew", pady=4)
        dir_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(dir_frame, textvariable=self._save_dir_var).grid(
            row=0, column=0, sticky="ew"
        )
        ctk.CTkButton(
            dir_frame, text="…", width=32,
            command=self._browse_dir,
        ).grid(row=0, column=1, padx=(4, 0))
        row += 1

        # ── Security ───────────────────────────────────────────────────────
        section("Sécurité")

        ctk.CTkLabel(scroll, text="Nouveau PIN", anchor="w").grid(
            row=row, column=0, sticky="w", padx=(0, 16), pady=4
        )
        self._pin_entry = ctk.CTkEntry(scroll, show="●", placeholder_text="Nouveau PIN")
        self._pin_entry.grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        ctk.CTkLabel(scroll, text="Confirmer PIN", anchor="w").grid(
            row=row, column=0, sticky="w", padx=(0, 16), pady=4
        )
        self._pin2_entry = ctk.CTkEntry(scroll, show="●", placeholder_text="Confirmer PIN")
        self._pin2_entry.grid(row=row, column=1, sticky="ew", pady=4)
        row += 1

        self._pin_error = ctk.CTkLabel(
            scroll, text="", text_color=COLOR_ERROR, font=ctk.CTkFont(size=11)
        )
        self._pin_error.grid(row=row, column=0, columnspan=2, pady=(0, 4))
        row += 1

        # ── Save button ────────────────────────────────────────────────────
        ctk.CTkButton(
            scroll, text="Sauvegarder les paramètres",
            fg_color=COLOR_ACCENT, hover_color="#c73652",
            height=42, font=ctk.CTkFont(size=13, weight="bold"),
            command=self._save,
        ).grid(row=row, column=0, columnspan=2, sticky="ew", pady=(16, 0))

    def _on_model_changed(self, display_name: str):
        """Sync _model_var (model ID) from the combo display name, refresh card."""
        for model_id, info in MODEL_CATALOG.items():
            if info["display"] == display_name:
                self._model_var.set(model_id)
                self._build_model_card(model_id)
                return

    def _build_model_card(self, model_id: str):
        """Render the pros/cons/speed card for the given model ID."""
        for w in self._model_card.winfo_children():
            w.destroy()

        info = MODEL_CATALOG.get(model_id, {})
        if not info:
            return

        card = self._model_card
        pad = {"padx": 14}

        # RAM + vitesse + qualité en ligne
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=(10, 4), **pad)
        top.grid_columnconfigure((0, 1, 2), weight=1)

        def badge(parent, label, value, col):
            ctk.CTkLabel(parent, text=label,
                         font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED
                         ).grid(row=0, column=col, sticky="w")
            ctk.CTkLabel(parent, text=value,
                         font=ctk.CTkFont(size=12, weight="bold")
                         ).grid(row=1, column=col, sticky="w")

        badge(top, "RAM", info["ram"], 0)
        badge(top, "Vitesse", "⚡" * info["speed"] + "·" * (5 - info["speed"]), 1)
        badge(top, "Qualité", "★" * info["quality"] + "☆" * (5 - info["quality"]), 2)

        # Note spéciale
        if info.get("note"):
            ctk.CTkLabel(
                card, text=f"💡 {info['note']}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=COLOR_SUCCESS, anchor="w",
            ).grid(row=1, column=0, sticky="w", pady=(0, 4), **pad)

        # Avantages / Inconvénients côte à côte
        cols_frame = ctk.CTkFrame(card, fg_color="transparent")
        cols_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10), **pad)
        cols_frame.grid_columnconfigure((0, 1), weight=1)

        def bullet_list(parent, title, items, color, col):
            ctk.CTkLabel(parent, text=title,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=color, anchor="w",
                         ).grid(row=0, column=col, sticky="w", padx=(0, 8))
            for i, item in enumerate(items):
                ctk.CTkLabel(
                    parent, text=f"  • {item}",
                    font=ctk.CTkFont(size=11),
                    anchor="w", wraplength=180, justify="left",
                ).grid(row=i + 1, column=col, sticky="w", padx=(0, 8))

        bullet_list(cols_frame, "✅ Avantages", info["pros"], COLOR_SUCCESS, 0)
        bullet_list(cols_frame, "⚠️ Inconvénients", info["cons"], COLOR_WARNING, 1)

    def _browse_dir(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(
            title="Choisir le dossier de sauvegarde",
            initialdir=self._save_dir_var.get(),
        )
        if path:
            self._save_dir_var.set(path)

    def _save(self):
        self._pin_error.configure(text="")

        # PIN change (optional)
        pin1 = self._pin_entry.get()
        pin2 = self._pin2_entry.get()
        if pin1 or pin2:
            ok, msg = validate_pin(pin1)
            if not ok:
                self._pin_error.configure(text=msg)
                return
            if pin1 != pin2:
                self._pin_error.configure(text="Les PINs ne correspondent pas.")
                return
            salt = generate_salt()
            pin_hash = hash_pin(pin1, salt)
            self.db.set_setting("pin_hash", pin_hash)
            self.db.set_setting("pin_salt", base64.b64encode(salt).decode())
            self.enc.unlock(pin1, salt)

        # _model_var contient l'ID réel du modèle (ex: "distil-whisper/distil-large-v3")
        self.db.set_setting("whisper_model", self._model_var.get())
        self.db.set_setting("language", self._lang_var.get())
        self.db.set_setting("silence_duration", str(int(self._silence_var.get())))
        save_dir = self._save_dir_var.get().strip()
        if save_dir:
            self.db.set_setting("save_dir", save_dir)
            Path(save_dir).mkdir(parents=True, exist_ok=True)

        if self.on_settings_changed:
            self.on_settings_changed()

        self.destroy()
