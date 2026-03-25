"""Gestion du cache et téléchargement des modèles Whisper / Distil-Whisper."""

import threading
import logging

log = logging.getLogger("journalor.downloader")

# Mapping noms courts faster-whisper → repo HuggingFace
FASTER_WHISPER_REPOS: dict[str, str] = {
    "tiny":     "Systran/faster-whisper-tiny",
    "base":     "Systran/faster-whisper-base",
    "small":    "Systran/faster-whisper-small",
    "medium":   "Systran/faster-whisper-medium",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
    # distil-whisper : déjà un repo HF complet
}

# ── État global des téléchargements ──────────────────────────────────────────
# Empêche de lancer deux téléchargements simultanés pour le même modèle.
# Format : { model_name: { "done": Event, "error": str|None, "callbacks": [...] } }
_downloads: dict[str, dict] = {}
_lock = threading.Lock()


def get_repo_id(model_name: str) -> str:
    return FASTER_WHISPER_REPOS.get(model_name, model_name)


def is_model_cached(model_name: str) -> bool:
    """True si model.bin est présent dans le cache HuggingFace local."""
    try:
        from huggingface_hub import try_to_load_from_cache
        result = try_to_load_from_cache(get_repo_id(model_name), "model.bin")
        return result is not None
    except Exception:
        return False


def download_model(
    model_name: str,
    on_progress: callable = None,
    # signature : on_progress(bytes_done: int, bytes_total: int, filename: str)
    on_done:     callable = None,
    on_error:    callable = None,
) -> None:
    """
    Télécharge le modèle dans le cache HF avec progression octet par octet.
    Si un téléchargement est déjà en cours pour ce modèle, les callbacks
    sont enregistrés et appelés à la fin — sans lancer un second thread.
    """
    with _lock:
        if model_name in _downloads:
            # Déjà en cours : on s'accroche aux callbacks existants
            log.info("Téléchargement déjà en cours pour %s, en attente…", model_name)
            state = _downloads[model_name]
            if on_done:
                state["callbacks"].append(("done", on_done))
            if on_error:
                state["callbacks"].append(("error", on_error))
            # Lancer un thread d'attente pour appeler les callbacks au bon moment
            threading.Thread(
                target=_wait_and_notify,
                args=(model_name, on_progress, on_done, on_error),
                daemon=True,
            ).start()
            return

        # Premier appel : on crée l'état et on lance le thread
        state = {
            "done":      threading.Event(),
            "error":     None,
            "callbacks": [],
        }
        _downloads[model_name] = state

    thread = threading.Thread(
        target=_download_thread,
        args=(model_name, on_progress, on_done, on_error, state),
        daemon=True,
    )
    thread.start()


def _wait_and_notify(model_name, on_progress, on_done, on_error, state=None):
    """Attend la fin du téléchargement principal et notifie les callbacks secondaires."""
    if state is None:
        with _lock:
            state = _downloads.get(model_name)
    if state is None:
        if on_done:
            on_done()
        return
    state["done"].wait()
    if state["error"]:
        if on_error:
            on_error(state["error"])
    else:
        if on_done:
            on_done()


def _download_thread(model_name, on_progress, on_done, on_error, state):
    """Thread de téléchargement avec interception de tqdm pour la progression."""
    try:
        import tqdm.auto as tqdm_auto
        from huggingface_hub import snapshot_download

        original_tqdm = tqdm_auto.tqdm

        # ── Interception de tqdm ──────────────────────────────────────────────
        # On crée une sous-classe qui renvoie les événements d'avancement.
        # Utilise une cellule de capture pour éviter les problèmes de thread.
        _cb = {"fn": on_progress}

        class _Tqdm(original_tqdm):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def update(self, n=1):
                super().update(n)
                fn = _cb.get("fn")
                if fn and self.total and self.total > 0:
                    fn(int(self.n), int(self.total), str(self.desc or ""))

        tqdm_auto.tqdm = _Tqdm

        try:
            repo_id = get_repo_id(model_name)
            log.info("Début téléchargement %s (%s)", model_name, repo_id)
            snapshot_download(repo_id=repo_id, repo_type="model")
            log.info("Téléchargement terminé : %s", model_name)
        finally:
            # Toujours restaurer tqdm même si une exception survient
            tqdm_auto.tqdm = original_tqdm

        # Marquer comme terminé
        state["error"] = None
        state["done"].set()
        if on_done:
            on_done()

    except Exception as exc:
        log.error("Erreur téléchargement %s : %s", model_name, exc)
        state["error"] = str(exc)
        state["done"].set()
        if on_error:
            on_error(str(exc))

    finally:
        # Nettoyer l'état global après la fin (succès ou erreur)
        with _lock:
            _downloads.pop(model_name, None)
