"""Konfigurasi bersama untuk aplikasi web, skrip, dan bot."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

DATABASE = os.getenv("DATABASE", str(ROOT / "instance" / "currycoach.sqlite3"))
REFERENCE_DIR = ROOT / "data" / "references"
WGER_API_URL = "https://wger.de/api/v2/exerciseinfo/"
USER_AGENT = "CurryCoachEducationalBot/1.0 (+student project; respectful crawler)"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CURRYCOACH_API_URL = os.getenv("CURRYCOACH_API_URL", "http://127.0.0.1:5000").rstrip("/")
