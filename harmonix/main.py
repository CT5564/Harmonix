import argparse
import asyncio

from harmonix.brain.agent import Agent
from harmonix.proactive.scheduler import ProactiveScheduler
from harmonix.service.log import get_log
from harmonix.service.tray import Tray
from harmonix.tools.registry import register_all
from harmonix.voice import stt, tts
from harmonix.voice.audio import record_until_silence
from harmonix.voice.wakeword import wait_for_wakeword

log = get_log(__name__)

MUTE_STATE = {"muted": False}


def _set_mute(muted: bool) -> None:
    MUTE_STATE["muted"] = muted


async def run_once(agent: Agent) -> None:
    """Single wake-word interaction: listen, think, speak."""
    command = await wait_for_wakeword(timeout=300)
    if command is None:
        log.info("Wake word timeout.")
        return

    if command == "":
        log.info("User said stop listening.")
        return

    log.info("Command: %s", command)

    full = command
    if len(command) < 3:
        ok, audio = await asyncio.to_thread(record_until_silence)
        if ok:
            spoken = await stt.transcribe(audio)
            full = f"{command} {spoken}".strip()
            log.info("Full utterance: %s", full)

    response = await agent.run(full)
    log.info("Response: %s", response)

    if response.strip() and not MUTE_STATE["muted"]:
        await tts.speak(response)


async def run_text_mode(agent: Agent) -> None:
    """Interactive text REPL for testing without a mic."""
    log.info("Text mode. Type commands (blank line to exit).")
    print("Harmonix text mode — type a command, or press Enter to exit.")
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            break
        response = await agent.run(line)
        print(f"Harmonix> {response}")


async def shutdown() -> None:
    for task in asyncio.all_tasks():
        if task is not asyncio.current_task():
            task.cancel()
    await asyncio.sleep(0.1)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Harmonix 2.0")
    parser.add_argument("--text", action="store_true", help="Text mode (no mic)")
    args = parser.parse_args()

    agent = Agent()
    register_all(agent)

    if args.text:
        await run_text_mode(agent)
        return

    loop = asyncio.get_running_loop()
    scheduler = ProactiveScheduler()
    scheduler.start()

    tray = Tray(loop, _set_mute, shutdown)
    try:
        tray.start()
    except Exception as e:
        log.warning("Tray failed to start: %s", e)

    log.info("Harmonix online. Say '%s' to wake me.", "harmonix")

    try:
        while True:
            await run_once(agent)
    except asyncio.CancelledError:
        pass
    finally:
        await scheduler.stop()


def cli() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    cli()
