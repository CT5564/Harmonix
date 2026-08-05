from harmonix.brain.agent import Agent
from harmonix.proactive import reminders
from harmonix.tools import apps, browser, files, notion, system


def register_all(agent: Agent) -> None:
    agent.register_tool(
        "list_dir",
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List files in a directory on the user's computer.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "Directory path (default '.')"}},
                },
            },
        },
        files.list_dir,
    )
    agent.register_tool(
        "read_file",
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a text file from the user's computer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "limit": {"type": "integer", "description": "Max lines to read (default 200)"},
                    },
                    "required": ["path"],
                },
            },
        },
        files.read_file,
    )
    agent.register_tool(
        "search_files",
        {
            "type": "function",
            "function": {
                "name": "search_files",
                "description": "Search file contents for a keyword on the user's computer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "path": {"type": "string", "description": "Directory to search (default '.')"},
                    },
                    "required": ["query"],
                },
            },
        },
        files.search_files,
    )
    agent.register_tool(
        "write_file",
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write text content to a file on the user's computer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        files.write_file,
    )
    agent.register_tool(
        "open_file",
        {
            "type": "function",
            "function": {
                "name": "open_file",
                "description": "Open a file or folder with its default application.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        files.open_file,
    )
    agent.register_tool(
        "launch_app",
        {
            "type": "function",
            "function": {
                "name": "launch_app",
                "description": "Launch an application by name (chrome, spotify, vscode, etc.).",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
        },
        apps.launch_app,
    )
    agent.register_tool(
        "is_running",
        {
            "type": "function",
            "function": {
                "name": "is_running",
                "description": "Check whether an application is currently running.",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
        },
        apps.is_running,
    )
    agent.register_tool(
        "focus_window",
        {
            "type": "function",
            "function": {
                "name": "focus_window",
                "description": "Bring a running application's window to the foreground.",
                "parameters": {
                    "type": "object",
                    "properties": {"name": {"type": "string"}},
                    "required": ["name"],
                },
            },
        },
        apps.focus_window,
    )
    agent.register_tool(
        "get_time",
        {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "Get the current date and time.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        system.get_time,
    )
    agent.register_tool(
        "get_weather",
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather in Manila.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        system.get_weather,
    )
    agent.register_tool(
        "notify",
        {
            "type": "function",
            "function": {
                "name": "notify",
                "description": "Show a desktop notification to the user.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "message": {"type": "string"},
                    },
                    "required": ["title", "message"],
                },
            },
        },
        system.notify,
    )
    agent.register_tool(
        "navigate",
        {
            "type": "function",
            "function": {
                "name": "navigate",
                "description": "Navigate the user's Chrome browser to a URL.",
                "parameters": {
                    "type": "object",
                    "properties": {"url": {"type": "string"}},
                    "required": ["url"],
                },
            },
        },
        browser.navigate,
    )
    agent.register_tool(
        "read_page",
        {
            "type": "function",
            "function": {
                "name": "read_page",
                "description": "Read the visible text content of the current browser page.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        browser.read_page,
    )
    agent.register_tool(
        "current_page",
        {
            "type": "function",
            "function": {
                "name": "current_page",
                "description": "Get the title and URL of the current browser tab.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        browser.current_page,
    )
    agent.register_tool(
        "list_tasks",
        {
            "type": "function",
            "function": {
                "name": "list_tasks",
                "description": "List tasks from the user's Notion database.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        notion.list_tasks,
    )
    agent.register_tool(
        "create_task",
        {
            "type": "function",
            "function": {
                "name": "create_task",
                "description": "Create a task in the user's Notion database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "due_date": {"type": "string", "description": "ISO date YYYY-MM-DD (optional)"},
                    },
                    "required": ["title"],
                },
            },
        },
        notion.create_task,
    )
    agent.register_tool(
        "search_notion",
        {
            "type": "function",
            "function": {
                "name": "search_notion",
                "description": "Search the user's Notion workspace by keyword.",
                "parameters": {
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                    "required": ["keyword"],
                },
            },
        },
        notion.search_notion,
    )
    agent.register_tool(
        "add_reminder",
        {
            "type": "function",
            "function": {
                "name": "add_reminder",
                "description": "Set a reminder. When accepts 'HH:MM' (today, or tomorrow if passed), 'in 5 minutes', 'in 2 hours', or an ISO timestamp.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string"},
                        "when": {"type": "string"},
                    },
                    "required": ["message", "when"],
                },
            },
        },
        reminders.add_reminder,
    )
    agent.register_tool(
        "list_reminders",
        {
            "type": "function",
            "function": {
                "name": "list_reminders",
                "description": "List all pending reminders.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        reminders.list_reminders,
    )
