# Jarvis - Voice Assistant

A personal AI voice assistant powered by Claude API and Google Calendar.

## Requirements

- **Python 3.12** — download from [python.org/downloads](https://python.org/downloads)

## Setup

```bash
python setup.py
python -m src.main
```

`setup.py` handles Python 3.12 verification, ffmpeg installation, virtual environment creation, and dependency installation automatically.

## Autostart on Windows login

To have Jarvis launch automatically every time Windows starts, run once:

```powershell
powershell -ExecutionPolicy Bypass -File setup_autostart.ps1
```

This creates a shortcut in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup` that opens Jarvis minimized in the background. To disable autostart, delete the shortcut from that folder (or run `Remove-Item` with the path printed by the script).

## What it does

- Listens to your voice
- Transcribes speech to text
- Claude understands your intent and executes tools
- Queries and creates Google Calendar events
- Responds by voice

## Example

> "Jarvis, what do I have today?"

Jarvis checks your calendar and responds with your schedule.

## Tech Stack

- **AI**: Claude API (tool use)
- **Voice input**: Whisper (speech-to-text)
- **Voice output**: TTS
- **Calendar**: Google Calendar API
- **Agents**: Claude Code with custom subagents and skills

## Project Structure

```
jarvis/
├── setup.py           # One-shot setup
├── src/
│   ├── main.py        # Entry point
│   ├── voice/         # Audio input/output
│   ├── transcription/ # Speech-to-text
│   ├── gcalendar/     # Google Calendar integration
│   ├── gmail/         # Gmail integration
│   └── tools/         # Claude tool definitions
└── .claude/
    ├── agents/        # Specialized subagents
    └── skills/        # Task-specific skills
```

## Author

Hugo