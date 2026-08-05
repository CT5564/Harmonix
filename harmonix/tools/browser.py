import json
import os
import subprocess
import urllib.parse
import urllib.request

import websocket

from harmonix.service.log import get_log

log = get_log(__name__)

CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"
PROFILE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "chrome-profile",
)


def _ensure_chrome() -> bool:
    """Ensure a controllable Chrome instance is running with remote debugging."""
    import time

    if _port_ready():
        return True

    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for path in chrome_paths:
        if os.path.exists(path):
            os.makedirs(PROFILE_DIR, exist_ok=True)
            subprocess.Popen(
                [
                    path,
                    f"--remote-debugging-port={CDP_PORT}",
                    f"--user-data-dir={PROFILE_DIR}",
                    "--no-first-run",
                    "--remote-allow-origins=*",
                ],
                creationflags=0x08000000,
            )
            break
    else:
        return False

    for _ in range(20):
        time.sleep(0.5)
        if _port_ready():
            return True
    return False


def _port_ready() -> bool:
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=2) as resp:
            resp.read()
            return True
    except Exception:
        return False


def _get_page() -> dict | None:
    with urllib.request.urlopen(f"{CDP_URL}/json", timeout=3) as resp:
        targets = json.loads(resp.read().decode())
    for t in targets:
        if t.get("type") == "page" and t.get("url") and t.get("url") != "chrome://newtab/":
            return t
    for t in targets:
        if t.get("type") == "page":
            return t
    return None


def _new_tab(url: str) -> dict | None:
    req = urllib.request.Request(
        f"{CDP_URL}/json/new?{urllib.parse.quote(url, safe='')}",
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())


def _cmd(ws, method: str, params: dict | None = None) -> dict:
    _cmd.counter = getattr(_cmd, "counter", 0) + 1
    msg_id = _cmd.counter
    ws.send(json.dumps({"id": msg_id, "method": method, "params": params or {}}))
    while True:
        msg = json.loads(ws.recv())
        if msg.get("id") == msg_id:
            return msg


def _connect() -> websocket.WebSocket | None:
    if not _ensure_chrome():
        return None
    page = _get_page()
    if page is None:
        page = _new_tab("about:blank")
    if page is None:
        return None
    ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=15)
    return ws


async def navigate(url: str) -> str:
    import time

    import urllib.parse

    if not url.startswith("http"):
        url = "https://" + url
    ws = _connect()
    if ws is None:
        return "I couldn't connect to Chrome, sir."
    try:
        _cmd(ws, "Page.navigate", {"url": url})
        _cmd(ws, "Page.enable")
        ws.close()
        time.sleep(2)
        return f"Navigated to {url}."
    except Exception as e:
        ws.close()
        return f"Browser error: {e}"


async def current_page() -> str:
    ws = _connect()
    if ws is None:
        return "I couldn't connect to Chrome, sir."
    try:
        title = _cmd(ws, "Runtime.evaluate", {"expression": "document.title"})
        url = _cmd(ws, "Runtime.evaluate", {"expression": "location.href"})
        ws.close()
        t = title.get("result", {}).get("result", {}).get("value", "")
        u = url.get("result", {}).get("result", {}).get("value", "")
        return f"Title: {t}\nURL: {u}"
    except Exception as e:
        ws.close()
        return f"Browser error: {e}"


async def read_page(max_chars: int = 3000) -> str:
    """Extract readable text from the current page."""
    ws = _connect()
    if ws is None:
        return "I couldn't connect to Chrome, sir."
    try:
        expr = (
            "(() => {"
            "  const sel = document.querySelector('article, main, body');"
            "  if (!sel) return '';"
            "  const clone = sel.cloneNode(true);"
            "  clone.querySelectorAll('script, style, noscript, nav, footer').forEach(el => el.remove());"
            "  return (clone.innerText || '').replace(/\\n{3,}/g, '\\n\\n').slice(0, 3000);"
            "})()"
        )
        result = _cmd(ws, "Runtime.evaluate", {"expression": expr, "returnByValue": True})
        ws.close()
        value = result.get("result", {}).get("result", {}).get("value", "")
        return value or "(no readable text on this page)"
    except Exception as e:
        ws.close()
        return f"Browser error: {e}"
