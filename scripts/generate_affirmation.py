"""
Ghazalia Daily Affirmation Pipeline
====================================
Pulls verbatim Arabic passages from the Ihya corpus, performs deep
etymological and morphological analysis of each root word, then crafts
an English affirmation that is faithful to the original meaning.

Flow:
  1. Select today's passage from the curated Ihya corpus (ihya_corpus.json)
  2. Send Arabic text to Gemini for morphological decomposition (root -> form -> meaning)
  3. Gemini cross-references classical Arabic lexicons (Lisan al-Arab, Al-Misbah)
  4. Gemini produces an affirmation grounded in the etymological analysis
  5. Output is appended to affirmations.json and the daily file
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

# Paths
ROOT        = Path(__file__).resolve().parent.parent
CORPUS_FILE = ROOT / "data" / "ihya_corpus.json"
OUTPUT_FILE = ROOT / "affirmations" / "affirmations.json"
DAILY_DIR   = ROOT / "affirmations" / "daily"

DAILY_DIR.mkdir(parents=True, exist_ok=True)


# Gemini client (no SDK needed - plain HTTPS)
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
)

def call_gemini(system_prompt: str, user_prompt: str) -> str:
    """Call Gemini API and return the raw text response."""
    payload = json.dumps({
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": user_prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 2000,
        }
    }).encode("utf-8")

    req = urllib.request.Request(
        GEMINI_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        raise RuntimeError(f"Gemini API error {e.code}: {body}")

    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Unexpected Gemini response structure: {data}") from e


# Helpers
def load_corpus() -> list:
    with open(CORPUS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_affirmations() -> list:
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def get_used_ids(affirmations: list) -> set:
    return {a["passage_id"] for a in affirmations}


def select_passage(corpus: list, used_ids: set):
    """
    Pick the next unused passage from the corpus.
    Cycles back to the beginning once all passages are used.
    """
    unused = [p for p in corpus if p["id"] not in used_ids]
    if not unused:
        # Full cycle complete - reset and restart
        unused = corpus
    # Use today's date to pick deterministically (same passage all day)
    day_of_year = datetime.now(timezone.utc).timetuple().tm_yday
    return unused[day_of_year % len(unused)]


def save_affirmations(affirmations: list) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(affirmations, f, ensure_ascii=False, indent=2)


def save_daily(affirmation: dict) -> None:
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_file = DAILY_DIR / f"{date_str}.json"
    with open(daily_file, "w", encoding="utf-8") as f:
        json.dump(affirmation, f, ensure_ascii=False, indent=2)
    print(f"  Saved daily file: {daily_file.name}")


# Core prompts
SYSTEM_PROMPT = """You are a scholar of classical Arabic and Islamic spiritual literature,
specialising in the Ihya Ulum al-Din of Imam Abu Hamid al-Ghazali (d. 505 AH).
You have deep expertise in:

  - Arabic morphology (sarf): the derivation of words from tri- and quad-literal roots
  - Arabic syntax (nahw): how grammatical structure encodes meaning
  - Classical Arabic lexicography: Lisan al-Arab (Ibn Manzur), Al-Qamus al-Muhit (Fayruzabadi),
    Al-Misbah al-Munir (al-Fayyumi), and Mufradat Alfaz al-Quran (al-Raghib al-Isfahani)
  - The spiritual and theological register of al-Ghazali's prose

Your task is to perform a rigorous etymological-morphological analysis of a given Arabic
passage from the Ihya, and then produce an English affirmation that is:

  1. Faithful to the root meanings of the key Arabic words
  2. Attentive to the morphological form (e.g. masdar, fa'il, maf'ul, sifa mushabbaha)
     and how that form shapes nuance
  3. Not distorted by common English translation conventions that flatten meaning
  4. Written as a first-person affirmation suitable for daily contemplation
  5. Grounded in what al-Ghazali actually intended in context

