import asyncio
import os

from dotenv import load_dotenv
from notion_client import Client

import harmonix.config as config
from harmonix.service.log import get_log

load_dotenv(config.BASE_DIR / ".env")

log = get_log(__name__)

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
TASKS_DB_ID = config.NOTION_TASKS_DB_ID

_client: Client | None = None


def _get_client() -> Client | None:
    global _client
    if not NOTION_TOKEN:
        return None
    if _client is None:
        _client = Client(auth=NOTION_TOKEN)
    return _client


async def _resolve_data_source(database_id: str) -> str | None:
    client = _get_client()
    if client is None:
        return None
    db_info = await asyncio.to_thread(
        lambda: client.request(path=f"databases/{database_id}", method="GET")
    )
    sources = db_info.get("data_sources", [])
    if not sources:
        return None
    return sources[0].get("id")


async def query_tasks() -> list[dict]:
    """Query the Notion Tasks database, return raw page dicts."""
    client = _get_client()
    if client is None:
        return []
    ds_id = await _resolve_data_source(TASKS_DB_ID)
    if not ds_id:
        return []
    response = await asyncio.to_thread(
        lambda: client.request(path=f"data_sources/{ds_id}/query", method="POST", body={})
    )
    return response.get("results", [])


def _prop(props: dict, name: str):
    p = props.get(name)
    if not p:
        return None
    return p.get(p.get("type"))


def _text(value) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(item.get("plain_text", "") for item in value)
    if isinstance(value, dict):
        return value.get("name", "") or value.get("plain_text", "") or str(value.get("start", ""))
    return str(value)


async def list_tasks() -> str:
    """Return a spoken-friendly summary of all Notion tasks."""
    entries = await query_tasks()
    if not entries:
        return "I don't have access to Notion right now, sir."

    lines = []
    for entry in entries:
        props = entry.get("properties", {})
        title = _text(props.get("Assignment Name", {}).get("title"))
        status = _text(props.get("Status"))
        priority = _text(props.get("Priority"))
        due = _text(props.get("Due / When"))
        type_ = _text(props.get("Type"))
        parts = [title or "Untitled"]
        if status:
            parts.append(f"[{status}]")
        if due:
            parts.append(f"due {due[:10]}")
        if priority:
            parts.append(f"({priority})")
        if type_:
            parts.append(type_)
        lines.append(" - " + " ".join(parts))

    return "\n".join(lines) or "No tasks in Notion, sir."


async def create_task(title: str, due_date: str | None = None) -> str:
    """Create a task page in the Notion Tasks database."""
    client = _get_client()
    if client is None:
        return "Notion isn't configured, sir."
    props: dict = {
        "Assignment Name": {"title": [{"text": {"content": title}}]},
        "Status": {"status": {"name": "Not Started"}},
    }
    if due_date:
        props["Due / When"] = {"date": {"start": due_date}}

    try:
        response = await asyncio.to_thread(
            lambda: client.request(
                path="pages",
                method="POST",
                body={"parent": {"database_id": TASKS_DB_ID}, "properties": props},
            )
        )
        return f"Task created: {title}"
    except Exception as e:
        return f"Failed to create task: {e}"


async def search_notion(keyword: str) -> str:
    """Search Notion pages by keyword."""
    client = _get_client()
    if client is None:
        return "Notion isn't configured, sir."
    try:
        response = await asyncio.to_thread(
            lambda: client.search(query=keyword)
        )
    except Exception as e:
        return f"Search failed: {e}"

    results = response.get("results", [])
    if not results:
        return f"No Notion results for '{keyword}'."

    lines = []
    for item in results[:10]:
        if item.get("object") != "page":
            continue
        props = item.get("properties", {})
        title = ""
        for prop in props.values():
            if prop.get("type") == "title":
                title = _text(prop.get("title"))
                break
        lines.append(f" - {title or 'Untitled'}")

    return "\n".join(lines) or f"No pages found for '{keyword}'."
