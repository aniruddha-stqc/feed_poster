from datetime import datetime, timezone
from pathlib import Path

from google.cloud import firestore
from google.oauth2 import service_account

from gemini_summarizer import summarize_one_liner


def get_firestore_client():
    # Path to service account JSON inside config/
    base_dir = Path(__file__).parent
    key_path = base_dir / "config" / "firestore_sa.json"

    if not key_path.exists():
        raise RuntimeError(f"Firestore service account file not found: {key_path}")

    creds = service_account.Credentials.from_service_account_file(str(key_path))
    # project_id is inside the JSON, so we reuse it
    return firestore.Client(credentials=creds, project=creds.project_id)


def main():
    client = get_firestore_client()
    col = client.collection("news_items")

    title = "নতুন ছবিতে জিতের সঙ্গে জুটি বাঁধছেন মিমি"
    raw_summary = "দীর্ঘ বিরতির পর আবার বড় পর্দায় ফিরছেন মিমি চক্রবর্তী।"

    # Use your Gemini layer
    summary = summarize_one_liner(title, raw_summary)

    data = {
        "title": title,
        "raw_summary": raw_summary,
        "summary": summary,
        "source": "test",
        "url": "https://example.com",
        "status": "ready",
        "created_at": datetime.now(timezone.utc),
    }

    doc_ref = col.document()
    doc_ref.set(data)

    print("✅ Firestore write successful.")
    print("Document ID:", doc_ref.id)


if __name__ == "__main__":
    main()
