# Harmonix 2.0

Your always-on, voice-first personal AI assistant. Say **"Harmonix, ..."** and
it listens, thinks, and speaks back — and can actually do things on your PC.

## Stack

- **Voice** — 100% local and free
  - Wake word: energy VAD + faster-whisper keyword check
  - STT: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) `small` (English + Filipino)
  - TTS: [Kokoro](https://github.com/thewh1teagle/kokoro-onnx) (natural local voice)
- **Brain** — hybrid
  - Cloud: OmniRoute (OpenAI-compatible), tool-calling capable
  - Fallback: local Ollama (qwen2.5:3b) when the cloud is unreachable
- **Memory** — local SQLite: conversation history, user facts, reminders
- **Tools** — files, app launch/focus, Chrome CDP, Notion tasks, weather, notifications
- **Proactive** — morning briefing, due reminders, nudges

## Setup

```powershell
scripts\setup.bat          # installs uv + Python 3.12 venv + deps
```

Copy `.env.example` to `.env` and fill in keys (OmniRoute, Notion, OpenWeatherMap).

## Run

```powershell
uv run python -m harmonix.main --text     # type commands (no mic needed)
uv run python -m harmonix.main            # voice mode: wake word + spoken replies
```

Auto-start at logon:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-startup.ps1
```

## Layout

```
harmonix/
  main.py            entry point (voice loop / text mode / tray)
  config.py          env-driven settings
  voice/             wake word, STT (whisper), TTS (Kokoro), VAD
  brain/             LLM router (OmniRoute ⇄ Ollama), agent loop, persona
  memory/            SQLite history + facts + reminders
  tools/             files, apps, browser (CDP), Notion, system, registry
  proactive/         scheduler, morning briefing, reminders
  service/           logging, tray icon, startup
```

## Notes

- Requires Python 3.12 (faster-whisper/ctranslate2 has no 3.13 wheels).
- Browser control launches a dedicated Chrome instance with remote debugging.
- One-time model downloads (~300MB TTS + ~1GB STT) on first run.
