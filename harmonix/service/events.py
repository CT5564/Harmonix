import asyncio
from collections import deque
from datetime import datetime, timezone

from harmonix.service.log import get_log

log = get_log(__name__)


class EventBus:
    """Broadcasts Harmonix lifecycle events to subscribers (e.g. dashboard)."""

    def __init__(self, history_size: int = 200):
        self.state = "starting"
        self.state_extra: dict = {}
        self._history: deque[dict] = deque(maxlen=history_size)
        self._subscribers: set[asyncio.Queue] = set()

    def snapshot(self) -> dict:
        return {
            "type": "snapshot",
            "state": self.state,
            "state_extra": self.state_extra,
            "history": list(self._history),
        }

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    async def publish(self, event: dict) -> None:
        event = dict(event)
        event.setdefault("ts", datetime.now(timezone.utc).isoformat())
        self._history.append(event)
        dead = []
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    q.get_nowait()
                    q.put_nowait(event)
                except Exception:
                    pass
            except Exception:
                dead.append(q)
        for q in dead:
            self.unsubscribe(q)

    async def set_state(self, state: str, **extra) -> None:
        self.state = state
        self.state_extra = dict(extra)
        await self.publish({"type": "state", "state": state, **extra})

    def emit_text(self, role: str, content: str) -> None:
        asyncio.ensure_future(
            self.publish({"type": "text", "role": role, "content": content})
        )

    def emit_tool(self, name: str, args: dict, result: str) -> None:
        asyncio.ensure_future(
            self.publish({"type": "tool", "name": name, "args": args, "result": result[:200]})
        )


bus = EventBus()
