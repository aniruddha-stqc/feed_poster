# feed_poster

AI-powered Bangla entertainment news pipeline.

- Collects RSS feeds (News18, ABP, HT Bangla, etc.)
- Stores items in Firestore (`news_items`, status="raw")
- Uses Google Gemini to generate summaries
- Preps content for auto-posting to Telegram / socials

## Components

- `rss_collector.py` – RSS → Firestore (`status="raw"`)
- `processor.py` – Firestore raw → Gemini summary → `status="ready"`
- `gemini_summarizer.py` – Gemini API wrapper (key in `config/gemini_key.txt`)
- `firestore_test_push.py` – simple Firestore connectivity test

## Secrets

Not committed to git:

- `config/gemini_key.txt`
- `config/firestore_sa.json`

Both must be created locally before running the scripts.
