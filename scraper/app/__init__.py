"""Scraper application package."""

import sys
from pathlib import Path

SHARED_PATH = Path(__file__).resolve().parents[2] / "shared" / "python"
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))
