# news_collector.py

import os
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import urlparse

import pandas as pd
from google.oauth2 import service_account
from google.cloud import firestore

from newspaper_scrap import (
    scrape_bartaman_binodon_with_articles,
    scrape_dainik_statesman_binodan_with_articles,
    scrape_eisamay_entertainment_with_articles,

    BARTAMAN_CATEGORY_URL,
    DS_CATEGORY_URL,
    EISAMAY_ENT_CATEGORY_URL,
)

# -------------------------
# Firestore helpers
# -------------------------


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
    Uses uid as document ID so duplicates (same uid) are skipped.
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

        data = {
            "uid": item["uid"],
            "title": item["title"],
            "raw_summary": item["summary_raw"],
            "full_text": item.get("full_text", ""),   # 👈 ADD THIS
            "url": item["link"],
            "source": item["source"],
            "feed_url": item["feed_url"],
            "media_url": item.get("media_url") or "",
            "published_raw": item["published"],
            "published_at": item.get("published_dt_str", ""),  # ISO string
            "status": "raw",
            "created_at": datetime.now(timezone.utc),
        }


        doc_ref.set(data)
        added += 1

    print(f"\nFirestore push: added {added}, skipped {skipped} (already existed).")


# -------------------------
# Misc helpers
# -------------------------

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


# -------------------------
# Scraped sources collector
# -------------------------


def collect_scraped():
    """
    Use scraped Bartaman + Dainik Statesman + Eisamay instead of RSS.
    Returns a list of dicts compatible with the old RSS pipeline.
    """
    rows = []

    # ---------- Bartaman ----------
    try:
        bartaman_items = scrape_bartaman_binodon_with_articles()

    except Exception as e:
        print(f"Error scraping Bartaman: {e}")
        bartaman_items = []

    for item in bartaman_items:
        ad = item.get("article_details") or {}

        title = (ad.get("article_title") or item.get("title") or "").strip()
        link = (item.get("article_url") or "").strip()
        summary = (ad.get("short_description") or "").strip()
        media_url = (ad.get("article_image_url") or item.get("card_image_url") or "").strip()
        published = (ad.get("date") or "").strip()
        full_text = (ad.get("full_text") or "").strip()   # 👈 NEW

        # keep all original scraped fields
        row = dict(item)
        # and override / add normalized fields
        row.update({
            "uid": make_uid(link, title),
            "source": "Bartaman Binodon",
            "feed_url": BARTAMAN_CATEGORY_URL,
            "title": title,
            "summary_raw": summary,
            "full_text": full_text,      # 👈 TOP-LEVEL FIELD
            "link": link,
            "published": published,
            "media_url": media_url,
            "status": "raw",
        })

        rows.append(row)


    # ---------- Dainik Statesman ----------
    try:
        ds_items = scrape_dainik_statesman_binodan_with_articles()
    except Exception as e:
        print(f"Error scraping Dainik Statesman: {e}")
        ds_items = []

    for item in ds_items:
        ad = item.get("article_details") or {}

        title = (ad.get("article_title") or item.get("title") or "").strip()
        link = (item.get("article_url") or "").strip()
        summary = (ad.get("short_description") or "").strip()
        media_url = (ad.get("article_image_url") or item.get("card_image_url") or "").strip()
        published = (ad.get("date") or "").strip()
        full_text = (ad.get("full_text") or "").strip()   # 👈 NEW

        row = dict(item)
        row.update({
            "uid": make_uid(link, title),
            "source": "Dainik Statesman Binodan",
            "feed_url": DS_CATEGORY_URL,
            "title": title,
            "summary_raw": summary,
            "full_text": full_text,      # 👈 NEW
            "link": link,
            "published": published,
            "media_url": media_url,
            "status": "raw",
        })

        rows.append(row)


    # ---------- Eisamay Entertainment ----------
    try:
        es_items = scrape_eisamay_entertainment_with_articles()
    except Exception as e:
        print(f"Error scraping Eisamay: {e}")
        es_items = []

    for item in es_items:
        ad = item.get("article_details") or {}

        title = (ad.get("article_title") or item.get("title") or "").strip()
        link = (item.get("article_url") or "").strip()
        summary = (ad.get("short_description") or item.get("listing_subheadline") or "").strip()
        media_url = (ad.get("article_image_url") or item.get("card_image_url") or "").strip()
        published = (ad.get("date") or "").strip()
        full_text = (ad.get("full_text") or "").strip()   # 👈 NEW

        row = dict(item)
        row.update({
            "uid": make_uid(link, title),
            "source": "Eisamay Entertainment",
            "feed_url": EISAMAY_ENT_CATEGORY_URL,
            "title": title,
            "summary_raw": summary,
            "full_text": full_text,      # 👈 NEW
            "link": link,
            "published": published,
            "media_url": media_url,
            "status": "raw",
        })

        rows.append(row)


    return rows


# -------------------------
# Main
# -------------------------


def main():
    rows = collect_scraped()

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

    # 4) Drop the Timestamp column (so JSON never sees it)
    df = df.drop(columns=["published_dt"])

    # 5) To dict – now all values are plain Python types
    items = df.to_dict(orient="records")

    # 6) Save JSON (for debugging / local inspection)
    OUTFILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Saved {len(items)} items to {OUTFILE.resolve()}")

    # Debug print a few headlines
    for i, item in enumerate(items[:3], start=1):
        print("=" * 80)
        print(f"[{i}] {item['source']}")
        print(f"    {item['published_dt_str']}")
        print(f"    {item['title']}")

    # 7) Push to Firestore
    push_to_firestore(items)


if __name__ == "__main__":
    main()
