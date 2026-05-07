# Jarvis - Voice Assistant

A personal AI voice assistant for Windows. Say "Alexa" to activate it, then speak naturally in Spanish. Jarvis understands your intent using Claude and can check your calendar, read emails, control Spotify, and report the weather.

## What it does

- **Wake word** — say "Alexa" to activate; no button press required
- **Calendar** — check today's events, upcoming week, create new events
- **Gmail** — read unread emails and send replies by voice
- **Spotify** — play music by artist/track/genre, pause, skip, set volume
- **Weather** — current conditions from OpenWeatherMap
- **Startup greeting** — on first activation each session, Jarvis greets you with the weather and your calendar summary
- **Autostart** — optional Windows startup shortcut so Jarvis is always running in the background

---

## Requirements

### Python 3.12
Download from [python.org/downloads](https://www.python.org/downloads/release/python-3120/). Check **"Add Python to PATH"** during installation.

### ffmpeg
Required by Whisper for audio decoding. `setup.py` installs it automatically via `winget`.

### LLM — Anthropic API
Jarvis uses Claude (Haiku model) for intent understanding and tool use. This requires an **Anthropic API account with paid credits** — the Claude Pro subscription plan does not grant API access. Sign up and add credits at [console.anthropic.com](https://console.anthropic.com).

### Text-to-speech
Three options, listed from best to simplest:

| Option | Quality | Cost | Key env var |
|---|---|---|---|
| **ElevenLabs** (current) | Best — natural, multilingual | Paid (free tier limited) | `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID` |
| **Google Cloud TTS** | Good | Free tier available (1M chars/month) | Requires Google Cloud credentials |
| **pyttsx3** | Basic — robotic | Free, fully offline | None |

The repo ships with ElevenLabs. To switch, replace `src/voice/speaker.py`.

### Speech recognition — Whisper
OpenAI Whisper runs **locally** for free. No API key needed. Model size is controlled by `WHISPER_MODEL` in `.env` (default: `base`). Larger models (`small`, `medium`) are more accurate but slower.

### Wake word — openWakeWord
Uses the **"alexa" model** from [openWakeWord](https://github.com/dscripka/openWakeWord), which runs **locally and offline** for free. The model is downloaded automatically on first run.

### Spotify
Requires a **Spotify Premium account** — the free tier does not support playback control via the API. You also need a [Spotify Developer app](https://developer.spotify.com/dashboard) for the API credentials.

### Google Calendar and Gmail
Free with any Google account. Requires a Google Cloud project with the Calendar API and Gmail API enabled, plus an OAuth2 desktop credentials file. See [Google Cloud Console](https://console.cloud.google.com).

---

## Setup

### 1. Run the setup script

```bash
python setup.py
```

This will:
- Verify Python 3.12 is installed
- Install ffmpeg via winget (if missing)
- Create a `venv312` virtual environment
- Install all Python dependencies from `requirements.txt`

### 2. Activate the virtual environment

```powershell
venv312\Scripts\activate
```

### 3. Configure `.env`

Copy the template below into a `.env` file in the project root and fill in your keys:

```env
# Anthropic (required)
ANTHROPIC_API_KEY=sk-ant-...

# ElevenLabs TTS (required for voice output)
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...

# OpenWeatherMap (required for weather)
OPENWEATHER_API_KEY=...
OPENWEATHER_CITY=Valencia,ES
OPENWEATHER_UNITS=metric

# Spotify (optional — Spotify features disabled if missing)
SPOTIFY_CLIENT_ID=...
SPOTIFY_CLIENT_SECRET=...
SPOTIFY_REDIRECT_URI=http://localhost:8888/callback

# Gmail send safety guard (set to 1 to enable email sending)
JARVIS_ALLOW_SEND=0

# Whisper model size: base (default), small, medium, large
WHISPER_MODEL=base

# Startup tabs — comma-separated URLs to open on first activation
# Leave blank for defaults (YouTube, Claude, Instagram)
JARVIS_STARTUP_URLS=

# ERP or custom URL appended to default startup tabs
ERP_URL=
```

### 4. Place Google credentials

Download `credentials.json` from the Google Cloud Console (OAuth2 desktop app) and place it at:

```
credentials/credentials.json
```

On first run, a browser window will open for Google OAuth consent. The resulting tokens are saved automatically to `credentials/token.json` and `credentials/gmail_token.json`.

### 5. Start Jarvis

```bash
python -m src.main
```

---

## How to use

1. **Activate** — say **"Alexa"** clearly. Jarvis will greet you with the weather and today's schedule.
2. **Speak** — ask anything naturally in Spanish. No wake word needed between turns within the same session.
3. **End session** — say "**Adiós**" or "**Hasta luego**" to exit.

If Jarvis hears nothing for two consecutive turns it goes back to listening for the wake word.

---

## Voice command examples

### Calendar
| Say | What happens |
|---|---|
| "¿Qué tengo hoy?" | Lists today's events |
| "¿Qué tengo esta semana?" | Lists events for the next 7 days |
| "Crea una reunión mañana a las 10 con el equipo" | Creates a calendar event |

### Gmail
| Say | What happens |
|---|---|
| "Lee mis emails" | Reads unread inbox messages |
| "Responde al de Juan diciendo que confirmo la reunión" | Drafts a reply — Jarvis reads it back and waits for your confirmation before sending |

### Weather
| Say | What happens |
|---|---|
| "¿Qué tiempo hace?" | Current conditions for the default city |
| "¿Qué tiempo hace en Madrid?" | Current conditions for a specific city |

### Spotify
| Say | What happens |
|---|---|
| "Pon jazz" | Plays a jazz playlist |
| "Pon a Duki" | Plays Duki's top tracks |
| "Pon La Víctima de Duki" | Plays that specific song |
| "Para" / "Pausa" | Pauses playback |
| "Siguiente" / "Salta" | Skips to next track |
| "Atrás" | Goes to previous track |
| "Volumen 60" | Sets volume to 60% |
| "¿Qué suena?" | Shows the current track |

---

## Autostart on Windows login

To have Jarvis launch automatically every time Windows starts:

```powershell
powershell -ExecutionPolicy Bypass -File setup_autostart.ps1
```

This creates a shortcut in `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`.

**To disable autostart:** delete the shortcut from that folder, or run:

```powershell
Remove-Item "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Jarvis.lnk"
```

---

## Project structure

```
jarvis/
├── setup.py               # One-shot setup
├── setup_autostart.ps1    # Windows autostart installer
├── requirements.txt
├── .env                   # Your secrets (gitignored)
├── credentials/           # Google OAuth tokens (gitignored)
└── src/
    ├── main.py            # Orchestrator / entry point
    ├── voice/             # Microphone input, TTS output, wake word
    ├── transcription/     # Whisper speech-to-text
    ├── intent/            # Pre-LLM intent detection (farewell)
    ├── gcalendar/         # Google Calendar integration
    ├── gmail/             # Gmail integration
    ├── weather/           # OpenWeatherMap client
    ├── spotify/           # Spotify playback control
    └── tools/             # Claude tool definitions
```

## Author

Hugo
