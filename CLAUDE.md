# Jarvis - Voice Assistant

## Project Overview
Personal AI voice assistant that listens to voice commands, understands intent 
using Claude API with tool use, and executes actions like querying Google Calendar.

## Tech Stack
- Python 3.x
- Claude API (tool use / function calling)
- Whisper (speech-to-text)
- Google Calendar API (OAuth2)
- TTS for voice responses

## Requirements
- Python 3.12
- ffmpeg (installed automatically by setup.py)

## Commands
- Setup: `python setup.py`
- Dev: `python -m src.main`
- Tests: `pytest tests/`

## Architecture
- src/voice/listener.py → captures microphone audio
- src/voice/speaker.py → text-to-speech output
- src/transcription/whisper.py → audio to text
- src/gcalendar/auth.py → Google OAuth2
- src/gcalendar/events.py → Calendar API calls
- src/gmail/auth.py → Gmail OAuth2
- src/gmail/messages.py → Gmail API calls (list unread, send reply, mark read)
- src/tools/definitions.py → Claude tool definitions
- src/main.py → orchestrator / entry point

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
