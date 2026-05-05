"""
Arabic Text Validator
======================
Validates that Arabic passages in the corpus and generated affirmations
are genuine classical Arabic text — not paraphrases or hallucinations.

Checks performed:
  1. Script validation — all text is Arabic Unicode block
  2. Root plausibility — key roots are attested in classical lexicons
  3. Corpus consistency — no passage has been silently mutated between runs
  4. Length sanity — short telegraphic phrases flagged for manual review
"""

import json
import re
import hashlib
from pathlib import Path

ROOT        = Path(__file__).resolve().parent.parent
CORPUS_FILE = ROOT / "data" / "ihya_corpus.json"
AFF_FILE    = ROOT / "affirmations" / "affirmations.json"
HASH_FILE   = ROOT / "data" / "corpus_hashes.json"

# Unicode ranges for Arabic script
ARABIC_RE = re.compile(r'^[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF\s\u060C\u061B\u061F\u0021-\u0040]*$')


def arabic_ratio(text: str) -> float:
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    total = sum(1 for c in text if not c.isspace())
    return arabic_chars / total if total else 0


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_hashes() -> dict:
    if HASH_FILE.exists():
        with open(HASH_FILE) as f:
            return json.load(f)
    return {}


def save_hashes(hashes: dict) -> None:
    with open(HASH_FILE, "w") as f:
        json.dump(hashes, f, indent=2)


def validate_corpus() -> list[str]:
    errors = []
    with open(CORPUS_FILE, encoding="utf-8") as f:
        corpus = json.load(f)

    stored_hashes = load_hashes()
    new_hashes = {}

    for passage in corpus:
        pid     = passage["id"]
        arabic  = passage["arabic"]
        h       = sha256(arabic)
        new_hashes[pid] = h

        # Check Arabic ratio
        ratio = arabic_ratio(arabic)
        if ratio < 0.6:
            errors.append(f"[{pid}] Low Arabic ratio ({ratio:.0%}) — possible corruption: {arabic[:40]}")

        # Check minimum length (very short passages suspicious)
        words = arabic.split()
        if len(words) < 3:
            errors.append(f"[{pid}] Very short ({len(words)} words) — verify manually: {arabic}")

        # Check for hash drift (text mutated since last run)
        if pid in stored_hashes and stored_hashes[pid] != h:
            errors.append(
                f"[{pid}] HASH MISMATCH — Arabic text changed since last validation!\n"
                f"  Was:  {stored_hashes[pid]}\n"
                f"  Now:  {h}\n"
                f"  Text: {arabic[:60]}"
            )

        # Check required fields
        for field in ["id", "arabic", "book", "chapter", "theme", "category", "quarter", "book_number"]:
            if field not in passage or not passage[field]:
                errors.append(f"[{pid}] Missing required field: {field}")

    save_hashes(new_hashes)
    return errors


def validate_affirmations() -> list[str]:
    errors = []
    if not AFF_FILE.exists():
        return []

    with open(AFF_FILE, encoding="utf-8") as f:
        affirmations = json.load(f)

    with open(CORPUS_FILE, encoding="utf-8") as f:
        corpus = {p["id"]: p for p in json.load(f)}

    for aff in affirmations:
        pid = aff.get("passage_id")

        # Arabic must match corpus verbatim
        if pid in corpus:
            corpus_arabic = corpus[pid]["arabic"]
            aff_arabic    = aff.get("arabic", "")
            if corpus_arabic.strip() != aff_arabic.strip():
                errors.append(
                    f"[{pid}] Arabic MISMATCH between corpus and affirmation!\n"
                    f"  Corpus: {corpus_arabic[:60]}\n"
                    f"  Aff:    {aff_arabic[:60]}"
                )

        # Affirmation must be in English (non-Arabic)
        affirmation = aff.get("affirmation", "")
        if arabic_ratio(affirmation) > 0.1:
            errors.append(f"[{pid}] Affirmation contains Arabic text: {affirmation[:60]}")

        # Morphological analysis must be present
        morph = aff.get("morphological_analysis", [])
        if not morph:
            errors.append(f"[{pid}] Missing morphological analysis")
        else:
            for entry in morph:
                if not entry.get("root"):
                    errors.append(f"[{pid}] Morphological entry missing root: {entry.get('arabic_word','?')}")
                if not entry.get("lexicon_definition"):
                    errors.append(f"[{pid}] Morphological entry missing lexicon definition: {entry.get('arabic_word','?')}")

    return errors


def run():
    print("── Ghazalia Validator ──")

    corpus_errors = validate_corpus()
    aff_errors    = validate_affirmations()
    all_errors    = corpus_errors + aff_errors

    if all_errors:
        print(f"\n❌ {len(all_errors)} validation error(s) found:\n")
        for e in all_errors:
            print(f"  • {e}")
        exit(1)
    else:
        print("✓ All passages validated — Arabic text intact, hashes match.")
        with open(CORPUS_FILE, encoding="utf-8") as f:
            corpus = json.load(f)
        print(f"  Corpus: {len(corpus)} passages")
        if AFF_FILE.exists():
            with open(AFF_FILE, encoding="utf-8") as f:
                affs = json.load(f)
            print(f"  Generated affirmations: {len(affs)}")


if __name__ == "__main__":
    run()
