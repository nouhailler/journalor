"""Gestion du cache et téléchargement des modèles Whisper / Distil-Whisper."""

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

# ── État global — empêche les téléchargements simultanés du même modèle ───────
_state_lock = threading.Lock()
_active: dict[str, dict] = {}
# Format : { model_name: { "done": Event, "error": str|None, "cancel": Event } }


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
    # signature : on_progress(file_idx, file_total, filename, file_bytes)
    on_done:     callable = None,
    on_error:    callable = None,
) -> threading.Event:
    """
    Télécharge le modèle dans le cache HF fichier par fichier.
    Retourne un threading.Event qu'on peut set() pour annuler entre deux fichiers.

    Si un téléchargement est déjà en cours pour ce modèle, les callbacks
    sont rattachés à celui-ci — aucun second thread n'est lancé.
    """
    with _state_lock:
        if model_name in _active:
            log.info("DL déjà en cours pour %s — rattachement", model_name)
            cancel = _active[model_name]["cancel"]
            # Lancer un thread d'attente léger
            threading.Thread(
                target=_wait_for_existing,
                args=(model_name, on_done, on_error),
                daemon=True,
            ).start()
            return cancel

        cancel = threading.Event()
        state  = {"done": threading.Event(), "error": None, "cancel": cancel}
        _active[model_name] = state

    t = threading.Thread(
        target=_run,
        args=(model_name, on_progress, on_done, on_error, state),
        daemon=True,
    )
    t.start()
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

        # Récupère la liste des fichiers avec leurs tailles
        api = HfApi()
        siblings = api.model_info(repo_id).siblings or []
        files = [
            {"name": s.rfilename, "size": s.size or 0}
            for s in siblings
            if not s.rfilename.startswith(".")
            and s.rfilename != ".gitattributes"
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

            if on_progress:
                on_progress(idx, total, f["name"], f["size"])

            log.info("  [%d/%d] %s (%s)", idx + 1, total, f["name"],
                     _fmt(f["size"]))
            hf_hub_download(repo_id=repo_id, filename=f["name"])

        if on_progress:
            on_progress(total, total, "", 0)

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


def _fmt(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n/1e9:.1f} Go"
    if n >= 1_000_000:
        return f"{n/1e6:.0f} Mo"
    if n >= 1_000:
        return f"{n/1e3:.0f} Ko"
    return f"{n} o"
