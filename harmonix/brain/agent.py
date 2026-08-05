import json

import harmonix.config as config
from harmonix.brain import llm
from harmonix.brain.persona import system_prompt
from harmonix.memory import history as memory
from harmonix.service.log import get_log

log = get_log(__name__)

MAX_HISTORY = 20


class Agent:
    """Conversation agent: memory-backed, tool-capable LLM loop."""

    def __init__(self, persist: bool = True):
        self.persist = persist
        self.history: list[dict] = []
        self.tools: list = []
        self.tool_handlers: dict[str, callable] = {}
        self._load_history()

    def register_tool(self, name: str, schema: dict, handler: callable) -> None:
        self.tools.append(schema)
        self.tool_handlers[name] = handler

    def reset(self) -> None:
        self.history = []
        if self.persist:
            memory.clear_conversation()

    def _load_history(self) -> None:
        if self.persist:
            self.history = memory.recent_messages(MAX_HISTORY)

    def _messages(self, user_input: str) -> list[dict]:
        facts = memory.all_facts()
        prompt = system_prompt(with_tools=bool(self.tools))
        if facts:
            prompt += (
                "\n\nKnown facts about the user (from memory):\n"
                + "\n".join(f"- {f['key']}: {f['value']}" for f in facts)
            )
        messages = [{"role": "system", "content": prompt}]
        messages.extend(self.history[-MAX_HISTORY:])
        messages.append({"role": "user", "content": user_input})
        return messages

    async def run(self, user_input: str, model: str = config.OMNIROUTE_FAST_MODEL) -> str:
        messages = self._messages(user_input)
        response = await llm.chat(model, messages, tools=self.tools or None)

        message = response["message"]
        content = message.get("content") or ""
        tool_calls = message.get("tool_calls")

        self._remember(user_input)

        if tool_calls:
            self.history.append(message)
            content = await self._run_tool_calls(tool_calls, model)
        else:
            self.history.append({"role": "assistant", "content": content})

        self._remember(content, role="assistant")
        self._extract_facts(user_input, content)
        return content

    async def _run_tool_calls(self, tool_calls: list, model: str) -> str:
        for tc in tool_calls:
            fn = tc.get("function", {})
            name = fn.get("name", "")
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}

            handler = self.tool_handlers.get(name)
            if handler is None:
                result = f"Unknown tool: {name}"
            else:
                try:
                    import asyncio

                    result = (
                        await handler(**args)
                        if asyncio.iscoroutinefunction(handler)
                        else handler(**args)
                    )
                except Exception as e:
                    result = f"Tool error: {e}"

            self.history.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.get("id", ""),
                    "content": str(result),
                }
            )

        follow_up = await llm.chat(model, self.history)
        final = follow_up["message"].get("content") or ""
        self.history.append({"role": "assistant", "content": final})
        self._remember(final, role="assistant")
        return final

    def _remember(self, content: str, role: str = "user") -> None:
        if self.persist and content.strip():
            memory.add_message(role, content)

    def _extract_facts(self, user_input: str, reply: str) -> None:
        import re

        m = re.search(r"(?:remember that|remember|note that)\s+(.+?)[.!?]?$", user_input, re.IGNORECASE)
        if m:
            fact = m.group(1).strip()
            if fact:
                key = re.sub(r"[^a-z0-9]+", "_", fact.lower())[:64].strip("_") or "fact"
                memory.set_fact(key, fact, source="user")
                log.info("Stored fact: %s", fact)
