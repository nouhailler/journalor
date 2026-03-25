"""Gestion du cache et téléchargement des modèles Whisper / Distil-Whisper."""

import threading
from pathlib import Path

# Mapping noms courts faster-whisper → repo HuggingFace
FASTER_WHISPER_REPOS: dict[str, str] = {
    "tiny":     "Systran/faster-whisper-tiny",
    "base":     "Systran/faster-whisper-base",
    "small":    "Systran/faster-whisper-small",
    "medium":   "Systran/faster-whisper-medium",
    "large-v2": "Systran/faster-whisper-large-v2",
    "large-v3": "Systran/faster-whisper-large-v3",
    # distil-whisper : le nom est déjà un repo HF complet
}


def get_repo_id(model_name: str) -> str:
    """Résout un nom de modèle faster-whisper en identifiant de dépôt HuggingFace."""
    return FASTER_WHISPER_REPOS.get(model_name, model_name)


def is_model_cached(model_name: str) -> bool:
    """Retourne True si le fichier model.bin est présent dans le cache HF local."""
    try:
        from huggingface_hub import try_to_load_from_cache
        repo_id = get_repo_id(model_name)
        result = try_to_load_from_cache(repo_id, "model.bin")
        return result is not None
    except Exception:
        return False


def download_model(
    model_name: str,
    on_start:    callable = None,   # (total_files: int)
    on_progress: callable = None,   # (done: int, total: int, filename: str)
    on_done:     callable = None,   # ()
    on_error:    callable = None,   # (message: str)
) -> threading.Thread:
    """Télécharge tous les fichiers du modèle dans le cache HF, dans un thread."""

    def _run():
        try:
            from huggingface_hub import HfApi, hf_hub_download

            repo_id = get_repo_id(model_name)
            api = HfApi()

            # Liste des fichiers du dépôt
            files = [
                f for f in api.list_repo_files(repo_id)
                if not f.startswith(".") and not f.endswith(".gitattributes")
            ]
            total = len(files)

            if on_start:
                on_start(total)

            for i, filename in enumerate(files):
                if on_progress:
                    on_progress(i, total, filename)
                hf_hub_download(repo_id=repo_id, filename=filename)

            if on_progress:
                on_progress(total, total, "")
            if on_done:
                on_done()

        except Exception as exc:
            if on_error:
                on_error(str(exc))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t
