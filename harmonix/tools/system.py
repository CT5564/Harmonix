import asyncio
from datetime import datetime, timedelta

import httpx

import harmonix.config as config
from harmonix.service.log import get_log

log = get_log(__name__)


def _now() -> datetime:
    return datetime.utcnow() + timedelta(hours=config.TZ_OFFSET_HOURS)


async def get_time() -> str:
    now = _now()
    return now.strftime("%A, %B %d, %I:%M %p")


async def get_weather(lat: float = 14.5995, lon: float = 120.9842) -> str:
    import os

    key = os.getenv("OPENWEATHERMAP_API_KEY", "")
    if not key:
        return "I don't have a weather key configured."
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={"lat": lat, "lon": lon, "units": "metric", "appid": key},
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        log.error("Weather fetch failed: %s", e)
        return "I couldn't reach the weather service."

    temp = round(data["main"]["temp"])
    desc = data["weather"][0]["description"].capitalize()
    humidity = data["main"]["humidity"]
    return f"{desc}, {temp} degrees, humidity {humidity} percent"


def notify(title: str, message: str) -> str:
    """Show a Windows toast notification."""
    try:
        from plyer import notification

        notification.notify(title=title, message=message, timeout=5)
        return "Notification sent."
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
            return "Notification sent."
        except Exception:
            return "Couldn't show notification."
