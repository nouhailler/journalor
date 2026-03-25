"""Audio recording using sounddevice."""

import threading
import time
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd

from utils.constants import (
    SAMPLE_RATE, CHANNELS, CHUNK_DURATION,
    SILENCE_THRESHOLD, SILENCE_DURATION_DEFAULT, MAX_RECORDING_MINUTES,
)


class AudioRecorder:
    """Records audio from the default microphone to a WAV file."""

    def __init__(
        self,
        output_dir: Path,
        silence_threshold: float = SILENCE_THRESHOLD,
        silence_duration: float = SILENCE_DURATION_DEFAULT,
        max_minutes: int = MAX_RECORDING_MINUTES,
    ):
        self.output_dir = output_dir
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.max_seconds = max_minutes * 60

        self._frames: list[np.ndarray] = []
        self._recording = False
        self._paused = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_level: float = 0.0
        self._elapsed: float = 0.0
        self._output_path: Path | None = None

        # Callbacks
        self.on_level: callable = None       # called with float rms each chunk
        self.on_auto_stop: callable = None   # called when silence stops recording
        self.on_max_reached: callable = None # called when max duration reached

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def elapsed(self) -> float:
        return self._elapsed

    @property
    def current_level(self) -> float:
        return self._last_level

    def start(self) -> Path:
        """Start recording; returns the output WAV path."""
        if self._recording:
            return self._output_path
        self._frames = []
        self._stop_event.clear()
        self._paused = False
        self._elapsed = 0.0
        filename = f"audio_{int(time.time())}.wav"
        self._output_path = self.output_dir / filename
        self._recording = True
        self._thread = threading.Thread(target=self._record_loop, daemon=True)
        self._thread.start()
        return self._output_path

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def stop(self) -> Path | None:
        """Stop recording and save WAV file."""
        if not self._recording:
            return self._output_path
        self._stop_event.set()
        self._recording = False
        if self._thread:
            self._thread.join(timeout=5)
        self._save_wav()
        return self._output_path

    def _record_loop(self) -> None:
        chunk_size = int(SAMPLE_RATE * CHUNK_DURATION)
        silence_frames = 0
        silence_limit = self.silence_duration / CHUNK_DURATION

        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            blocksize=chunk_size,
        ) as stream:
            while not self._stop_event.is_set():
                if self._paused:
                    time.sleep(0.1)
                    continue

                data, _ = stream.read(chunk_size)
                rms = float(np.sqrt(np.mean(data ** 2)))
                self._last_level = rms

                if self.on_level:
                    self.on_level(rms)

                if not self._paused:
                    self._frames.append(data.copy())
                    self._elapsed += CHUNK_DURATION

                # Silence detection
                if rms < self.silence_threshold:
                    silence_frames += 1
                    if silence_frames >= silence_limit and self.silence_duration > 0:
                        self._recording = False
                        self._stop_event.set()
                        self._save_wav()
                        if self.on_auto_stop:
                            self.on_auto_stop()
                        return
                else:
                    silence_frames = 0

                # Max duration
                if self._elapsed >= self.max_seconds:
                    self._recording = False
                    self._stop_event.set()
                    self._save_wav()
                    if self.on_max_reached:
                        self.on_max_reached()
                    return

    def _save_wav(self) -> None:
        if not self._frames or not self._output_path:
            return
        audio = np.concatenate(self._frames, axis=0)
        audio_int16 = (audio * 32767).astype(np.int16)
        with wave.open(str(self._output_path), "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(audio_int16.tobytes())

    def get_duration(self) -> float:
        return self._elapsed
