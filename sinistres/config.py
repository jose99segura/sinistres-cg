"""Settings read from the environment (and a local .env file in development)."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    # Tiny .env reader so local runs need no extra dependency. Real env vars win.
    path = ROOT / ".env"
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "ministral-14b-latest")
# Seconds between two model calls from this process (free tier: 30 requests/minute).
LLM_MIN_INTERVAL = float(os.environ.get("LLM_MIN_INTERVAL", "2.1"))
DB_PATH = ROOT / os.environ.get("DB_PATH", "data/sinistres.db")
PDF_DIR = ROOT / "data" / "pdfs"
SEGMENTS_DIR = ROOT / "data" / "segments"
CONTRACTS_FILE = ROOT / "contracts.yaml"

# Public demo protection: analyses per client IP per hour, and per instance per day.
RATE_PER_IP_HOUR = int(os.environ.get("RATE_PER_IP_HOUR", "20"))
RATE_GLOBAL_DAY = int(os.environ.get("RATE_GLOBAL_DAY", "500"))
