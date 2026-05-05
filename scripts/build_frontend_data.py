"""
Build Frontend Data
====================
Converts the full affirmations.json (with morphological analysis) into
a leaner frontend/data/affirmations.json that the website consumes.

Also writes frontend/data/today.json for fast first-load.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT             = Path(__file__).resolve().parent.parent
SOURCE_FILE      = ROOT / "affirmations" / "affirmations.json"
FRONTEND_DIR     = ROOT / "frontend" / "data"
FRONTEND_ALL     = FRONTEND_DIR / "affirmations.json"
FRONTEND_TODAY   = FRONTEND_DIR / "today.json"

FRONTEND_DIR.mkdir(parents=True, exist_ok=True)

FRONTEND_FIELDS = [
    "date", "passage_id", "book", "book_number", "quarter",
    "chapter", "theme", "category", "arabic",
    "affirmation", "brief_translation", "contextual_meaning",
]


def build():
    if not SOURCE_FILE.exists():
        print("No affirmations.json found — nothing to build.")
        return

    with open(SOURCE_FILE, "r", encoding="utf-8") as f:
        all_records = json.load(f)

    # Slim records for frontend
    slim = [
        {k: r[k] for k in FRONTEND_FIELDS if k in r}
        for r in all_records
    ]

    with open(FRONTEND_ALL, "w", encoding="utf-8") as f:
        json.dump(slim, f, ensure_ascii=False, indent=2)

    # Today's record
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today = next((r for r in slim if r["date"] == today_str), slim[-1] if slim else None)

    if today:
        with open(FRONTEND_TODAY, "w", encoding="utf-8") as f:
            json.dump(today, f, ensure_ascii=False, indent=2)

    print(f"Built {len(slim)} affirmations → frontend/data/")
    print(f"Today: {today['date'] if today else 'none'} — {today['affirmation'][:60] if today else ''}…")


if __name__ == "__main__":
    build()
