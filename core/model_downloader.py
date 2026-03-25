"""Gestion du cache et téléchargement des modèles Whisper / Distil-Whisper."""

import time
import threading
import logging

log = logging.getLogger("journalor.downloader")

FASTER_WHISPER_REPOS: dict[str, str] = {
    "tiny":     "Systran/faster-whisper-tiny",
    "base":     "Systran/faster-whisper-base",
    "small":    "Systran/faster-whisper-small",
    "medium":   "Systran/faster-whisper-medium",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
}

# ── État global ───────────────────────────────────────────────────────────────
_state_lock = threading.Lock()
_active: dict[str, dict] = {}


def get_repo_id(model_name: str) -> str:
    return FASTER_WHISPER_REPOS.get(model_name, model_name)


def get_cache_path(model_name: str) -> str:
    """Retourne le chemin du cache HuggingFace pour ce modèle."""
    import os
    repo_id  = get_repo_id(model_name)
    cache    = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface/hub"))
    folder   = "models--" + repo_id.replace("/", "--")
    return os.path.join(cache, folder)


def is_model_cached(model_name: str) -> bool:
    """True si model.bin est présent dans le cache HuggingFace local."""
    try:
        from huggingface_hub import try_to_load_from_cache
        result = try_to_load_from_cache(get_repo_id(model_name), "model.bin")
        return result is not None
    except Exception:
        return False


def download_model(
    model_name:  str,
    on_progress: callable = None,
    # signature : on_progress(file_idx, file_total, filename,
    #                         bytes_done, bytes_total)
    on_done:     callable = None,
    on_error:    callable = None,
) -> threading.Event:
    """
    Lance le téléchargement dans un thread.
    Retourne un Event qu'on peut set() pour annuler entre deux fichiers.
    Si un DL est déjà en cours, les callbacks sont rattachés à celui-ci.
    """
    with _state_lock:
        if model_name in _active:
            log.info("DL déjà en cours pour %s — rattachement", model_name)
            threading.Thread(
                target=_wait_for_existing,
                args=(model_name, on_done, on_error),
                daemon=True,
            ).start()
            return _active[model_name]["cancel"]

        cancel = threading.Event()
        state  = {"done": threading.Event(), "error": None, "cancel": cancel}
        _active[model_name] = state

    threading.Thread(
        target=_run,
        args=(model_name, on_progress, on_done, on_error, state),
        daemon=True,
    ).start()
    return cancel


def _wait_for_existing(model_name, on_done, on_error):
    with _state_lock:
        state = _active.get(model_name)
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


def _run(model_name, on_progress, on_done, on_error, state):
    try:
        from huggingface_hub import HfApi, hf_hub_download

        repo_id = get_repo_id(model_name)
        log.info("Début téléchargement %s (%s)", model_name, repo_id)

        # Liste des fichiers (sans .gitattributes)
        api      = HfApi()
        siblings = api.model_info(repo_id).siblings or []
        files    = [
            {"name": s.rfilename, "size": s.size or 0}
            for s in siblings
            if not s.rfilename.startswith(".")
            and s.rfilename not in (".gitattributes",)
        ]
        total = len(files)

        for idx, f in enumerate(files):
            if state["cancel"].is_set():
                log.info("Téléchargement annulé : %s", model_name)
                state["error"] = "Annulé par l'utilisateur"
                state["done"].set()
                if on_error:
                    on_error("Annulé par l'utilisateur")
                return

            log.info("  [%d/%d] %s (%s)", idx + 1, total,
                     f["name"], fmt_bytes(f["size"]))

            # Notification début de fichier
            if on_progress:
                on_progress(idx, total, f["name"], 0, f["size"])

            # Téléchargement avec progression octet par octet (throttlée)
            _download_file(repo_id, f["name"], idx, total, on_progress, state)

        # Terminé
        if on_progress:
            on_progress(total, total, "", 0, 0)
        log.info("Téléchargement terminé : %s", model_name)
        state["error"] = None
        state["done"].set()
        if on_done:
            on_done()

    except Exception as exc:
        log.error("Erreur DL %s : %s", model_name, exc)
        state["error"] = str(exc)
        state["done"].set()
        if on_error:
            on_error(str(exc))
    finally:
        with _state_lock:
            _active.pop(model_name, None)


def _download_file(repo_id, filename, idx, total, on_progress, state):
    """
    Télécharge un fichier unique avec un monkey-patch tqdm throttlé :
    au maximum 2 appels on_progress par seconde pour ne pas saturer tkinter.
    """
    import tqdm.auto as _tqdm_mod
    from huggingface_hub import hf_hub_download

    original_tqdm = _tqdm_mod.tqdm
    last_t        = [0.0]

    cb = {"fn": on_progress}  # cellule mutable pour la closure

    class _ThrottledTqdm(original_tqdm):
        def update(self, n=1):
            super().update(n)
            fn = cb.get("fn")
            if fn is None:
                return
            now = time.monotonic()
            if now - last_t[0] >= 0.5:          # max 2 updates/sec
                last_t[0] = now
                b_done  = int(self.n)
                b_total = int(self.total) if self.total else 0
                try:
                    fn(idx, total, filename, b_done, b_total)
                except Exception:
                    pass

    _tqdm_mod.tqdm = _ThrottledTqdm
    try:
        hf_hub_download(repo_id=repo_id, filename=filename)
    finally:
        _tqdm_mod.tqdm = original_tqdm
        cb["fn"] = None   # évite tout appel résiduel après restauration


def fmt_bytes(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n/1e9:.1f} Go"
    if n >= 1_000_000:
        return f"{n/1e6:.0f} Mo"
    if n >= 1_000:
        return f"{n/1e3:.0f} Ko"
    return f"{n} o" if n else "?"
