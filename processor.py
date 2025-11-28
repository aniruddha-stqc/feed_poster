# processor.py
from datetime import datetime, timezone

from google.cloud import firestore

from gemini_summarizer import (
    summarize_one_liner,
    telegram_caption,
    instagram_caption,
)
from card_generator import create_card
from hashtags import build_hashtags


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



def process_one_doc(doc_ref, data: dict):
    title = data.get("title", "") or ""
    raw_summary = data.get("raw_summary", "") or ""
    source = data.get("source", "") or ""
    url = data.get("url", "") or ""
    published_at = (data.get("published_at") or "")[:10]

    # 1) Gemini text generation
    try:
        one_line = summarize_one_liner(title, raw_summary)
        cap_tg = telegram_caption(title, raw_summary, source, url)
        cap_ig = instagram_caption(title, raw_summary, source)
        mode = "gemini"
        gemini_error = None
    except Exception as e:
        # You can plug your template_summarizer fallback here if you want
        one_line = title[:120]
        cap_tg = f"📰 {title}\n\n🔗 {url}"
        cap_ig = f"🎬 {title}\n\nSource: {source}"
        mode = "fallback"
        gemini_error = str(e)

    # 2) Hashtags
    hashtags = build_hashtags(data)
    tag_line = " ".join(hashtags) if hashtags else ""

    caption_telegram_full = cap_tg + ("\n\n" + tag_line if tag_line else "")
    caption_instagram_full = cap_ig + ("\n\n" + tag_line if tag_line else "")

    # 3) Image card via Pillow
    card_path = create_card(title=title, source=source, date_str=published_at)

    # 4) Update Firestore
    update_data = {
        "summary": one_line,
        "caption_telegram": caption_telegram_full,
        "caption_instagram": caption_instagram_full,
        "hashtags": hashtags,
        "image_card_path": card_path,
        "status": "ready",
        "processed_at": datetime.now(timezone.utc),
        "ai_mode": mode,
    }
    if gemini_error:
        update_data["gemini_error"] = gemini_error

    doc_ref.update(update_data)


def main():
    client = get_firestore_client()
    col = client.collection("news_items")

    # Get items that are still raw
    docs = col.where("status", "==", "raw").stream()

    count = 0
    for doc in docs:
        data = doc.to_dict()
        try:
            process_one_doc(doc.reference, data)
            count += 1
        except Exception as e:
            # mark as error so it doesn't block forever
            doc.reference.update({
                "status": "error",
                "processing_error": str(e),
                "processed_at": datetime.now(timezone.utc),
            })
    print(f"Processed {count} items.")


if __name__ == "__main__":
    main()
