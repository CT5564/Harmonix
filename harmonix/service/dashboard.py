import asyncio

from aiohttp import web

import harmonix.config as config
from harmonix.service.events import bus
from harmonix.service.log import get_log

log = get_log(__name__)

DASHBOARD_PORT = int(config.DASHBOARD_PORT if hasattr(config, "DASHBOARD_PORT") else 8083)

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Harmonix</title>
<style>
  :root {
    --bg: #0b0e14;
    --panel: #12161f;
    --text: #dbe2ee;
    --muted: #7c8698;
    --accent: #3b82f6;
    --thinking: #a855f7;
    --listening: #3b82f6;
    --speaking: #22c55e;
    --loading: #f59e0b;
    --error: #ef4444;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: radial-gradient(1200px 600px at 50% -10%, #16203a 0%, var(--bg) 55%);
    color: var(--text);
    font-family: "Segoe UI", system-ui, sans-serif;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 32px 16px;
  }
  .indicator-wrap { display: flex; flex-direction: column; align-items: center; gap: 18px; margin-bottom: 28px; }
  .orb {
    width: 130px; height: 130px; border-radius: 50%;
    background: conic-gradient(var(--listening), #1d4ed8, var(--listening));
    position: relative;
    box-shadow: 0 0 60px color-mix(in srgb, var(--listening) 50%, transparent);
    animation: breathe 2.6s ease-in-out infinite;
  }
  .orb::after {
    content: "";
    position: absolute; inset: 10px;
    background: #10141d; border-radius: 50%;
  }
  .orb .label {
    position: absolute; inset: 0;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; font-size: 15px; letter-spacing: 0.5px;
    z-index: 2; color: var(--text);
  }
  .orb.thinking { --state: var(--thinking); background: conic-gradient(var(--thinking), #6d28d9, var(--thinking)); box-shadow: 0 0 60px color-mix(in srgb, var(--thinking) 50%, transparent); animation: spin 1.4s linear infinite; }
  .orb.thinking::before { content: ""; position: absolute; inset: -6px; border-radius: 50%; border: 2px solid transparent; border-top-color: var(--thinking); animation: spin 0.9s linear infinite; }
  .orb.speaking { --state: var(--speaking); background: conic-gradient(var(--speaking), #15803d, var(--speaking)); box-shadow: 0 0 60px color-mix(in srgb, var(--speaking) 50%, transparent); animation: pulse 0.9s ease-in-out infinite; }
  .orb.loading { --state: var(--loading); background: conic-gradient(var(--loading), #b45309, var(--loading)); box-shadow: 0 0 60px color-mix(in srgb, var(--loading) 50%, transparent); animation: breathe 1.4s ease-in-out infinite; }
  .orb.starting, .orb.idle { background: conic-gradient(var(--muted), #3a4252, var(--muted)); box-shadow: none; animation: breathe 3.5s ease-in-out infinite; }
  @keyframes breathe { 0%,100% { transform: scale(1); } 50% { transform: scale(1.06); } }
  @keyframes pulse { 0%,100% { transform: scale(1); } 50% { transform: scale(0.94); } }
  @keyframes spin { to { transform: rotate(360deg); } }
  .status {
    font-size: 17px; font-weight: 600; min-height: 26px; text-align: center;
    color: var(--text);
  }
  .status .sub { font-size: 13px; color: var(--muted); font-weight: 400; margin-top: 4px; }
  .dots::after { content: ""; animation: dots 1.2s steps(4,end) infinite; }
  @keyframes dots { 0% { content: ""; } 25% { content: "."; } 50% { content: ".."; } 75% { content: "..."; } }
  .meta { font-size: 12px; color: var(--muted); margin-bottom: 18px; }
  .meta a { color: var(--accent); text-decoration: none; }
  .log {
    width: min(760px, 100%);
    background: var(--panel); border: 1px solid #1e2635; border-radius: 14px;
    padding: 18px; height: 52vh; overflow-y: auto;
  }
  .msg { margin-bottom: 12px; }
  .msg .who { font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--muted); margin-bottom: 3px; }
  .msg.user .who { color: var(--accent); }
  .msg.assistant .who { color: var(--speaking); }
  .msg .body { font-size: 15px; line-height: 1.5; white-space: pre-wrap; }
  .msg.tool { opacity: 0.7; }
  .msg.tool .who { color: var(--thinking); }
  .msg.tool .body { font-family: Consolas, monospace; font-size: 12px; }
  .empty { color: var(--muted); text-align: center; padding: 30px; font-style: italic; }
  .conn { position: fixed; top: 14px; right: 14px; display: flex; align-items: center; gap: 7px; font-size: 12px; color: var(--muted); }
  .conn .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--error); }
  .conn.online .dot { background: var(--speaking); }
  ::-webkit-scrollbar { width: 8px; }
  ::-webkit-scrollbar-thumb { background: #232c3d; border-radius: 4px; }
</style>
</head>
<body>
  <div class="conn" id="conn"><span class="dot"></span><span id="connText">connecting</span></div>

  <div class="indicator-wrap">
    <div class="orb" id="orb"><div class="label">Harmonix</div></div>
    <div class="status" id="status">Starting<span class="dots"></span>
      <div class="sub" id="statusSub"></div>
    </div>
    <div class="meta">Live at <a href="#" id="url">this page</a> &middot; wake word &ldquo;harmonix&rdquo;</div>
  </div>

  <div class="log" id="log"><div class="empty">Waiting for Harmonix to speak...</div></div>

<script>
const stateLabels = {
  starting:  "Starting Harmonix",
  loading:   "Loading models",
  listening: "Listening for \u201Charmonix\u201D",
  thinking:  "Thinking",
  speaking:  "Speaking",
  idle:      "Listening",
};

let state = "starting";

function renderState(st, extra) {
  const orb = document.getElementById("orb");
  orb.className = "orb " + (st === "listening" ? "listening" : st);
  const subText = (st === "loading" && extra && extra.message) ? extra.message
                : (st === "speaking" ? "Responding..." : "");
  document.getElementById("status").innerHTML = (stateLabels[st] || st)
    + "<span class='dots'></span><div class='sub' id='statusSub'></div>";
  const sub = document.getElementById("statusSub");
  if (subText) sub.textContent = subText;
}

function appendMsg(role, content) {
  const log = document.getElementById("log");
  const empty = log.querySelector(".empty");
  if (empty) empty.remove();
  const div = document.createElement("div");
  div.className = "msg " + role;
  const who = role === "user" ? "You" : role === "assistant" ? "Harmonix" : "tool";
  div.innerHTML = "<div class='who'>" + who + "</div><div class='body'></div>";
  div.querySelector(".body").textContent = content;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function connect() {
  const ws = new WebSocket((location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws");
  ws.onopen = () => {
    document.getElementById("conn").classList.add("online");
    document.getElementById("connText").textContent = "live";
  };
  ws.onclose = () => {
    document.getElementById("conn").classList.remove("online");
    document.getElementById("connText").textContent = "reconnecting";
    setTimeout(connect, 1500);
  };
  ws.onerror = () => ws.close();
  ws.onmessage = (ev) => {
    const msg = JSON.parse(ev.data);
    if (msg.type === "snapshot") {
      state = msg.state;
      renderState(state, msg.state_extra);
      document.getElementById("log").innerHTML = "<div class='empty'>Waiting for Harmonix to speak...</div>";
      (msg.history || []).forEach(e => {
        if (e.type === "text") appendMsg(e.role, e.content);
        else if (e.type === "tool") appendMsg("tool", "→ " + e.name + " " + JSON.stringify(e.args || {}));
      });
    } else if (msg.type === "state") {
      state = msg.state;
      renderState(state, msg.state_extra);
    } else if (msg.type === "text") {
      appendMsg(msg.role, msg.content);
    } else if (msg.type === "tool") {
      appendMsg("tool", "→ " + msg.name + " " + JSON.stringify(msg.args || {}));
    }
  };
}

document.getElementById("url").textContent = location.href;
connect();
</script>
</body>
</html>
"""


async def _index(_request: web.Request) -> web.Response:
    return web.Response(text=HTML, content_type="text/html")


async def _ws(request: web.Request) -> web.WebSocketResponse:
    ws = web.WebSocketResponse(max_msg_size=65536)
    await ws.prepare(request)

    queue = bus.subscribe()
    await ws.send_json(bus.snapshot())

    async def pump():
        try:
            while True:
                event = await queue.get()
                await ws.send_json(event)
        except (asyncio.CancelledError, ConnectionResetError, RuntimeError):
            pass

    pump_task = asyncio.create_task(pump())
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.ERROR:
                break
    finally:
        pump_task.cancel()
        bus.unsubscribe(queue)
    return ws


class Dashboard:
    def __init__(self, port: int = DASHBOARD_PORT):
        self.port = port
        self._runner: web.AppRunner | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    async def start(self) -> None:
        app = web.Application()
        app.router.add_get("/", _index)
        app.router.add_get("/ws", _ws)
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "127.0.0.1", self.port)
        await site.start()
        log.info("Dashboard live at %s", self.url)

    async def stop(self) -> None:
        if self._runner:
            await self._runner.cleanup()
            self._runner = None
