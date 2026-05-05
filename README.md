# Ghazalia Backend — Daily Affirmation Pipeline

## How it works

Every morning at 8:00am Riyadh time, GitHub automatically:
1. Picks a verbatim Arabic passage from the Ihya corpus
2. Sends it to Google Gemini for deep etymological and morphological analysis
3. Generates an English affirmation grounded in the root meanings
4. Updates the website data files

## Setup

### 1. Get a free Gemini API key
- Go to https://aistudio.google.com/apikey
- Sign in with a Google account
- Click "Create API key"
- Copy the key

### 2. Add the key to GitHub
- In your repository: Settings -> Secrets and variables -> Actions
- Click "New repository secret"
- Name: GEMINI_API_KEY
- Secret: paste your key
- Click "Add secret"

### 3. Run for the first time
- Go to the Actions tab in your repository
- Click "Daily Affirmation Generator"
- Click "Run workflow" -> "Run workflow"
- Wait for the green checkmark

### 4. Connect to your website
After a successful run, open your website's index.html and replace
YOUR_GITHUB_USERNAME with your actual GitHub username (two places).

## File structure

```
ghazalia-backend/
├── .github/workflows/daily.yml     <- runs every morning automatically
├── data/ihya_corpus.json           <- 50 verbatim Arabic passages
├── scripts/
│   ├── generate_affirmation.py     <- calls Gemini, writes output
│   ├── build_frontend_data.py      <- prepares data for the website
│   └── validate.py                 <- checks Arabic text integrity
├── affirmations/                   <- generated output (auto-filled)
│   └── daily/
└── frontend/data/                  <- website reads from here (auto-filled)
```

## Cost
The Gemini API free tier allows 1,500 requests per day.
This pipeline uses 1 request per day. It is completely free.
