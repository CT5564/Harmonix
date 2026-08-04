import asyncio
import time

import harmonix.config as config
from harmonix.service.log import get_log
from harmonix.voice.audio import wait_for_voice
from harmonix.voice.stt import transcribe

log = get_log(__name__)

WAKE_WORD = config.WAKE_WORD.lower()


async def wait_for_wakeword(timeout: float = 300.0) -> str | None:
    """Listen until the wake word is spoken.

    Returns the command text after the wake word, or "" for "stop listening",
    or None on timeout/error.
    """
    deadline = time.monotonic() + timeout
    log.info("Waiting for '%s'...", config.WAKE_WORD)

    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        detected, vad = await asyncio.to_thread(
            wait_for_voice, timeout_seconds=remaining
        )
        if not detected:
            return None

        audio = vad.to_audio()
        text = await transcribe(audio)
        if not text:
            continue

        lower = text.lower().strip()
        log.info("Heard: %r", text)

        if lower.startswith(WAKE_WORD):
            cmd = text[len(WAKE_WORD):].strip().lstrip(",.:;!?- ")
            return cmd or text

        if "stop listening" in lower:
            return ""

    return None
