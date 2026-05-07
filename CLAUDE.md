# Jarvis - Voice Assistant

## Project Overview
Personal AI voice assistant that listens to voice commands, understands intent 
using Claude API with tool use, and executes actions like querying Google Calendar,
reading Gmail, controlling Spotify, and fetching weather.

## Tech Stack
- Python 3.12
- Claude API (tool use / function calling) — claude-haiku-4-5-20251001
- openWakeWord (wake word detection — "alexa" model, offline)
- Whisper (speech-to-text, local)
- ElevenLabs (text-to-speech)
- Google Calendar API (OAuth2)
- Gmail API (OAuth2)
- Spotify Web API via spotipy
- OpenWeatherMap REST API

## Requirements
- Python 3.12
- ffmpeg (installed automatically by setup.py)

## Commands
- Setup: `python setup.py` — creates venv312, installs dependencies, installs ffmpeg
- Activate venv: `venv312\Scripts\activate` (Windows)
- Run: `python -m src.main`
- Tests: `pytest tests/`
- Autostart: `powershell -ExecutionPolicy Bypass -File setup_autostart.ps1`

## Architecture
- src/main.py → orchestrator / entry point
- src/voice/listener.py → captures microphone audio (SpeechRecognition)
- src/voice/speaker.py → text-to-speech output (ElevenLabs)
- src/voice/wake_word.py → wake word detection (openWakeWord "alexa" model)
- src/transcription/whisper.py → audio to text (local Whisper model)
- src/intent/goodbye.py → pre-LLM farewell phrase detection
- src/gcalendar/auth.py → Google Calendar OAuth2
- src/gcalendar/events.py → Calendar API calls (today, upcoming, create)
- src/gmail/auth.py → Gmail OAuth2
- src/gmail/messages.py → Gmail API calls (list unread, send reply, mark read)
- src/weather/client.py → OpenWeatherMap REST client
- src/weather/summary.py → weather phrase formatter for startup greeting
- src/spotify/auth.py → Spotify OAuth2 (Authorization Code flow, token cached)
- src/spotify/playback.py → Spotify playback control (play, pause, skip, volume)
- src/spotify/launcher.py → auto-launch Spotify desktop app on Windows
- src/tools/definitions.py → Claude tool definitions (static TOOLS list)

## Code Style
- Python type hints always
- Never hardcode API keys — use .env
- Descriptive variable names in English

## Critical Constraints
- NEVER commit credentials or API keys
- credentials/ folder is gitignored
- All secrets go in .env file

## Available Agents
- planner → plan features before implementing
- architect → system design decisions
- code-reviewer → review before committing
- python-reviewer → Python specific review
- security-reviewer → check credentials and API security
- tdd-guide → test-driven development
- build-error-resolver → fix dependency issues

## Available Skills
- backend-patterns → API and database patterns
- api-design → endpoint design
- python-patterns → Python best practices
- python-testing → pytest patterns
- tdd-workflow → TDD methodology
- security-review → security checklist
- voice-response → format text to be natural when spoken aloud by TTS
- intent-parser → parse natural language voice commands into structured intents
- calendar-reader → format raw calendar API responses as conversational language
