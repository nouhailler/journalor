"""Transcription using faster-whisper in a background thread."""

import threading
from pathlib import Path


class Transcriber:
    """Wraps faster-whisper for non-blocking transcription."""

    def __init__(self, model_name: str = "base", language: str = "fr"):
        self.model_name = model_name
        self.language = language
        self._model = None
        self._lock = threading.Lock()

    def _load_model(self):
        from faster_whisper import WhisperModel
        with self._lock:
            if self._model is None:
                self._model = WhisperModel(
                    self.model_name,
                    device="cpu",
                    compute_type="int8",
                )

    def transcribe(
        self,
        audio_path: Path,
        on_progress: callable = None,
        on_done: callable = None,
        on_error: callable = None,
    ) -> threading.Thread:
        """Start transcription in background thread."""
        def _run():
            try:
                self._load_model()
                lang = None if self.language == "auto" else self.language
                segments, info = self._model.transcribe(
                    str(audio_path),
                    language=lang,
                    beam_size=5,
                )
                text_parts = []
                for seg in segments:
                    text_parts.append(seg.text.strip())
                    if on_progress:
                        progress = min(seg.end / max(info.duration, 1), 1.0)
                        on_progress(progress)

                result = " ".join(text_parts).strip()
                if on_done:
                    on_done(result)
            except Exception as exc:
                if on_error:
                    on_error(str(exc))

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        return t

    def reload_model(self, model_name: str, language: str = "fr") -> None:
        with self._lock:
            self.model_name = model_name
            self.language = language
            self._model = None
