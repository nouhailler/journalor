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
        self.geometry("580x740")
        self.resizable(False, True)
        self.db = db
        self.enc = enc
        self.on_settings_changed = on_settings_changed
        self._build()
        self.after(100, self.grab_set)

    # ── Layout principal ───────────────────────────────────────────────────────

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(self)
        scroll.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        scroll.grid_columnconfigure(0, weight=1)

        # ── Transcription ──────────────────────────────────────────────────────
        self._section(scroll, "🎙️  Transcription", row=0)

        # Sélecteur de modèle
        self._build_model_selector(scroll, row=1)

        # Langue
        self._label(scroll, "Langue de transcription", row=3)
        lang_val = self.db.get_setting("language", "fr")
        self._lang_var = tk.StringVar(value=lang_val)
        ctk.CTkOptionMenu(
            scroll,
            values=["fr", "en", "de", "es", "it", "pt", "auto"],
            variable=self._lang_var,
        ).grid(row=3, column=0, sticky="w", pady=4, padx=(160, 0))

        # ── Audio ──────────────────────────────────────────────────────────────
        self._section(scroll, "🔊  Enregistrement audio", row=4)

        silence_val = float(
            self.db.get_setting("silence_duration", str(SILENCE_DURATION_DEFAULT))
        )
        self._silence_var = tk.DoubleVar(value=silence_val)
        self._build_silence_slider(scroll, row=5)

        # ── Stockage ───────────────────────────────────────────────────────────
        self._section(scroll, "💾  Stockage", row=6)
        self._build_dir_picker(scroll, row=7)

        # ── Sécurité ───────────────────────────────────────────────────────────
        self._section(scroll, "🔒  Sécurité — Changer le PIN", row=8)
        self._build_pin_fields(scroll, row=9)

        # ── Bouton sauvegarder ─────────────────────────────────────────────────
        ctk.CTkButton(
            scroll,
            text="✅  Sauvegarder les paramètres",
            fg_color=COLOR_ACCENT, hover_color="#c73652",
            height=44, font=ctk.CTkFont(size=14, weight="bold"),
            command=self._save,
        ).grid(row=12, column=0, sticky="ew", pady=(20, 4))

    # ── Helpers de mise en page ────────────────────────────────────────────────

    def _section(self, parent, text: str, row: int):
        ctk.CTkLabel(
            parent, text=text,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(18, 4))

    def _label(self, parent, text: str, row: int):
        ctk.CTkLabel(parent, text=text, anchor="w").grid(
            row=row, column=0, sticky="w", pady=(4, 0)
        )

    # ── Sélecteur de modèle Whisper ────────────────────────────────────────────

    def _build_model_selector(self, parent, row: int):
        model_val = self.db.get_setting("whisper_model", WHISPER_DEFAULT)
        if model_val not in MODEL_CATALOG:
            model_val = WHISPER_DEFAULT
        self._current_model_id = model_val

        display_names = [MODEL_CATALOG[k]["display"] for k in MODEL_CATALOG]

        # Label + ComboBox sur la même ligne
        row_frame = ctk.CTkFrame(parent, fg_color="transparent")
        row_frame.grid(row=row, column=0, sticky="ew", pady=(0, 4))
        row_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            row_frame, text="Modèle Whisper",
            anchor="w", width=160,
        ).grid(row=0, column=0, sticky="w")

        self._combo = ctk.CTkComboBox(
            row_frame,
            values=display_names,
            command=self._on_model_changed,
            width=340,
        )
        self._combo.set(MODEL_CATALOG[model_val]["display"])
        self._combo.grid(row=0, column=1, sticky="ew")

        # Fiche descriptive (ligne suivante, pleine largeur)
        self._card_frame = ctk.CTkFrame(parent, fg_color="#0d1b2a", corner_radius=10)
        self._card_frame.grid(row=row + 1, column=0, sticky="ew", pady=(0, 8))
        self._card_frame.grid_columnconfigure(0, weight=1)
        self._refresh_card(model_val)

    def _on_model_changed(self, display_name: str):
        for model_id, info in MODEL_CATALOG.items():
            if info["display"] == display_name:
                self._current_model_id = model_id
                self._refresh_card(model_id)
                return

    def _refresh_card(self, model_id: str):
        for w in self._card_frame.winfo_children():
            w.destroy()

        info = MODEL_CATALOG.get(model_id)
        if not info:
            return

        p = {"padx": 16}

        # ── Ligne badges RAM / Vitesse / Qualité ───────────────────────────
        badges = ctk.CTkFrame(self._card_frame, fg_color="transparent")
        badges.grid(row=0, column=0, sticky="ew", pady=(12, 6), **p)
        for col, (lbl, val) in enumerate([
            ("RAM",     info["ram"]),
            ("Vitesse", "⚡" * info["speed"] + "·" * (5 - info["speed"])),
            ("Qualité", "★" * info["quality"] + "☆" * (5 - info["quality"])),
        ]):
            badges.grid_columnconfigure(col, weight=1)
            ctk.CTkLabel(badges, text=lbl,
                         font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED,
                         ).grid(row=0, column=col, sticky="w")
            ctk.CTkLabel(badges, text=val,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         ).grid(row=1, column=col, sticky="w")

        # ── Note spéciale ──────────────────────────────────────────────────
        if info.get("note"):
            ctk.CTkLabel(
                self._card_frame,
                text=f"💡 {info['note']}",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=COLOR_SUCCESS, anchor="w",
            ).grid(row=1, column=0, sticky="w", pady=(0, 6), **p)

        # ── Avantages / Inconvénients ──────────────────────────────────────
        pros_cons = ctk.CTkFrame(self._card_frame, fg_color="transparent")
        pros_cons.grid(row=2, column=0, sticky="ew", pady=(0, 12), **p)
        pros_cons.grid_columnconfigure((0, 1), weight=1)

        def bullets(col, title, items, color):
            ctk.CTkLabel(pros_cons, text=title,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=color, anchor="w",
                         ).grid(row=0, column=col, sticky="w", padx=(0, 10))
            for i, item in enumerate(items):
                ctk.CTkLabel(
                    pros_cons,
                    text=f"• {item}",
                    font=ctk.CTkFont(size=11),
                    anchor="w", wraplength=200, justify="left",
                ).grid(row=i + 1, column=col, sticky="w", padx=(0, 10), pady=1)

        bullets(0, "✅ Avantages",      info["pros"], COLOR_SUCCESS)
        bullets(1, "⚠️ Inconvénients", info["cons"], COLOR_WARNING)

    # ── Slider silence ─────────────────────────────────────────────────────────

    def _build_silence_slider(self, parent, row: int):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", pady=4)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Silence avant arrêt auto", width=160, anchor="w"
                     ).grid(row=0, column=0, sticky="w")

        slider = ctk.CTkSlider(frame, from_=0, to=10, variable=self._silence_var)
        slider.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        self._silence_lbl = ctk.CTkLabel(
            frame, text=f"{int(self._silence_var.get())}s", width=30
        )
        self._silence_lbl.grid(row=0, column=2)
        self._silence_var.trace_add(
            "write",
            lambda *_: self._silence_lbl.configure(text=f"{int(self._silence_var.get())}s"),
        )

    # ── Dossier de sauvegarde ──────────────────────────────────────────────────

    def _build_dir_picker(self, parent, row: int):
        save_dir = self.db.get_setting("save_dir", str(Path.home() / "journalor_data"))
        self._save_dir_var = tk.StringVar(value=save_dir)

        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", pady=4)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Dossier de sauvegarde", width=160, anchor="w"
                     ).grid(row=0, column=0, sticky="w")
        ctk.CTkEntry(frame, textvariable=self._save_dir_var).grid(
            row=0, column=1, sticky="ew", padx=(0, 8)
        )
        ctk.CTkButton(frame, text="…", width=36, command=self._browse_dir
                      ).grid(row=0, column=2)

    def _browse_dir(self):
        from tkinter import filedialog
        path = filedialog.askdirectory(
            title="Choisir le dossier de sauvegarde",
            initialdir=self._save_dir_var.get(),
        )
        if path:
            self._save_dir_var.set(path)

    # ── Champs PIN ─────────────────────────────────────────────────────────────

    def _build_pin_fields(self, parent, row: int):
        for r, (label, attr) in enumerate([
            ("Nouveau PIN",   "_pin_entry"),
            ("Confirmer PIN", "_pin2_entry"),
        ]):
            frame = ctk.CTkFrame(parent, fg_color="transparent")
            frame.grid(row=row + r, column=0, sticky="ew", pady=3)
            frame.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(frame, text=label, width=160, anchor="w"
                         ).grid(row=0, column=0, sticky="w")
            entry = ctk.CTkEntry(frame, show="●", placeholder_text=label)
            entry.grid(row=0, column=1, sticky="ew")
            setattr(self, attr, entry)

        self._pin_error = ctk.CTkLabel(
            parent, text="", text_color=COLOR_ERROR, font=ctk.CTkFont(size=11)
        )
        self._pin_error.grid(row=row + 2, column=0, sticky="w", pady=(0, 4))

    # ── Sauvegarde ─────────────────────────────────────────────────────────────

    def _save(self):
        self._pin_error.configure(text="")

        # PIN (optionnel)
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
            self.db.set_setting("pin_hash", hash_pin(pin1, salt))
            self.db.set_setting("pin_salt", base64.b64encode(salt).decode())
            self.enc.unlock(pin1, salt)

        self.db.set_setting("whisper_model", self._current_model_id)
        self.db.set_setting("language", self._lang_var.get())
        self.db.set_setting("silence_duration", str(int(self._silence_var.get())))

        save_dir = self._save_dir_var.get().strip()
        if save_dir:
            self.db.set_setting("save_dir", save_dir)
            Path(save_dir).mkdir(parents=True, exist_ok=True)

        if self.on_settings_changed:
            self.on_settings_changed()

        self.destroy()
