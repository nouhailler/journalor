"""Audio utility functions."""

import wave
from pathlib import Path

import numpy as np


def wav_to_mp3(wav_path: Path, bitrate: int = 128) -> Path:
    """
    Convert a WAV file to MP3 using lameenc (pure Python, no ffmpeg needed).
    Returns the path of the created MP3 file.
    Raises RuntimeError if lameenc is not installed or conversion fails.
    """
    try:
        import lameenc
    except ImportError:
        raise RuntimeError(
            "lameenc n'est pas installé. Lancez : pip install lameenc"
        )

    mp3_path = wav_path.with_suffix(".mp3")

    with wave.open(str(wav_path), "rb") as wf:
        n_channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    data = np.frombuffer(raw, dtype=np.int16)

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(bitrate)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(n_channels)
    encoder.set_quality(2)  # 2 = haute qualité

    mp3_data = encoder.encode(data.tobytes())
    mp3_data += encoder.flush()
    mp3_path.write_bytes(mp3_data)
    return mp3_path
