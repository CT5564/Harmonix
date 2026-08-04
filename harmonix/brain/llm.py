import httpx

import harmonix.config as config
from harmonix.service.log import get_log

log = get_log(__name__)

SYSTEM_FALLBACK = {
    "model": "fallback",
    "message": {"role": "assistant", "content": "I'm sorry, sir. I can't reach my AI services right now."},
    "finish_reason": "stop",
}


async def _omniroute_chat(model: str, messages: list, tools: list | None) -> dict | None:
    headers = {"Content-Type": "application/json"}
    if config.OMNIROUTE_API_KEY:
        headers["Authorization"] = f"Bearer {config.OMNIROUTE_API_KEY}"

    body: dict = {"model": model, "messages": messages, "stream": False}
    if tools:
        body["tools"] = tools

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(config.OMNIROUTE_URL, headers=headers, json=body)
    except Exception as e:
        log.warning("OmniRoute unreachable: %s", e)
        return None

    if resp.status_code != 200:
        log.warning("OmniRoute HTTP %d: %s", resp.status_code, resp.text[:300])
        return None

    try:
        data = resp.json()
        choice = data["choices"][0]
        message = choice.get("message", {})
        tool_calls = message.get("tool_calls")
        return {
            "model": data.get("model", model),
            "message": {
                "role": "assistant",
                "content": message.get("content") or "",
                **({"tool_calls": tool_calls} if tool_calls else {}),
            },
            "finish_reason": choice.get("finish_reason", "stop"),
        }
    except Exception as e:
        log.warning("OmniRoute bad response: %s", e)
        return None


async def _ollama_chat(messages: list, tools: list | None) -> dict | None:
    """Local Ollama fallback. Doesn't support tool calls for small models."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{config.OLLAMA_URL}/api/chat",
                json={
                    "model": config.OLLAMA_MODEL,
                    "messages": messages,
                    "stream": False,
                },
            )
    except Exception as e:
        log.warning("Ollama unreachable: %s", e)
        return None

    if resp.status_code != 200:
        log.warning("Ollama HTTP %d", resp.status_code)
        return None

    data = resp.json()
    message = data.get("message", {})
    return {
        "model": data.get("model", config.OLLAMA_MODEL),
        "message": {
            "role": "assistant",
            "content": message.get("content", "") or "",
        },
        "finish_reason": "stop",
    }


async def chat(
    model: str,
    messages: list,
    tools: list | None = None,
    allow_ollama: bool = True,
) -> dict:
    """Call the LLM. Tries OmniRoute cloud, falls back to local Ollama."""
    result = await _omniroute_chat(model, messages, tools)
    if result is not None:
        return result

    if allow_ollama:
        result = await _ollama_chat(messages, tools)
        if result is not None:
            return result

    return SYSTEM_FALLBACK
