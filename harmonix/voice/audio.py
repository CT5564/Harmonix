from threading import Lock

import numpy as np
import sounddevice as sd

import harmonix.config as config

SAMPLE_RATE = config.SAMPLE_RATE
CHANNELS = config.CHANNELS
DTYPE = config.DTYPE
BLOCK_SIZE = int(config.SAMPLE_RATE * 0.5)

_lock = Lock()


def rms(data: np.ndarray) -> float:
    return float(np.sqrt(np.mean(data.astype(np.float32) ** 2)))


def db_from_rms(rms_value: float) -> float:
    if rms_value <= 0:
        return -100.0
    return 20.0 * np.log10(rms_value / 32768.0)


def is_voiced(db: float) -> bool:
    return db >= config.SILENCE_DB


class VAD:
    """Energy-based voice activity detection over sounddevice blocks."""

    def __init__(
        self,
        silence_db: float = config.SILENCE_DB,
        silence_duration: float = config.SILENCE_DURATION,
        max_duration: float = config.MAX_RECORD_SECONDS,
    ):
        self.silence_db = silence_db
        self.silence_duration = silence_duration
        self.max_duration = max_duration
        self._frames: list[np.ndarray] = []
        self._silence_blocks = 0
        self._total_blocks = 0

    @property
    def silence_threshold_blocks(self) -> int:
        return max(1, int(self.silence_duration / (BLOCK_SIZE / SAMPLE_RATE)))

    @property
    def max_blocks(self) -> int:
        return max(1, int(self.max_duration / (BLOCK_SIZE / SAMPLE_RATE)))

    @property
    def total_blocks(self) -> int:
        return self._total_blocks

    def reset(self) -> None:
        self._frames = []
        self._silence_blocks = 0
        self._total_blocks = 0

    def push(self, block: np.ndarray) -> bool:
        """Feed one block. Returns True when recording should stop."""
        self._frames.append(block.copy())
        self._total_blocks += 1
        db = db_from_rms(rms(block))
        if db < self.silence_db:
            self._silence_blocks += 1
        else:
            self._silence_blocks = 0

        if self._silence_blocks >= self.silence_threshold_blocks and self._total_blocks > 1:
            return True
        if self._total_blocks >= self.max_blocks:
            return True
        return False

    def to_audio(self) -> np.ndarray:
        return np.concatenate(self._frames, axis=0) if self._frames else np.zeros(0)


def record_until_silence(
    vad: VAD | None = None,
    min_seconds: float = 0.2,
) -> tuple[bool, np.ndarray]:
    """Record from mic until silence or max duration.

    Returns (ok, int16 audio array). ok is False on error or too-short capture.
    """
    vad = vad or VAD()
    vad.reset()

    def callback(data, _frames, _time, status):
        if status:
            return
        vad.push(data)

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCK_SIZE,
            callback=callback,
        ):
            while True:
                sd.sleep(100)
                if vad._silence_blocks >= vad.silence_threshold_blocks and vad.total_blocks > 1:
                    break
                if vad.total_blocks >= vad.max_blocks:
                    break
    except Exception:
        return False, np.zeros(0)

    audio = vad.to_audio()
    if len(audio) < SAMPLE_RATE * min_seconds:
        return False, np.zeros(0)
    return True, audio


def wait_for_voice(
    vad: VAD | None = None,
    energy_hits: int = 3,
    timeout_seconds: float = 300.0,
) -> tuple[bool, VAD]:
    """Wait for sustained voice energy. Returns (detected, vad_with_frames)."""
    vad = vad or VAD()
    vad.reset()
    hits = 0
    deadline = __import__("time").monotonic() + timeout_seconds

    def callback(data, _frames, _time, status):
        nonlocal hits
        if status:
            return
        db = db_from_rms(rms(data))
        hits = hits + 1 if db >= vad.silence_db else 0
        vad.push(data)

    try:
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=BLOCK_SIZE,
            callback=callback,
        ):
            while __import__("time").monotonic() < deadline:
                sd.sleep(100)
                if hits >= energy_hits:
                    return True, vad
    except Exception:
        return False, vad
    return False, vad
