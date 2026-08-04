import asyncio

from harmonix.brain.agent import Agent
from harmonix.service.log import get_log
from harmonix.voice import stt, tts
from harmonix.voice.audio import record_until_silence
from harmonix.voice.wakeword import wait_for_wakeword

log = get_log(__name__)


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

    # If the command is short, record the full utterance (post-wakeword).
    full = command
    if len(command) < 3:
        ok, audio = await asyncio.to_thread(record_until_silence)
        if ok:
            spoken = await stt.transcribe(audio)
            full = f"{command} {spoken}".strip()
            log.info("Full utterance: %s", full)

    response = await agent.run(full)
    log.info("Response: %s", response)

    if response.strip():
        await tts.speak(response)


async def main() -> None:
    agent = Agent()
    log.info("Harmonix online. Say '%s' to wake me.", "harmonix")

    while True:
        try:
            await run_once(agent)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            log.error("Loop error: %s", e)
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
