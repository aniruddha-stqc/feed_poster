from gemini_summarizer import summarize_one_liner, telegram_caption, instagram_caption

item = {
    "title": "নতুন ছবিতে জিতের সঙ্গে জুটি বাঁধছেন মিমি",
    "raw_summary": "দীর্ঘ বিরতির পর আবার বড় পর্দায় ফিরছেন মিমি চক্রবর্তী।",
    "source": "News18 Bangla",
    "url": "https://example.com"
}

print("ONE LINE:")
print(summarize_one_liner(item["title"], item["raw_summary"]))

print("\nTELEGRAM:")
print(telegram_caption(item["title"], item["raw_summary"], item["source"], item["url"]))

print("\nINSTAGRAM:")
print(instagram_caption(item["title"], item["raw_summary"], item["source"]))
