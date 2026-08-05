from datetime import datetime, timedelta

import harmonix.config as config
from harmonix.memory import history as memory
from harmonix.service.log import get_log

log = get_log(__name__)


def _now() -> datetime:
    return datetime.utcnow() + timedelta(hours=config.TZ_OFFSET_HOURS)


def _parse_due(time_str: str) -> str:
    """Parse a natural time expression into an ISO timestamp.

    Accepts 'HH:MM', 'in 5 minutes', 'in 2 hours', 'in 1 day',
    or an ISO datetime.
    """
    t = time_str.strip().lower()
    try:
        return datetime.fromisoformat(time_str).replace(microsecond=0).isoformat()
    except ValueError:
        pass

    try:
        hour, minute = t.split(":")
        due = _now().replace(hour=int(hour), minute=int(minute), second=0, microsecond=0)
        if due <= _now():
            due += timedelta(days=1)
        return due.isoformat()
    except ValueError:
        pass

    import re

    m = re.match(r"in (\d+)\s*(minute|min|hour|hr|day|second|sec)s?", t)
    if m:
        amount, unit = int(m.group(1)), m.group(2)
        delta = {
            "second": timedelta(seconds=amount),
            "sec": timedelta(seconds=amount),
            "minute": timedelta(minutes=amount),
            "min": timedelta(minutes=amount),
            "hour": timedelta(hours=amount),
            "hr": timedelta(hours=amount),
            "day": timedelta(days=amount),
        }[unit]
        return (_now() + delta).replace(microsecond=0).isoformat()

    return (_now() + timedelta(hours=1)).replace(microsecond=0).isoformat()


def add_reminder(message: str, when: str) -> str:
    due = _parse_due(when)
    rid = memory.add_reminder(message, due)
    log.info("Added reminder #%d: %s at %s", rid, message, due)
    return f"Reminder set: {message}. I'll remind you at {due}."


def list_reminders() -> str:
    reminders = memory.pending_reminders()
    if not reminders:
        return "You have no pending reminders, sir."
    lines = [f"- {r['message']} (due {r['due_ts']})" for r in reminders]
    return "\n".join(lines)
