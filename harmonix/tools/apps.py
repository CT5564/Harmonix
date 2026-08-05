import os
import subprocess

import psutil

from harmonix.service.log import get_log

log = get_log(__name__)

_APP_MAP = {
    "chrome": ["start", "chrome"],
    "firefox": ["start", "firefox"],
    "edge": ["start", "msedge"],
    "spotify": ["start", "spotify"],
    "notepad": ["notepad"],
    "calculator": ["calc"],
    "paint": ["mspaint"],
    "vscode": ["code"],
    "explorer": ["explorer"],
    "cmd": ["cmd"],
    "powershell": ["powershell"],
    "word": ["winword"],
    "excel": ["excel"],
}


async def launch_app(name: str) -> str:
    key = name.lower().strip()
    cmd = _APP_MAP.get(key, [key])
    try:
        if cmd[0] == "start":
            subprocess.Popen(cmd, shell=True)
        else:
            subprocess.Popen(cmd)
        return f"Launching {name}."
    except Exception as e:
        return f"Couldn't launch {name}: {e}"


async def list_running() -> str:
    seen = set()
    lines = []
    for proc in psutil.process_iter(["name"]):
        pname = proc.info.get("name")
        if pname and pname.lower().endswith(".exe"):
            pname = pname[:-4]
        if pname and pname not in seen:
            seen.add(pname)
            lines.append(pname)
    return "\n".join(sorted(lines)[:60])


async def is_running(name: str) -> str:
    key = name.lower()
    for proc in psutil.process_iter(["name"]):
        pname = (proc.info.get("name") or "").lower()
        if key in pname:
            return f"Yes, {name} is running."
    return f"No, {name} isn't running."


async def focus_window(name: str) -> str:
    """Bring a running app's window to the foreground."""
    import ctypes

    import psutil

    key = name.lower()
    target_pid = None
    for proc in psutil.process_iter(["name", "pid"]):
        if key in (proc.info.get("name") or "").lower():
            target_pid = proc.info["pid"]
            break

    if not target_pid:
        return f"{name} isn't running, so I can't focus it."

    hwnd = None
    from ctypes import wintypes

    user32 = ctypes.windll.user32

    def callback(h, _p):
        nonlocal hwnd
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
        if pid.value == target_pid and user32.IsWindowVisible(h):
            hwnd = h
            return False
        return True

    user32.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)(callback), 0)
    if hwnd:
        user32.ShowWindow(hwnd, 9)
        user32.SetForegroundWindow(hwnd)
        return f"Focused {name}."
    return f"Found {name} running but couldn't focus its window."
