#!/usr/bin/env python3
"""Environment check script for Jarvis. Run by hook at startup."""

import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
errors = []
warnings = []

# Python version
if sys.version_info < (3, 9):
    errors.append(f"Python 3.9+ required, found {sys.version}")

# Required packages
required = [
    "anthropic",
    "google.oauth2",
    "googleapiclient",
    "dotenv",
    "speech_recognition",
    "whisper",
    "pyttsx3",
]
for pkg in required:
    try:
        __import__(pkg)
    except ImportError:
        errors.append(f"Missing package: {pkg} — run: pip install -r requirements.txt")

# credentials.json
if not (ROOT / "credentials" / "credentials.json").exists():
    errors.append("Missing credentials/credentials.json — download from Google Cloud Console")

# .env file
if not (ROOT / ".env").exists():
    warnings.append("Missing .env file — copy .env.example and fill in your API keys")

# ANTHROPIC_API_KEY
if not os.getenv("ANTHROPIC_API_KEY"):
    warnings.append("ANTHROPIC_API_KEY not set in .env")

# Report
if errors:
    print("❌ JARVIS ENVIRONMENT ERRORS:")
    for e in errors:
        print(f"  • {e}")
    sys.exit(1)

if warnings:
    print("⚠️  JARVIS WARNINGS:")
    for w in warnings:
        print(f"  • {w}")

print("✅ Jarvis environment OK")
sys.exit(0)
