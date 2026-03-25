"""Dialogue de téléchargement d'un modèle Whisper avec watchdog."""

import time
import customtkinter as ctk

from core.model_downloader import (
    download_model, is_model_cached, get_repo_id, get_cache_path, fmt_bytes
)
from utils.constants import (
    MODEL_CATALOG, COLOR_ACCENT, COLOR_SUCCESS, COLOR_ERROR,
    COLOR_TEXT_MUTED, COLOR_WARNING,
)

# Délai en secondes sans progression avant d'afficher l'aide manuelle
WATCHDOG_TIMEOUT = 45


class DownloadDialog(ctk.CTkToplevel):
    """
    Vérifie le cache, affiche la progression si besoin, puis appelle on_ready().
    Si déjà en cache → on_ready() immédiat, aucune fenêtre affichée.
    """

    def __init__(self, master, model_name: str,
                 on_ready: callable, on_cancel: callable = None):
        self._model_name  = model_name
        self._on_ready    = on_ready
        self._on_cancel   = on_cancel
        self._cancel_ev   = None
        self._last_update = time.monotonic()
        self._done        = False

        if is_model_cached(model_name):
            master.after(0, on_ready)
            return

        super().__init__(master)
        self._build_ui()
        self.after(200, self._safe_grab)
        self._cancel_ev = download_model(
            model_name,
            on_progress = self._cb_progress,
            on_done     = self._cb_done,
            on_error    = self._cb_error,
        )
        # Lancer le watchdog
        self.after(5000, self._watchdog_tick)

    # ── Construction ───────────────────────────────────────────────────────────

    def _build_ui(self):
        info    = MODEL_CATALOG.get(self._model_name, {})
        display = info.get("display", self._model_name)
        repo_id = get_repo_id(self._model_name)

        self.title("Téléchargement du modèle")
        self.geometry("520x340")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._do_cancel)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="⬇️",
                     font=ctk.CTkFont(size=40)).grid(row=0, column=0, pady=(20, 2))
        ctk.CTkLabel(self, text="Téléchargement du modèle",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=1, column=0)
        ctk.CTkLabel(self, text=display,
                     font=ctk.CTkFont(size=13), text_color=COLOR_ACCENT
                     ).grid(row=2, column=0, pady=(0, 2))
        ctk.CTkLabel(self, text=f"Source : {repo_id}",
                     font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED
                     ).grid(row=3, column=0, pady=(0, 10))

        self._bar = ctk.CTkProgressBar(self, width=460)
        self._bar.set(0)
        self._bar.grid(row=4, column=0, padx=24, sticky="ew")

        self._lbl_main = ctk.CTkLabel(
            self, text="Connexion au serveur…",
            font=ctk.CTkFont(size=12))
        self._lbl_main.grid(row=5, column=0, pady=(8, 2))

        self._lbl_file = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED, wraplength=480)
        self._lbl_file.grid(row=6, column=0)

        # Zone d'aide manuelle (cachée par défaut)
        self._help_frame = ctk.CTkFrame(self, fg_color="#1a0a00", corner_radius=8)
        # Ne pas grider ici — affiché par le watchdog si besoin

        ctk.CTkLabel(
            self,
            text="La transcription démarrera automatiquement.",
            font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED,
        ).grid(row=8, column=0, pady=(10, 0))

        self._cancel_btn = ctk.CTkButton(
            self, text="Annuler",
            fg_color="transparent", border_width=1, border_color="gray",
            width=100, height=32, command=self._do_cancel)
        self._cancel_btn.grid(row=9, column=0, pady=(8, 16))

    def _build_help_panel(self):
        """Panneau affiché quand le watchdog détecte un blocage."""
        f = self._help_frame
        for w in f.winfo_children():
            w.destroy()
        f.grid_columnconfigure(0, weight=1)

        repo_id    = get_repo_id(self._model_name)
        cache_path = get_cache_path(self._model_name)

        ctk.CTkLabel(
            f, text="⚠️  Le téléchargement semble bloqué",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLOR_WARNING,
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            f,
            text="Vous pouvez télécharger le modèle manuellement via le terminal :",
            font=ctk.CTkFont(size=11), anchor="w", wraplength=470,
        ).grid(row=1, column=0, sticky="w", padx=12)

        # Commande CLI copiable
        cmd = f"huggingface-cli download {repo_id}"
        cmd_box = ctk.CTkTextbox(f, height=32, font=ctk.CTkFont(family="monospace", size=11))
        cmd_box.insert("1.0", cmd)
        cmd_box.configure(state="disabled")
        cmd_box.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 4))

        ctk.CTkLabel(
            f,
            text=f"Cache local : {cache_path}",
            font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED,
            anchor="w", wraplength=470,
        ).grid(row=3, column=0, sticky="w", padx=12, pady=(0, 10))

    # ── Watchdog ───────────────────────────────────────────────────────────────

    def _watchdog_tick(self):
        """Vérifie toutes les 5 secondes si la progression avance."""
        if self._done or not self.winfo_exists():
            return
        elapsed = time.monotonic() - self._last_update
        if elapsed >= WATCHDOG_TIMEOUT:
            self._show_help()
        else:
            self.after(5000, self._watchdog_tick)

    def _show_help(self):
        """Affiche le panneau d'aide manuelle et agrandit la fenêtre."""
        if not self.winfo_exists():
            return
        self._build_help_panel()
        self._help_frame.grid(row=7, column=0, sticky="ew", padx=24, pady=(8, 0))
        self.geometry("520x480")

    # ── Callbacks depuis le thread ─────────────────────────────────────────────

    def _cb_progress(self, file_idx, file_total, filename, bytes_done, bytes_total):
        def _update():
            if not self.winfo_exists() or self._done:
                return
            self._last_update = time.monotonic()

            # Progression globale : basée sur les octets si connus, sinon fichiers
            if bytes_total and bytes_total > 0:
                ratio = bytes_done / bytes_total
            elif file_total:
                ratio = file_idx / file_total
            else:
                ratio = 0
            self._bar.set(max(0.0, min(1.0, ratio)))

            # Ligne principale
            if bytes_total and bytes_total > 0:
                pct  = int(ratio * 100)
                done = fmt_bytes(bytes_done)
                tot  = fmt_bytes(bytes_total)
                self._lbl_main.configure(
                    text=f"Fichier {file_idx + 1} / {file_total}  —  "
                         f"{pct} %  ({done} / {tot})"
                )
            elif file_total:
                pct = int((file_idx / file_total) * 100)
                self._lbl_main.configure(
                    text=f"Fichier {file_idx + 1} / {file_total}  —  {pct} %"
                )
            else:
                self._lbl_main.configure(text="Téléchargement en cours…")

            # Nom du fichier courant
            short = filename.split("/")[-1] if filename else ""
            self._lbl_file.configure(
                text=f"↓  {short}" if short else ""
            )
        try:
            self.after(0, _update)
        except Exception:
            pass

    def _cb_done(self):
        def _finish():
            if not self.winfo_exists():
                return
            self._done = True
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
            self._done = True
            self._bar.set(0)
            self._lbl_main.configure(
                text=f"❌  Erreur : {msg}", text_color=COLOR_ERROR)
            self._lbl_file.configure(text="")
            self._show_help()
        try:
            self.after(0, _show)
        except Exception:
            pass

    # ── Fermeture ──────────────────────────────────────────────────────────────

    def _safe_grab(self):
        try:
            if self.winfo_exists():
                self.grab_set()
        except Exception:
            pass

    def _close_ready(self):
        self._release_and_destroy()
        if self._on_ready:
            self._on_ready()

    def _do_cancel(self):
        if self._cancel_ev is not None:
            self._cancel_ev.set()
        self._release_and_destroy()
        if self._on_cancel:
            self._on_cancel()

    def _release_and_destroy(self):
        try:
            self.grab_release()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
