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

WATCHDOG_TIMEOUT = 45   # secondes sans progression → affiche l'aide manuelle


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
        self.after(5000, self._watchdog_tick)

    # ── Interface principale ───────────────────────────────────────────────────

    def _build_ui(self):
        info    = MODEL_CATALOG.get(self._model_name, {})
        display = info.get("display", self._model_name)
        repo_id = get_repo_id(self._model_name)

        self.title("Téléchargement du modèle")
        self.geometry("540x320")
        self.minsize(540, 320)
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._do_cancel)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Conteneur scrollable — tout le contenu y vit
        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self._scroll.grid_columnconfigure(0, weight=1)

        s = self._scroll   # raccourci

        ctk.CTkLabel(s, text="⬇️",
                     font=ctk.CTkFont(size=40)).grid(row=0, column=0, pady=(20, 2))
        ctk.CTkLabel(s, text="Téléchargement du modèle",
                     font=ctk.CTkFont(size=16, weight="bold")).grid(row=1, column=0)
        ctk.CTkLabel(s, text=display,
                     font=ctk.CTkFont(size=13), text_color=COLOR_ACCENT
                     ).grid(row=2, column=0, pady=(0, 2))
        ctk.CTkLabel(s, text=f"Source : {repo_id}",
                     font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED
                     ).grid(row=3, column=0, pady=(0, 12))

        self._bar = ctk.CTkProgressBar(s)
        self._bar.set(0)
        self._bar.grid(row=4, column=0, padx=24, sticky="ew")

        self._lbl_main = ctk.CTkLabel(
            s, text="Connexion au serveur…",
            font=ctk.CTkFont(size=12))
        self._lbl_main.grid(row=5, column=0, pady=(8, 2))

        self._lbl_file = ctk.CTkLabel(
            s, text="",
            font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED, wraplength=500)
        self._lbl_file.grid(row=6, column=0)

        ctk.CTkLabel(
            s,
            text="La transcription démarrera automatiquement à la fin.",
            font=ctk.CTkFont(size=10), text_color=COLOR_TEXT_MUTED,
        ).grid(row=7, column=0, pady=(10, 0))

        self._cancel_btn = ctk.CTkButton(
            s, text="Annuler",
            fg_color="transparent", border_width=1, border_color="gray",
            width=100, height=32, command=self._do_cancel)
        self._cancel_btn.grid(row=8, column=0, pady=(8, 16))

        # Zone d'aide (cachée par défaut, révélée par le watchdog)
        self._help_row = 9

    # ── Panneau d'aide manuelle ────────────────────────────────────────────────

    def _build_help_panel(self):
        repo_id    = get_repo_id(self._model_name)
        cache_path = get_cache_path(self._model_name)
        info       = MODEL_CATALOG.get(self._model_name, {})
        display    = info.get("display", self._model_name)
        ram        = info.get("ram", "?")

        s = self._scroll

        # Séparateur
        ctk.CTkFrame(s, height=1, fg_color="#333355"
                     ).grid(row=self._help_row, column=0,
                             sticky="ew", padx=16, pady=(4, 12))

        # Cadre principal de l'aide
        card = ctk.CTkFrame(s, fg_color="#1a1000", corner_radius=10)
        card.grid(row=self._help_row + 1, column=0,
                  sticky="ew", padx=16, pady=(0, 8))
        card.grid_columnconfigure(0, weight=1)

        def lbl(parent, text, row, **kw):
            ctk.CTkLabel(parent, text=text, anchor="w",
                         wraplength=470, justify="left", **kw
                         ).grid(row=row, column=0, sticky="w",
                                padx=16, pady=kw.pop("pady", 2))

        # Titre
        lbl(card,
            "⚠️  Le téléchargement semble bloqué ou très lent",
            row=0,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLOR_WARNING,
            pady=(14, 6))

        lbl(card,
            f"Le modèle {display} pèse environ {ram} et peut prendre "
            "plusieurs minutes selon votre connexion. "
            "Si le téléchargement ne progresse plus, vous pouvez le faire "
            "manuellement depuis un terminal en 3 étapes :",
            row=1,
            font=ctk.CTkFont(size=11),
            pady=(0, 10))

        # ── Étape 1 ──────────────────────────────────────────────────────────
        self._step_label(card, 2,
            "Étape 1",
            "Ouvrir un terminal (Ctrl+Alt+T sous Debian/Ubuntu)")

        # ── Étape 2 ──────────────────────────────────────────────────────────
        self._step_label(card, 3,
            "Étape 2  (si huggingface-cli n'est pas installé)",
            "Installer l'outil de téléchargement HuggingFace :")
        self._cmd_box(card, 4, "pip install huggingface_hub")

        # ── Étape 3 ──────────────────────────────────────────────────────────
        self._step_label(card, 5,
            "Étape 3",
            "Lancer le téléchargement du modèle :")
        self._cmd_box(card, 6, f"huggingface-cli download {repo_id}")

        lbl(card,
            "→  Cette commande télécharge automatiquement tous les fichiers "
            f"du modèle dans le dossier cache HuggingFace de votre machine :\n"
            f"   {cache_path}",
            row=7,
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
            pady=(2, 8))

        # ── Étape 4 ──────────────────────────────────────────────────────────
        self._step_label(card, 8,
            "Étape 4",
            "Revenir dans Journalor et relancer l'enregistrement :")

        lbl(card,
            "→  Journalor détectera automatiquement le modèle dans le cache "
            "et lancera la transcription sans aucun nouveau téléchargement.",
            row=9,
            font=ctk.CTkFont(size=11),
            text_color=COLOR_TEXT_MUTED,
            pady=(2, 8))

        # ── Conseil alternatif ────────────────────────────────────────────────
        ctk.CTkFrame(card, height=1, fg_color="#333322"
                     ).grid(row=10, column=0, sticky="ew", padx=12, pady=(4, 8))

        lbl(card,
            "💡  Conseil : si le téléchargement est systématiquement lent, "
            "choisissez un modèle plus léger dans ⚙️ Paramètres — "
            "le modèle Distil-Large-v3 (1.5 Go) offre une qualité comparable "
            "au Large-v2 pour un poids 3× inférieur.",
            row=11,
            font=ctk.CTkFont(size=11),
            text_color="#cccc88",
            pady=(0, 14))

    def _step_label(self, parent, row, title, body):
        ctk.CTkLabel(
            parent,
            text=f"📌 {title}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=COLOR_ACCENT,
            anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=16, pady=(8, 0))
        ctk.CTkLabel(
            parent, text=f"    {body}",
            font=ctk.CTkFont(size=11), anchor="w", wraplength=460,
        ).grid(row=row, column=0, sticky="w", padx=16, pady=(20, 0))
        # On surcharge la ligne du titre avec un frame 2-lignes
        # En pratique, on place titre et corps dans un sous-frame
        for w in parent.grid_slaves(row=row):
            w.destroy()
        sub = ctk.CTkFrame(parent, fg_color="transparent")
        sub.grid(row=row, column=0, sticky="ew", padx=16, pady=(6, 0))
        sub.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(sub, text=f"📌  {title}",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_ACCENT, anchor="w"
                     ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(sub, text=body,
                     font=ctk.CTkFont(size=11), anchor="w",
                     wraplength=450, justify="left"
                     ).grid(row=1, column=0, sticky="w", padx=(16, 0))

    def _cmd_box(self, parent, row, cmd: str):
        """Boîte de code copiable."""
        box = ctk.CTkTextbox(
            parent, height=34,
            font=ctk.CTkFont(family="monospace", size=12),
            fg_color="#0a0a1a",
        )
        box.insert("1.0", cmd)
        box.configure(state="disabled")
        box.grid(row=row, column=0, sticky="ew", padx=16, pady=(3, 2))

    # ── Watchdog ───────────────────────────────────────────────────────────────

    def _watchdog_tick(self):
        if self._done or not self.winfo_exists():
            return
        if time.monotonic() - self._last_update >= WATCHDOG_TIMEOUT:
            self._show_help()
        else:
            self.after(5000, self._watchdog_tick)

    def _show_help(self):
        if not self.winfo_exists():
            return
        self._build_help_panel()
        # Agrandir la fenêtre pour que le contenu soit visible
        self.geometry("560x680")
        self.minsize(560, 400)
        # Continuer le watchdog au cas où ça reparte
        self.after(30000, self._watchdog_tick)

    # ── Callbacks depuis le thread ─────────────────────────────────────────────

    def _cb_progress(self, file_idx, file_total, filename, bytes_done, bytes_total):
        def _update():
            if not self.winfo_exists() or self._done:
                return
            self._last_update = time.monotonic()

            ratio = (bytes_done / bytes_total) if bytes_total else (
                     (file_idx / file_total) if file_total else 0)
            self._bar.set(max(0.0, min(1.0, ratio)))

            if bytes_total and bytes_total > 0:
                pct  = int(ratio * 100)
                self._lbl_main.configure(
                    text=f"Fichier {file_idx + 1} / {file_total}  —  "
                         f"{pct} %  ({fmt_bytes(bytes_done)} / {fmt_bytes(bytes_total)})"
                )
            elif file_total:
                pct = int((file_idx / file_total) * 100)
                self._lbl_main.configure(
                    text=f"Fichier {file_idx + 1} / {file_total}  —  {pct} %")
            else:
                self._lbl_main.configure(text="Téléchargement en cours…")

            short = filename.split("/")[-1] if filename else ""
            self._lbl_file.configure(text=f"↓  {short}" if short else "")
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
                text=f"❌  Erreur réseau : {msg}", text_color=COLOR_ERROR)
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
