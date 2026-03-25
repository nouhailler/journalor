"""Dialogue de téléchargement d'un modèle Whisper."""

import customtkinter as ctk

from core.model_downloader import download_model, is_model_cached, get_repo_id, _fmt
from utils.constants import (
    MODEL_CATALOG, COLOR_ACCENT, COLOR_SUCCESS, COLOR_ERROR, COLOR_TEXT_MUTED
)


class DownloadDialog(ctk.CTkToplevel):
    """
    Vérifie le cache, affiche la progression si besoin, puis appelle on_ready().
    Si déjà en cache → on_ready() immédiat, aucune fenêtre affichée.
    """

    def __init__(self, master, model_name: str,
                 on_ready: callable, on_cancel: callable = None):
        self._model_name = model_name
        self._on_ready   = on_ready
        self._on_cancel  = on_cancel
        self._cancel_ev  = None

        if is_model_cached(model_name):
            master.after(0, on_ready)
            return

        super().__init__(master)
        self._build_ui()
        # grab_set différé — fenêtre pas encore visible au moment du __init__
        self.after(200, self._safe_grab)
        self._cancel_ev = download_model(
            model_name,
            on_progress = self._cb_progress,
            on_done     = self._cb_done,
            on_error    = self._cb_error,
        )

    # ── Interface ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        info    = MODEL_CATALOG.get(self._model_name, {})
        display = info.get("display", self._model_name)
        repo_id = get_repo_id(self._model_name)

        self.title("Téléchargement du modèle")
        self.geometry("500x310")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._do_cancel)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="⬇️",
                     font=ctk.CTkFont(size=40)).grid(row=0, column=0, pady=(24, 2))

        ctk.CTkLabel(self, text="Téléchargement du modèle",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=1, column=0)

        ctk.CTkLabel(self, text=display,
                     font=ctk.CTkFont(size=13),
                     text_color=COLOR_ACCENT).grid(row=2, column=0, pady=(0, 2))

        ctk.CTkLabel(self, text=f"Source : {repo_id}",
                     font=ctk.CTkFont(size=10),
                     text_color=COLOR_TEXT_MUTED).grid(row=3, column=0, pady=(0, 12))

        # Barre + labels
        self._bar = ctk.CTkProgressBar(self, width=420)
        self._bar.set(0)
        self._bar.grid(row=4, column=0, padx=30, sticky="ew")

        self._lbl_main = ctk.CTkLabel(
            self, text="Connexion au serveur…",
            font=ctk.CTkFont(size=12))
        self._lbl_main.grid(row=5, column=0, pady=(8, 2))

        self._lbl_file = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED,
            wraplength=440)
        self._lbl_file.grid(row=6, column=0)

        ctk.CTkLabel(
            self,
            text="La transcription démarrera automatiquement.",
            font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED,
        ).grid(row=7, column=0, pady=(10, 0))

        self._cancel_btn = ctk.CTkButton(
            self, text="Annuler",
            fg_color="transparent", border_width=1, border_color="gray",
            width=100, height=32,
            command=self._do_cancel)
        self._cancel_btn.grid(row=8, column=0, pady=(10, 18))

    def _safe_grab(self):
        """grab_set() seulement si la fenêtre existe encore."""
        try:
            if self.winfo_exists():
                self.grab_set()
        except Exception:
            pass

    # ── Callbacks depuis le thread de téléchargement ───────────────────────────

    def _cb_progress(self, idx: int, total: int, filename: str, file_bytes: int):
        """Appelé depuis le thread DL — planifie la mise à jour UI."""
        def _update():
            if not self.winfo_exists():
                return
            ratio = idx / total if total else 0
            self._bar.set(ratio)
            pct  = int(ratio * 100)
            size = f"  ({_fmt(file_bytes)})" if file_bytes > 0 else ""
            self._lbl_main.configure(
                text=f"Fichier {idx + 1} / {total}  —  {pct} %"
            )
            short = filename.split("/")[-1] if filename else ""
            self._lbl_file.configure(
                text=f"↓  {short}{size}" if short else ""
            )
        try:
            self.after(0, _update)
        except Exception:
            pass

    def _cb_done(self):
        def _finish():
            if not self.winfo_exists():
                return
            self._bar.set(1.0)
            self._lbl_main.configure(text="✅  Téléchargement terminé !")
            self._lbl_file.configure(text="Lancement de la transcription…")
            self._cancel_btn.configure(state="disabled")
            self.after(800, self._close_ready)
        try:
            self.after(0, _finish)
        except Exception:
            pass

    def _cb_error(self, msg: str):
        def _show():
            if not self.winfo_exists():
                return
            self._bar.set(0)
            self._lbl_main.configure(
                text=f"❌  Erreur : {msg}", text_color=COLOR_ERROR)
            self._lbl_file.configure(text="Vérifiez votre connexion Internet.")
        try:
            self.after(0, _show)
        except Exception:
            pass

    # ── Fermeture ──────────────────────────────────────────────────────────────

    def _close_ready(self):
        self._release_and_destroy()
        if self._on_ready:
            self._on_ready()

    def _do_cancel(self):
        # Signaler l'annulation au thread de téléchargement
        if self._cancel_ev is not None:
            self._cancel_ev.set()
        self._release_and_destroy()
        if self._on_cancel:
            self._on_cancel()

    def _release_and_destroy(self):
        """Libère le grab AVANT de détruire la fenêtre."""
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
