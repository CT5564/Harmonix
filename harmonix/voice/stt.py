import asyncio
from threading import Lock

import numpy as np

import harmonix.config as config
from harmonix.service.log import get_log

log = get_log(__name__)

_model = None
_model_lock = Lock()
_load_lock = asyncio.Lock()


def _get_model():
    global _model
    with _model_lock:
        if _model is None:
            from faster_whisper import WhisperModel

            log.info("Loading faster-whisper model '%s'...", config.STT_MODEL)
            try:
                from harmonix.service.events import bus
                asyncio.ensure_future(
                    bus.set_state("loading", message=f"Loading speech model ({config.STT_MODEL})...")
                )
            except Exception:
                pass
            _model = WhisperModel(
                config.STT_MODEL,
                device=config.STT_DEVICE,
                compute_type=config.STT_COMPUTE_TYPE,
            )
            log.info("STT model loaded.")
        return _model


async def transcribe(audio: np.ndarray) -> str:
    """Transcribe int16 PCM audio to text with faster-whisper."""
    async with _load_lock:
        model = await asyncio.to_thread(_get_model)

    audio = np.asarray(audio)
    if audio.ndim == 2:
        audio = audio[:, 0]
    audio_f32 = audio.astype(np.float32) / 32768.0

    def run():
        segments, info = model.transcribe(
            audio_f32,
            beam_size=5,
            vad_filter=True,
            language=None,
        )
        parts = [s.text.strip() for s in segments]
        return " ".join(parts).strip()

    try:
        text = await asyncio.to_thread(run)
    except Exception as e:
        log.error("STT failed: %s", e)
        return ""
    return text
