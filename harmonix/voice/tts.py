import asyncio
import os
import tempfile
import urllib.request
from pathlib import Path
from threading import Lock

import numpy as np
import sounddevice as sd

import harmonix.config as config
from harmonix.service.log import get_log

log = get_log(__name__)

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
MODEL_DIR.mkdir(exist_ok=True)

ONNX_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
VOICES_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
ONNX_PATH = MODEL_DIR / "kokoro-v1.0.onnx"
VOICES_PATH = MODEL_DIR / "voices-v1.0.bin"

_tts = None
_tts_lock = Lock()
_load_lock = asyncio.Lock()


def _download(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    log.info("Downloading %s...", dest.name)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=dest.suffix, dir=MODEL_DIR)
    tmp.close()
    urllib.request.urlretrieve(url, tmp.name)  # noqa: S310
    os.replace(tmp.name, dest)
    log.info("Downloaded %s.", dest.name)


def _get_tts():
    global _tts
    with _tts_lock:
        if _tts is None:
            from kokoro_onnx import Kokoro

            _download(ONNX_URL, ONNX_PATH)
            _download(VOICES_URL, VOICES_PATH)
            log.info("Loading Kokoro TTS...")
            _tts = Kokoro(str(ONNX_PATH), str(VOICES_PATH))
            log.info("TTS loaded.")
        return _tts


def available_voices() -> list[str]:
    return list(_get_tts().get_voices())


async def synthesize(text: str, voice: str = config.TTS_VOICE, speed: float = 1.0):
    async with _load_lock:
        tts = await asyncio.to_thread(_get_tts)
    samples, sample_rate = await asyncio.to_thread(
        tts.create, text, voice=voice, speed=speed, lang="en-us"
    )
    return samples.astype(np.float32), sample_rate


async def speak(
    text: str,
    voice: str = config.TTS_VOICE,
    speed: float = 1.0,
) -> None:
    """Synthesize and play speech synchronously (blocking until done)."""
    samples, sample_rate = await synthesize(text, voice=voice, speed=speed)
    await asyncio.to_thread(sd.play, samples, sample_rate)
    await asyncio.to_thread(sd.wait)
