import os
import subprocess
from pathlib import Path

import harmonix.config as config
from harmonix.service.log import get_log

log = get_log(__name__)


def _scope_path(path: str) -> Path | None:
    """Resolve a path and ensure it's within an allowed directory."""
    p = Path(path).expanduser().resolve()
    allowed = [Path(d).expanduser().resolve() for d in config.ALLOWED_DIRS if d]
    if not allowed:
        return p
    for base in allowed:
        try:
            p.relative_to(base)
            return p
        except ValueError:
            continue
    return None


async def list_dir(path: str = ".") -> str:
    p = _scope_path(path)
    if p is None:
        return "That path is outside my allowed directories, sir."
    try:
        entries = sorted(os.listdir(p))
    except Exception as e:
        return f"Couldn't list {path}: {e}"
    lines = []
    for name in entries[:50]:
        full = p / name
        kind = "/" if full.is_dir() else ""
        lines.append(f"{name}{kind}")
    return "\n".join(lines) or "(empty directory)"


async def read_file(path: str, limit: int = 200) -> str:
    p = _scope_path(path)
    if p is None:
        return "That path is outside my allowed directories, sir."
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Couldn't read {path}: {e}"
    if len(text.splitlines()) > limit:
        text = "\n".join(text.splitlines()[:limit]) + f"\n... ({len(text.splitlines()) - limit} more lines)"
    return text


async def search_files(query: str, path: str = ".") -> str:
    """Search file contents with ripgrep (falls back to plain grep)."""
    p = _scope_path(path)
    if p is None:
        return "That path is outside my allowed directories, sir."
    try:
        result = subprocess.run(
            ["rg", "--no-heading", "-i", "--max-count", "3", "-l", query, str(p)],
            capture_output=True, text=True, timeout=20,
        )
        if result.returncode == 1:
            return "No matches found."
        matches = [l for l in result.stdout.splitlines() if l.strip()][:20]
        return "\n".join(matches) or "No matches found."
    except FileNotFoundError:
        try:
            result = subprocess.run(
                ["findstr", "/s", "/i", "/m", query, f"{p}\\*"],
                capture_output=True, text=True, timeout=20,
            )
            lines = [l for l in result.stdout.splitlines() if l.strip()][:20]
            return "\n".join(lines) or "No matches found."
        except Exception as e:
            return f"Search failed: {e}"
    except Exception as e:
        return f"Search failed: {e}"


async def write_file(path: str, content: str) -> str:
    p = _scope_path(path)
    if p is None:
        return "That path is outside my allowed directories, sir."
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} characters to {path}."
    except Exception as e:
        return f"Couldn't write {path}: {e}"


async def open_file(path: str) -> str:
    p = _scope_path(path)
    if p is None:
        return "That path is outside my allowed directories, sir."
    try:
        os.startfile(str(p))  # noqa: S606
        return f"Opened {path}."
    except Exception as e:
        return f"Couldn't open {path}: {e}"
