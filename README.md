# Ghazalia Backend — Daily Affirmation Pipeline

## Architecture Overview

```
ihya_corpus.json          (50 verbatim Arabic passages from the Ihya)
       │
       ▼
generate_affirmation.py   (Claude performs etymological + morphological analysis)
       │
       ├── affirmations/daily/YYYY-MM-DD.json   (full scholarly record)
       ├── affirmations/affirmations.json        (cumulative archive)
       └── frontend/data/affirmations.json       (lean frontend payload)
                         └── today.json

GitHub Actions runs this at 05:00 UTC every day, commits the result,
and the frontend (Ghazalia.com) fetches the latest data on load.
```

## What Makes This Rigorous

### 1. Verbatim Arabic Source
All Arabic text comes from `ihya_corpus.json`, which is hand-curated from
the standard Cairo edition of the Ihya Ulum al-Din (the scholarly reference
edition). The Arabic is **never generated** — only selected. A SHA-256 hash
of each passage is stored in `data/corpus_hashes.json` and verified on every
pipeline run. If any Arabic text changes between runs, the pipeline fails.

### 2. Etymological-Morphological Analysis
For each passage, Claude performs a full Arabic linguistic analysis:

- **Root (جذر)**: Every key word is traced to its tri- or quad-literal root
- **Pattern (وزن)**: The morphological pattern (e.g. فِعَال for habitual traits,
  مَفعُول for the object of an action) and what it contributes to meaning
- **Classical lexicons consulted**: Lisan al-Arab (Ibn Manzur, d. 711 AH),
  Al-Qamus al-Muhit (Fayruzabadi), Al-Misbah al-Munir (al-Fayyumi),
  Mufradat Alfaz al-Quran (al-Raghib al-Isfahani)
- **Translation risks**: Common English renderings that flatten or distort
  the original meaning are explicitly flagged before the affirmation is written

### 3. Output Structure (full scholarly record)

```json
{
  "date": "2026-05-04",
  "passage_id": "ihya-4-36-001",
  "book": "Book 36: On Love, Longing, Intimacy and Contentment",
  "quarter": "Quarter IV — On the Saving Virtues",
  "arabic": "المحبة هي الميل إلى ما يوافق...",
  "affirmation": "I was made to incline toward what is good — ...",
  "brief_translation": "...",
  "contextual_meaning": "...",
  "translation_risks": ["...", "..."],
  "morphological_analysis": [
    {
      "arabic_word": "المحبة",
      "root": "ح-ب-ب",
      "pattern": "مَفعَلة / محبة",
      "pattern_meaning": "Noun of place/intensity from حَبَّ. The pattern ...",
      "lexicon_definition": "Lisan al-Arab: al-hubb aslahu ...",
      "translation_risk": "'Love' in English suggests emotion only. ..."
    }
  ]
}
```

## Setup

### 1. Repository Structure
```
ghazalia-backend/
├── .github/
│   └── workflows/
│       └── daily.yml          # GitHub Actions scheduler
├── data/
│   ├── ihya_corpus.json        # Verbatim Arabic passages (source of truth)
│   └── corpus_hashes.json      # SHA-256 hashes (auto-generated, do not edit)
├── scripts/
│   ├── generate_affirmation.py # Main pipeline
│   ├── build_frontend_data.py  # Compiles lean frontend payload
│   └── validate.py             # Arabic integrity checker
├── affirmations/
│   ├── affirmations.json       # Full cumulative archive
│   └── daily/                  # One JSON per day
│       └── YYYY-MM-DD.json
├── frontend/
│   └── data/
│       ├── affirmations.json   # Lean version for the website
│       └── today.json          # Today's affirmation (fast load)
└── README.md
```

### 2. GitHub Repository Setup
1. Create a new GitHub repository (can be public or private)
2. Push this entire `ghazalia-backend/` folder to it
3. Go to **Settings → Secrets and Variables → Actions**
4. Add a secret named `ANTHROPIC_API_KEY` with your Anthropic API key

### 3. Connect Frontend to Backend
In your `index.html` on Ghazalia.com, replace the static `QUOTES` array with:

```javascript
async function loadAffirmations() {
  // Today's affirmation — fast path
  const todayRes = await fetch(
    'https://raw.githubusercontent.com/YOUR_USER/ghazalia-backend/main/frontend/data/today.json'
  );
  const today = await todayRes.json();

  // All affirmations — for Browse panel
  const allRes = await fetch(
    'https://raw.githubusercontent.com/YOUR_USER/ghazalia-backend/main/frontend/data/affirmations.json'
  );
  const all = await allRes.json();

  return { today, all };
}
```

Replace `YOUR_USER` with your GitHub username.

### 4. Run Manually (test before scheduling)
```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...

# Validate corpus first
python scripts/validate.py

# Generate today's affirmation
python scripts/generate_affirmation.py

# Build frontend data
python scripts/build_frontend_data.py

# Force regeneration of today's entry
python scripts/generate_affirmation.py --force
```

### 5. Schedule
The GitHub Actions workflow runs automatically at **05:00 UTC daily**
(8:00 AM Riyadh / KSA time — after Fajr).

To trigger manually: GitHub → Actions → "Daily Affirmation Generator" → "Run workflow"

## Adding More Passages to the Corpus
Edit `data/ihya_corpus.json` and add a new entry following this schema:

```json
{
  "id": "ihya-{quarter_number}-{book_number}-{sequence}",
  "quarter": "Quarter I — Acts of Worship",
  "book": "Book 4: On the Secrets of Prayer",
  "book_number": 4,
  "chapter": "Chapter 2: On Presence of Heart",
  "theme": "Brief description of what this passage addresses",
  "category": "Worship",
  "arabic": "...verbatim Arabic from the Ihya..."
}
```

**Critical**: The Arabic text must be taken verbatim from a reliable printed
edition of the Ihya. The recommended edition is the Dar al-Ma'rifa, Beirut
4-volume edition, which is also available on ghazali.org and archive.org.

After adding passages, run `python scripts/validate.py` to register the new
hash before the next automated run.

## Cost Estimate
Each Claude API call uses approximately 800–1200 tokens input and
400–600 tokens output. At current pricing, the pipeline costs roughly
**$0.01–0.02 per day** to run.
