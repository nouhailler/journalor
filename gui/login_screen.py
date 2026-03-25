"""Login / first-run PIN setup screen."""

import base64
import tkinter as tk
import customtkinter as ctk

from core.encryption import generate_salt, hash_pin, EncryptionManager
from core.database import Database
from utils.validators import validate_pin
from utils.constants import COLOR_ACCENT, COLOR_ERROR, APP_NAME


class LoginScreen(ctk.CTkFrame):
    """
    Displayed at startup. If no PIN exists → setup mode.
    Otherwise → login mode.
    on_success(password) is called after unlock.
    """

    def __init__(self, master, db: Database, enc: EncryptionManager, on_success: callable):
        super().__init__(master, fg_color="transparent")
        self.db = db
        self.enc = enc
        self.on_success = on_success
        self._setup_mode = db.get_setting("pin_hash") is None
        self._attempts = 0
        self._build_ui()

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(self, width=480, corner_radius=16)
        card.grid(row=0, column=0)
        card.grid_propagate(False)
        card.configure(height=540)

        # App title
        ctk.CTkLabel(
            card, text="🎙️", font=ctk.CTkFont(size=52)
        ).pack(pady=(36, 4))
        ctk.CTkLabel(
            card, text=APP_NAME,
            font=ctk.CTkFont(size=28, weight="bold")
        ).pack()
        ctk.CTkLabel(
            card, text="Journal vocal personnel",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        ).pack(pady=(0, 24))

        if self._setup_mode:
            ctk.CTkLabel(
                card, text="Créez votre code PIN",
                font=ctk.CTkFont(size=15, weight="bold")
            ).pack()
            ctk.CTkLabel(
                card, text="4 à 8 chiffres",
                font=ctk.CTkFont(size=12),
                text_color="gray"
            ).pack(pady=(0, 12))

            self._pin1 = self._pin_entry(card)
            self._pin1.pack(padx=40, pady=(0, 8))
            ctk.CTkLabel(card, text="Confirmez le PIN").pack()
            self._pin2 = self._pin_entry(card)
            self._pin2.pack(padx=40, pady=(4, 12))

            btn_text = "Créer le PIN"
        else:
            ctk.CTkLabel(
                card, text="Entrez votre PIN",
                font=ctk.CTkFont(size=15, weight="bold")
            ).pack(pady=(0, 12))
            self._pin1 = self._pin_entry(card)
            self._pin1.pack(padx=40, pady=(0, 16))
            self._pin2 = None
            btn_text = "Déverrouiller"

        self._error_label = ctk.CTkLabel(
            card, text="", text_color=COLOR_ERROR,
            font=ctk.CTkFont(size=12), wraplength=300
        )
        self._error_label.pack()

        ctk.CTkButton(
            card, text=btn_text,
            fg_color=COLOR_ACCENT, hover_color="#c73652",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=42,
            command=self._submit,
        ).pack(padx=40, fill="x", pady=(8, 0))

        self._pin1.bind("<Return>", lambda e: self._submit())
        if self._pin2:
            self._pin2.bind("<Return>", lambda e: self._submit())

        self._pin1.focus()

    def _pin_entry(self, parent) -> ctk.CTkEntry:
        return ctk.CTkEntry(
            parent, show="●", placeholder_text="PIN",
            font=ctk.CTkFont(size=20),
            height=48, justify="center",
        )

    def _submit(self):
        pin = self._pin1.get()
        ok, msg = validate_pin(pin)
        if not ok:
            self._show_error(msg)
            return

        if self._setup_mode:
            pin2 = self._pin2.get()
            if pin != pin2:
                self._show_error("Les PINs ne correspondent pas.")
                return
            salt = generate_salt()
            pin_hash = hash_pin(pin, salt)
            self.db.set_setting("pin_hash", pin_hash)
            self.db.set_setting("pin_salt", base64.b64encode(salt).decode())
            self.enc.unlock(pin, salt)
            self.on_success(pin)
        else:
            salt_b64 = self.db.get_setting("pin_salt")
            salt = base64.b64decode(salt_b64)
            expected = self.db.get_setting("pin_hash")
            actual = hash_pin(pin, salt)
            if actual != expected:
                self._attempts += 1
                remaining = 5 - self._attempts
                if remaining <= 0:
                    self._show_error("Trop de tentatives. Fermeture.")
                    self.after(1500, self.winfo_toplevel().destroy)
                else:
                    self._show_error(f"PIN incorrect. {remaining} tentative(s) restante(s).")
                    self._pin1.delete(0, "end")
                return
            self.enc.unlock(pin, salt)
            self.on_success(pin)

    def _show_error(self, msg: str):
        self._error_label.configure(text=msg)
