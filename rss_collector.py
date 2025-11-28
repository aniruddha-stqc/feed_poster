import feedparser
import pandas as pd
from urllib.parse import urlparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

from google.cloud import firestore
from google.oauth2 import service_account

# -------------------------
# Firestore helpers
# -------------------------

import os
import json
from google.oauth2 import service_account
from pathlib import Path
from google.cloud import firestore


def get_firestore_client():
    # Priority: ENV > local config file
    sa_data = os.getenv("FIRESTORE_SA_JSON")

    if sa_data:
        info = json.loads(sa_data)
        creds = service_account.Credentials.from_service_account_info(info)
        return firestore.Client(credentials=creds, project=info["project_id"])

    # Local dev fallback
    base_dir = Path(__file__).parent
    key_path = base_dir / "config" / "firestore_sa.json"

    if not key_path.exists():
        raise RuntimeError("Firestore credentials not found (env or file).")

    creds = service_account.Credentials.from_service_account_file(str(key_path))
    return firestore.Client(credentials=creds, project=creds.project_id)


def push_to_firestore(items):
    """
    Push items to Firestore collection 'news_items'.
    Uses uid as document ID so duplicates are skipped.
    """
    client = get_firestore_client()
    col = client.collection("news_items")

    added = 0
    skipped = 0

    for item in items:
        doc_id = item["uid"]
        doc_ref = col.document(doc_id)

        # Dedup – if already exists, skip
        if doc_ref.get().exists:
            skipped += 1
            continue

        # Map fields to Firestore document structure
        data = {
            "uid": item["uid"],
            "title": item["title"],
            "raw_summary": item["summary_raw"],
            "url": item["link"],
            "source": item["source"],
            "feed_url": item["feed_url"],
            "media_url": item.get("media_url") or "",
            "published_raw": item["published"],
            "published_at": item.get("published_dt_str", ""),  # ISO string
            "status": "raw",  # pipeline status (instead of "NEW")
            "created_at": datetime.now(timezone.utc),
        }

        doc_ref.set(data)
        added += 1

    print(f"\nFirestore push: added {added}, skipped {skipped} (already existed).")


# -------------------------
# Your existing RSS logic
# -------------------------

FEED_URLS = [
    "https://bangla.hindustantimes.com/rss/entertainment",
    "https://bengali.abplive.com/entertainment/feed",
    "https://bengali.news18.com/commonfeeds/v1/ben/rss/entertainment/film-review.xml",
    "https://bengali.news18.com/commonfeeds/v1/ben/rss/entertainment/tollywood-movies.xml",
    "https://timesofindia.indiatimes.com/rssfeedsvideo/3812908.cms",
]

OUTFILE = Path("pipeline_items.json")


def make_uid(link: str, title: str) -> str:
    base = (link or "") + "|" + (title or "")
    return hashlib.md5(base.encode("utf-8")).hexdigest()


def get_source_name(feed, feed_url):
    title = feed.feed.get("title")
    if title:
        return title.strip()
    netloc = urlparse(feed_url).netloc
    return netloc.replace("www.", "")


def extract_media_url(entry):
    if hasattr(entry, "media_content") and entry.media_content:
        url = entry.media_content[0].get("url")
        if url:
            return url
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        url = entry.media_thumbnail[0].get("url")
        if url:
            return url
    if "enclosures" in entry and entry.enclosures:
        url = entry.enclosures[0].get("href")
        if url:
            return url
    return None


def collect_rss():
    rows = []
    for feed_url in FEED_URLS:
        feed = feedparser.parse(feed_url)
        source_name = get_source_name(feed, feed_url)

        for entry in feed.entries:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            media_url = extract_media_url(entry)
            published = entry.get("published", entry.get("pubDate", ""))

            row = {
                "uid": make_uid(link, title),
                "source": source_name,
                "feed_url": feed_url,
                "title": title,
                "summary_raw": (entry.get("summary", entry.get("description", "")) or "").strip(),
                "link": link,
                "published": published,
                "media_url": media_url or "",
                "status": "NEW",  # local status, Firestore gets "raw"
            }
            rows.append(row)
    return rows


def main():
    rows = collect_rss()
    df = pd.DataFrame(rows)

    # 1) Parse published → published_dt (Timestamp / NaT)
    df["published_dt"] = pd.to_datetime(
        df["published"],
        utc=True,
        errors="coerce",
    )

    # 2) Sort by datetime
    df = df.sort_values(by="published_dt", ascending=False).reset_index(drop=True)

    # 3) Make a STRING version for JSON (NaT becomes NaN, then we fill with "")
    df["published_dt_str"] = df["published_dt"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
    df["published_dt_str"] = df["published_dt_str"].fillna("")

    # 4) Drop the problematic Timestamp column completely (so JSON never sees it)
    df = df.drop(columns=["published_dt"])

    # 5) To dict – now all values are plain Python types (str, int, etc.)
    items = df.to_dict(orient="records")

    # 6) Save JSON (for debugging / local inspection)
    OUTFILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved {len(items)} items to {OUTFILE.resolve()}")
    for i, item in enumerate(items[:3], start=1):
        print("=" * 80)
        print(f"[{i}] {item['source']}")
        print(f"    {item['published_dt_str']}")
        print(f"    {item['title']}")

    # 7) Push to Firestore
    push_to_firestore(items)


if __name__ == "__main__":
    main()
