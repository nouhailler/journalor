"""Dialogue de téléchargement d'un modèle Whisper avec barre de progression."""

import tkinter as tk
import customtkinter as ctk

from core.model_downloader import download_model, is_model_cached, get_repo_id
from utils.constants import (
    MODEL_CATALOG, COLOR_ACCENT, COLOR_SUCCESS, COLOR_ERROR, COLOR_TEXT_MUTED
)


class DownloadDialog(ctk.CTkToplevel):
    """
    Vérifie si le modèle est en cache.
    - Si oui  → appelle on_ready() immédiatement (sans s'afficher).
    - Si non  → affiche la fenêtre de téléchargement avec barre de progression,
                puis appelle on_ready() quand tout est téléchargé.

    on_ready()  : appelé quand le modèle est prêt (cache ou fin de DL)
    on_cancel() : appelé si l'utilisateur ferme la fenêtre avant la fin
    """

    def __init__(
        self,
        master,
        model_name: str,
        on_ready:  callable,
        on_cancel: callable = None,
    ):
        self._model_name = model_name
        self._on_ready   = on_ready
        self._on_cancel  = on_cancel
        self._cancelled  = False

        # Vérification du cache — si déjà présent, pas besoin d'afficher la fenêtre
        if is_model_cached(model_name):
            master.after(0, on_ready)
            return

        super().__init__(master)
        self._build_ui(model_name)
        self.after(100, self.grab_set)
        self._start_download()

    def _build_ui(self, model_name: str):
        self.title("Téléchargement du modèle")
        self.geometry("480x300")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.grid_columnconfigure(0, weight=1)

        info = MODEL_CATALOG.get(model_name, {})
        display = info.get("display", model_name)
        repo_id = get_repo_id(model_name)

        # Icône + titre
        ctk.CTkLabel(
            self, text="⬇️",
            font=ctk.CTkFont(size=40),
        ).grid(row=0, column=0, pady=(28, 4))

        ctk.CTkLabel(
            self,
            text=f"Téléchargement du modèle",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=1, column=0)

        ctk.CTkLabel(
            self,
            text=display,
            font=ctk.CTkFont(size=13),
            text_color=COLOR_ACCENT,
        ).grid(row=2, column=0, pady=(0, 4))

        ctk.CTkLabel(
            self,
            text=f"Source : {repo_id}",
            font=ctk.CTkFont(size=10),
            text_color=COLOR_TEXT_MUTED,
        ).grid(row=3, column=0, pady=(0, 16))

        # Barre de progression
        self._bar = ctk.CTkProgressBar(self, width=380)
        self._bar.set(0)
        self._bar.grid(row=4, column=0, padx=40, sticky="ew")

        # Labels de statut
        self._status_pct = ctk.CTkLabel(
            self, text="Connexion au serveur...",
            font=ctk.CTkFont(size=12),
        )
        self._status_pct.grid(row=5, column=0, pady=(8, 2))

        self._status_file = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=10),
            text_color=COLOR_TEXT_MUTED,
            wraplength=420,
        )
        self._status_file.grid(row=6, column=0)

        # Note de patience
        ctk.CTkLabel(
            self,
            text="La transcription démarrera automatiquement à la fin.",
            font=ctk.CTkFont(size=10),
            text_color=COLOR_TEXT_MUTED,
        ).grid(row=7, column=0, pady=(12, 0))

        ctk.CTkButton(
            self, text="Annuler",
            fg_color="transparent", border_width=1, border_color="gray",
            width=100, height=32,
            command=self._on_close,
        ).grid(row=8, column=0, pady=(12, 20))

    def _start_download(self):
        download_model(
            self._model_name,
            on_start=self._on_start,
            on_progress=self._on_progress,
            on_done=self._on_done,
            on_error=self._on_error,
        )

    def _on_start(self, total_files: int):
        self._total = total_files
        self.after(0, lambda: self._status_pct.configure(
            text=f"0 / {total_files} fichiers téléchargés"
        ))

    def _on_progress(self, done: int, total: int, filename: str):
        def _update():
            if self._cancelled:
                return
            ratio = done / total if total else 0
            self._bar.set(ratio)
            pct = int(ratio * 100)
            self._status_pct.configure(
                text=f"{done} / {total} fichiers  ({pct} %)"
            )
            short = filename.split("/")[-1] if filename else ""
            self._status_file.configure(
                text=f"{'↓  ' + short if short else ''}"
            )
        self.after(0, _update)

    def _on_done(self):
        def _finish():
            if self._cancelled:
                return
            self._bar.set(1.0)
            self._status_pct.configure(
                text="✅  Téléchargement terminé !",
            )
            self._status_file.configure(text="Lancement de la transcription…")
            self.after(800, self._close_and_ready)
        self.after(0, _finish)

    def _on_error(self, message: str):
        def _show_err():
            self._bar.set(0)
            self._status_pct.configure(
                text=f"❌  Erreur : {message}",
                text_color=COLOR_ERROR,
            )
            self._status_file.configure(text="Vérifiez votre connexion Internet.")
        self.after(0, _show_err)

    def _close_and_ready(self):
        self.destroy()
        if self._on_ready:
            self._on_ready()

    def _on_close(self):
        self._cancelled = True
        self.destroy()
        if self._on_cancel:
            self._on_cancel()
