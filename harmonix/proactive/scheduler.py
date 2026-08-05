import asyncio
from datetime import datetime, timedelta

import harmonix.config as config
from harmonix.memory import history as memory
from harmonix.proactive.briefing import build_briefing
from harmonix.service.log import get_log
from harmonix.voice import tts
from harmonix.voice.audio import rms, db_from_rms

log = get_log(__name__)

REMINDER_CHECK_SECONDS = 15
BRIEFING_HOUR = 7  # 7:00 AM local


def _now() -> datetime:
    return datetime.utcnow() + timedelta(hours=config.TZ_OFFSET_HOURS)


async def _speak(text: str) -> None:
    try:
        await tts.speak(text)
    except Exception as e:
        log.error("TTS failed: %s", e)


class ProactiveScheduler:
    """Background loop: fires due reminders and the morning briefing."""

    def __init__(self):
        self._stop = asyncio.Event()
        self._last_briefing_date: str | None = None
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _run(self) -> None:
        log.info("Proactive scheduler started (briefing at %02d:00).", BRIEFING_HOUR)
        while not self._stop.is_set():
            try:
                await self._check_reminders()
                await self._check_briefing()
            except Exception as e:
                log.error("Scheduler error: %s", e)
            await asyncio.wait_for(
                asyncio.shield(self._stop.wait()),
                timeout=REMINDER_CHECK_SECONDS,
            )

    async def _check_reminders(self) -> None:
        now = _now()
        for r in memory.due_reminders(now.isoformat()):
            log.info("Firing reminder: %s", r["message"])
            await _speak(f"Reminder, sir: {r['message']}")
            memory.mark_reminder_fired(r["id"])

    async def _check_briefing(self) -> None:
        now = _now()
        today = now.date().isoformat()
        if self._last_briefing_date == today:
            return
        # Only brief once we've passed the briefing hour.
        if now.hour >= BRIEFING_HOUR:
            self._last_briefing_date = today
            log.info("Delivering morning briefing.")
            briefing = await build_briefing()
            await _speak(briefing)
