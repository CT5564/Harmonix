import harmonix.config as config
from harmonix.brain import llm
from harmonix.brain.persona import system_prompt
from harmonix.service.log import get_log

log = get_log(__name__)

MAX_HISTORY = 20


class Agent:
    """Conversation agent: maintains context and runs the LLM loop."""

    def __init__(self):
        self.history: list[dict] = []
        self.tools: list = []
        self.tool_handlers: dict[str, callable] = {}

    def register_tool(self, name: str, schema: dict, handler: callable) -> None:
        self.tools.append(schema)
        self.tool_handlers[name] = handler

    def reset(self) -> None:
        self.history = []

    def _messages(self, user_input: str) -> list[dict]:
        messages = [{"role": "system", "content": system_prompt(with_tools=bool(self.tools))}]
        messages.extend(self.history[-MAX_HISTORY:])
        messages.append({"role": "user", "content": user_input})
        return messages

    async def run(self, user_input: str, model: str = config.OMNIROUTE_FAST_MODEL) -> str:
        """Run a full turn. Returns the assistant's text response."""
        messages = self._messages(user_input)
        response = await llm.chat(model, messages, tools=self.tools or None)

        message = response["message"]
        content = message.get("content") or ""
        tool_calls = message.get("tool_calls")

        self.history.append({"role": "user", "content": user_input})

        if tool_calls:
            self.history.append(message)
            content = await self._run_tool_calls(tool_calls, model)
        else:
            self.history.append({"role": "assistant", "content": content})

        return content

    async def _run_tool_calls(self, tool_calls: list, model: str) -> str:
        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            try:
                args = __import__("json").loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}

            handler = self.tool_handlers.get(name)
            if handler is None:
                result = f"Unknown tool: {name}"
            else:
                try:
                    result = await handler(**args) if __import__("asyncio").iscoroutinefunction(handler) else handler(**args)
                except Exception as e:
                    result = f"Tool error: {e}"

            self.history.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": str(result),
            })

        follow_up = await llm.chat(model, self.history)
        final = follow_up["message"].get("content") or ""
        self.history.append({"role": "assistant", "content": final})
        return final
