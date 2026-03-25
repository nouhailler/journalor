"""Dialogue de téléchargement d'un modèle Whisper avec progression octet par octet."""

import customtkinter as ctk

from core.model_downloader import download_model, is_model_cached, get_repo_id
from utils.constants import (
    MODEL_CATALOG, COLOR_ACCENT, COLOR_SUCCESS, COLOR_ERROR, COLOR_TEXT_MUTED
)


def _fmt_bytes(n: int) -> str:
    """Formate un nombre d'octets en Mo ou Go lisible."""
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f} Go"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.0f} Mo"
    if n >= 1_000:
        return f"{n / 1_000:.0f} Ko"
    return f"{n} o"


class DownloadDialog(ctk.CTkToplevel):
    """
    Vérifie si le modèle est en cache.
    - Si oui  → appelle on_ready() immédiatement (sans fenêtre).
    - Si non  → affiche le dialogue de progression, puis appelle on_ready().

    on_progress reçoit (bytes_done, bytes_total, filename).
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

        # Modèle déjà en cache → pas de fenêtre
        if is_model_cached(model_name):
            master.after(0, on_ready)
            return

        super().__init__(master)
        self._build_ui()
        self.after(100, self.grab_set)
        self._start_download()

    # ── Construction de l'interface ────────────────────────────────────────────

    def _build_ui(self):
        info    = MODEL_CATALOG.get(self._model_name, {})
        display = info.get("display", self._model_name)
        repo_id = get_repo_id(self._model_name)

        self.title("Téléchargement du modèle")
        self.geometry("500x320")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="⬇️", font=ctk.CTkFont(size=40)).grid(
            row=0, column=0, pady=(28, 2)
        )
        ctk.CTkLabel(
            self, text="Téléchargement du modèle",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=1, column=0)
        ctk.CTkLabel(
            self, text=display,
            font=ctk.CTkFont(size=13), text_color=COLOR_ACCENT,
        ).grid(row=2, column=0, pady=(0, 2))
        ctk.CTkLabel(
            self, text=f"Source : {repo_id}",
            font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED,
        ).grid(row=3, column=0, pady=(0, 14))

        # Barre de progression
        self._bar = ctk.CTkProgressBar(self, width=420)
        self._bar.set(0)
        self._bar.grid(row=4, column=0, padx=30, sticky="ew")

        # Ligne de progression principale (pourcentage + taille)
        self._lbl_pct = ctk.CTkLabel(
            self, text="Connexion au serveur…",
            font=ctk.CTkFont(size=12),
        )
        self._lbl_pct.grid(row=5, column=0, pady=(8, 2))

        # Fichier en cours
        self._lbl_file = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED,
            wraplength=440,
        )
        self._lbl_file.grid(row=6, column=0)

        ctk.CTkLabel(
            self,
            text="La transcription démarrera automatiquement.",
            font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED,
        ).grid(row=7, column=0, pady=(12, 0))

        ctk.CTkButton(
            self, text="Annuler",
            fg_color="transparent", border_width=1, border_color="gray",
            width=100, height=32,
            command=self._on_close,
        ).grid(row=8, column=0, pady=(10, 20))

    # ── Téléchargement ─────────────────────────────────────────────────────────

    def _start_download(self):
        download_model(
            self._model_name,
            on_progress = self._on_progress,
            on_done     = self._on_done,
            on_error    = self._on_error,
        )

    def _on_progress(self, bytes_done: int, bytes_total: int, filename: str):
        """Appelé depuis le thread de téléchargement — planifié sur le thread UI."""
        def _update():
            if self._cancelled:
                return
            ratio = bytes_done / bytes_total if bytes_total else 0
            self._bar.set(ratio)
            pct  = int(ratio * 100)
            done = _fmt_bytes(bytes_done)
            total = _fmt_bytes(bytes_total)
            self._lbl_pct.configure(text=f"{pct} %   —   {done} / {total}")
            # Nom de fichier court (retire le chemin éventuel)
            short = filename.split("/")[-1].strip() if filename else ""
            self._lbl_file.configure(text=f"↓  {short}" if short else "")
        try:
            self.after(0, _update)
        except Exception:
            pass

    def _on_done(self):
        def _finish():
            if self._cancelled:
                return
            self._bar.set(1.0)
            self._lbl_pct.configure(text="✅  Téléchargement terminé !")
            self._lbl_file.configure(text="Lancement de la transcription…")
            self.after(800, self._close_and_ready)
        try:
            self.after(0, _finish)
        except Exception:
            pass

    def _on_error(self, message: str):
        def _show():
            self._bar.set(0)
            self._lbl_pct.configure(
                text=f"❌  Erreur : {message}", text_color=COLOR_ERROR
            )
            self._lbl_file.configure(text="Vérifiez votre connexion Internet.")
        try:
            self.after(0, _show)
        except Exception:
            pass

    def _close_and_ready(self):
        self.destroy()
        if self._on_ready:
            self._on_ready()

    def _on_close(self):
        self._cancelled = True
        self.destroy()
        if self._on_cancel:
            self._on_cancel()
