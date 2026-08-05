from datetime import datetime, timedelta

import harmonix.config as config
from harmonix.service.log import get_log
from harmonix.tools import notion, system

log = get_log(__name__)


def _now() -> datetime:
    return datetime.utcnow() + timedelta(hours=config.TZ_OFFSET_HOURS)


async def build_briefing() -> str:
    """Build a spoken morning briefing from Notion tasks + weather."""
    parts = ["Good morning, sir."]

    weather = await system.get_weather()
    if weather and "don't have a weather key" not in weather and "couldn't reach" not in weather:
        parts.append(f"Outside, {weather}.")

    try:
        tasks_text = await notion.list_tasks()
        if tasks_text and "don't have access" not in tasks_text:
            tasks = [t for t in tasks_text.splitlines() if t.strip()]
            if tasks:
                parts.append(
                    f"You have {len(tasks)} tasks in Notion. "
                    f"Here are the first few: {'. '.join(tasks[:3])}."
                )
            else:
                parts.append("Your task list is empty. All clear.")
        else:
            parts.append("I couldn't reach your Notion task list.")
    except Exception as e:
        log.error("Briefing task fetch failed: %s", e)
        parts.append("I had trouble reading your Notion tasks.")

    return " ".join(parts)
