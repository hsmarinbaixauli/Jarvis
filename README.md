# 🤖 Jarvis - Voice Assistant

A personal AI voice assistant powered by Claude API and Google Calendar.

## What it does

- 🎤 Listens to your voice
- 📝 Transcribes speech to text
- 🧠 Claude understands your intent and executes tools
- 📅 Queries and creates Google Calendar events
- 🔊 Responds by voice or text

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
jarvis/
├── .claude/
│   ├── agents/        # Specialized subagents
│   └── skills/        # Task-specific skills
├── src/
│   ├── voice/         # Audio input/output
│   ├── transcription/ # Speech-to-text
│   ├── calendar/      # Google Calendar integration
│   └── tools/         # Claude tool definitions
└── main.py            # Entry point

## Status

🚧 MVP in development

## Author

Hugo - learning to build AI agents with Claude Code