You must return ONLY valid JSON. No prose outside the JSON object."""


def build_user_prompt(passage: dict) -> str:
    return f"""Analyse this verbatim passage from the Ihya Ulum al-Din:

ARABIC TEXT (verbatim):
{passage['arabic']}

SOURCE: {passage['book']}, {passage['chapter']}
THEME: {passage['theme']}

Perform the following steps and return them in the JSON structure below:

1. MORPHOLOGICAL BREAKDOWN - for each key word/phrase:
   - Identify the tri/quadliteral root
   - State the morphological pattern (wazn / bab)
   - Explain what the pattern itself contributes to meaning
   - Note the classical lexicon definition (Lisan al-Arab preferred)
   - Flag any word where standard English translations lose nuance

2. CONTEXTUAL MEANING - explain in 3-5 sentences what al-Ghazali means in the
   full context of this book and chapter. Reference his broader argument.

3. TRANSLATION RISKS - list specific English words or phrases that commonly
   mistranslate this passage and why they fail.

4. AFFIRMATION - write a single first-person affirmation in English (1-3 sentences)
   that captures the root meanings faithfully, avoids the translation risks identified,
   is poetic but precise, and would serve as a daily contemplative prompt.

Return EXACTLY this JSON structure with no text before or after it:
{{
  "morphological_analysis": [
    {{
      "arabic_word": "...",
      "root": "...",
      "pattern": "...",
      "pattern_meaning": "...",
      "lexicon_definition": "...",
      "translation_risk": "..."
    }}
  ],
  "contextual_meaning": "...",
  "translation_risks": ["...", "..."],
  "affirmation": "...",
  "brief_translation": "..."
}}"""


# Main pipeline
def run_pipeline(force: bool = False) -> dict:
    print("-- Ghazalia Affirmation Pipeline --")

    corpus       = load_corpus()
    affirmations = load_affirmations()
    used_ids     = get_used_ids(affirmations)

    print(f"  Corpus size:   {len(corpus)} passages")
    print(f"  Used so far:   {len(used_ids)}")

    # Check if today's affirmation already exists (idempotent)
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if not force:
        today_file = DAILY_DIR / f"{today_str}.json"
        if today_file.exists():
            print(f"  Today's affirmation already generated: {today_file.name}")
            with open(today_file, "r", encoding="utf-8") as f:
                return json.load(f)

    passage = select_passage(corpus, used_ids)
    print(f"  Selected passage: [{passage['id']}] {passage['book']}")
    print(f"  Arabic: {passage['arabic'][:60]}...")

    # Gemini call
    print("  Calling Gemini for etymological analysis...")
    raw = call_gemini(SYSTEM_PROMPT, build_user_prompt(passage))

    # Strip markdown code fences if present
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    analysis = json.loads(raw)

    # Assemble final record
    record = {
        "date":                   today_str,
        "passage_id":             passage["id"],
        "book":                   passage["book"],
        "book_number":            passage["book_number"],
        "chapter":                passage["chapter"],
        "quarter":                passage["quarter"],
        "theme":                  passage["theme"],
        "category":               passage["category"],
        "arabic":                 passage["arabic"],
        "affirmation":            analysis["affirmation"],
        "brief_translation":      analysis["brief_translation"],
        "contextual_meaning":     analysis["contextual_meaning"],
        "translation_risks":      analysis["translation_risks"],
        "morphological_analysis": analysis["morphological_analysis"],
        "generated_at":           datetime.now(timezone.utc).isoformat(),
    }

    # Persist
    affirmations.append(record)
    save_affirmations(affirmations)
    save_daily(record)

    print(f"  Affirmation: \"{record['affirmation'][:80]}...\"")
    print("-- Done --")
    return record


if __name__ == "__main__":
    force = "--force" in sys.argv
    result = run_pipeline(force=force)
    print(json.dumps(result, ensure_ascii=False, indent=2))
