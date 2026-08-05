import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "harmonix.db"

_lock = threading.Lock()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init() -> None:
    with _lock, _conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS conversation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT NOT NULL,
                source TEXT,
                ts TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                due_ts TEXT NOT NULL,
                fired INTEGER NOT NULL DEFAULT 0,
                created_ts TEXT NOT NULL
            );
            """
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- conversation ---------------------------------------------------------


def add_message(role: str, content: str) -> None:
    _init()
    with _lock, _conn() as conn:
        conn.execute(
            "INSERT INTO conversation (ts, role, content) VALUES (?, ?, ?)",
            (now_iso(), role, content),
        )


def recent_messages(limit: int = 40) -> list[dict]:
    _init()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT role, content FROM conversation ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def clear_conversation() -> None:
    _init()
    with _lock, _conn() as conn:
        conn.execute("DELETE FROM conversation")


# --- facts -----------------------------------------------------------------


def set_fact(key: str, value: str, source: str = "") -> None:
    _init()
    with _lock, _conn() as conn:
        conn.execute(
            """INSERT INTO facts (key, value, source, ts) VALUES (?, ?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value, source=excluded.source, ts=excluded.ts""",
            (key, value, source, now_iso()),
        )


def get_fact(key: str) -> str | None:
    _init()
    with _conn() as conn:
        row = conn.execute("SELECT value FROM facts WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else None


def all_facts() -> list[dict]:
    _init()
    with _conn() as conn:
        rows = conn.execute("SELECT key, value, source, ts FROM facts").fetchall()
    return [dict(r) for r in rows]


def delete_fact(key: str) -> None:
    _init()
    with _lock, _conn() as conn:
        conn.execute("DELETE FROM facts WHERE key = ?", (key,))


# --- reminders ---------------------------------------------------------------


def add_reminder(message: str, due_ts: str) -> int:
    _init()
    with _lock, _conn() as conn:
        cur = conn.execute(
            "INSERT INTO reminders (message, due_ts, created_ts) VALUES (?, ?, ?)",
            (message, due_ts, now_iso()),
        )
        return cur.lastrowid


def due_reminders(now_ts: str) -> list[dict]:
    _init()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE fired = 0 AND due_ts <= ? ORDER BY due_ts",
            (now_ts,),
        ).fetchall()
    return [dict(r) for r in rows]


def mark_reminder_fired(reminder_id: int) -> None:
    _init()
    with _lock, _conn() as conn:
        conn.execute("UPDATE reminders SET fired = 1 WHERE id = ?", (reminder_id,))


def pending_reminders() -> list[dict]:
    _init()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM reminders WHERE fired = 0 ORDER BY due_ts"
        ).fetchall()
    return [dict(r) for r in rows]


# convenience for json persistence if needed
def facts_json() -> str:
    return json.dumps(all_facts())
