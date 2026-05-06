"""One-shot setup script for Jarvis on Windows.

Run once:
    python setup.py

Then start Jarvis with:
    python -m src.main
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
VENV = ROOT / "venv312"
REQUIREMENTS = ROOT / "requirements.txt"


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kwargs)


def check_python312() -> str:
    """Return the path to the Python 3.12 executable, or exit with instructions."""
    for candidate in (
        ["py", "-3.12", "-c", "import sys; print(sys.executable)"],
        ["python3.12", "-c", "import sys; print(sys.executable)"],
    ):
        try:
            result = subprocess.run(
                candidate, capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue

    print(
        "\nPython 3.12 is not installed.\n"
        "Download it from: https://www.python.org/downloads/release/python-3120/\n"
        "Check 'Add Python to PATH' during installation, then re-run: python setup.py"
    )
    sys.exit(1)


def check_ffmpeg() -> None:
    """Ensure ffmpeg is on PATH; install via winget if missing."""
    if shutil.which("ffmpeg"):
        print("  ffmpeg: already installed.")
        return

    print("  ffmpeg not found — installing via winget...")
    try:
        _run([
            "winget", "install", "Gyan.FFmpeg",
            "--accept-package-agreements",
            "--accept-source-agreements",
        ])
        print("  ffmpeg installed. Restart your terminal if PATH is not updated yet.")
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        print(
            f"\nCould not install ffmpeg automatically ({exc}).\n"
            "Install it manually from https://ffmpeg.org/download.html\n"
            "and ensure it is on your PATH, then re-run: python setup.py"
        )
        sys.exit(1)


def create_venv(python312: str) -> Path:
    """Create venv312 with Python 3.12 if it does not already exist."""
    if VENV.exists():
        print(f"  venv312: already exists at {VENV}")
        return VENV

    print(f"  Creating virtual environment at {VENV} ...")
    _run([python312, "-m", "venv", str(VENV)])
    print("  Done.")
    return VENV


def install_requirements(venv: Path) -> None:
    pip = str(venv / "Scripts" / "pip.exe")
    if not REQUIREMENTS.exists():
        print("  requirements.txt not found — skipping.")
        return

    print("  Upgrading pip ...")
    _run([pip, "install", "--upgrade", "pip"], capture_output=True)

    print("  Installing requirements (this may take a minute) ...")
    _run([pip, "install", "-r", str(REQUIREMENTS)])
    print("  Done.")


def main() -> None:
    print("=== Jarvis Setup ===\n")

    print("[1/4] Checking Python 3.12 ...")
    python312 = check_python312()
    print(f"  Found: {python312}\n")

    print("[2/4] Checking ffmpeg ...")
    check_ffmpeg()
    print()

    print("[3/4] Setting up virtual environment ...")
    venv = create_venv(python312)
    print()

    print("[4/4] Installing Python dependencies ...")
    install_requirements(venv)

    print("\nJarvis is ready. Run: python -m src.main")


if __name__ == "__main__":
    main()
