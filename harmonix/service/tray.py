import asyncio
import os
import threading
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from harmonix.service.log import get_log

log = get_log(__name__)


def _create_icon_image() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((8, 8, 56, 56), fill=(59, 130, 246, 255))
    d.ellipse((26, 20, 38, 32), fill=(255, 255, 255, 255))
    d.arc((20, 28, 44, 48), 200, 340, fill=(255, 255, 255, 255), width=4)
    return img


class Tray:
    """System tray icon: mute toggle, open logs, quit."""

    def __init__(self, loop: asyncio.AbstractEventLoop, on_mute: callable, on_quit):
        self._loop = loop
        self._on_mute = on_mute
        self._on_quit = on_quit
        self.muted = False
        self._icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None

    def _menu(self):
        return pystray.Menu(
            pystray.MenuItem(
                lambda item: "Unmute" if self.muted else "Mute",
                lambda _icon, _item: self._toggle_mute(),
                default=True,
            ),
            pystray.MenuItem("Open log file", lambda _i, _it: self._open_log()),
            pystray.MenuItem("Quit Harmonix", lambda _i, _it: self._quit()),
        )

    def _toggle_mute(self) -> None:
        self.muted = not self.muted
        self._on_mute(self.muted)
        log.info("Mute set to %s", self.muted)

    def _quit(self) -> None:
        log.info("Quit requested from tray.")
        asyncio.run_coroutine_threadsafe(self._on_quit(), self._loop)

    def _open_log(self) -> None:
        log_path = Path(__file__).resolve().parent.parent / "logs" / "harmonix.log"
        if log_path.exists():
            os.startfile(str(log_path))  # noqa: S606

    def start(self) -> None:
        def run():
            self._icon = pystray.Icon(
                "harmonix",
                _create_icon_image(),
                "Harmonix",
                self._menu(),
            )
            self._icon.run()

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
