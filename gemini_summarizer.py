# gemini_summarizer.py
import os
from pathlib import Path
import google.generativeai as genai

# -------------------------
# LOAD API KEY (ENV → FILE)
# -------------------------
KEY_FILE = Path(__file__).parent / "config" / "gemini_key.txt"

# First try environment variable (for GitHub Actions / CI)
API_KEY = os.getenv("GEMINI_API_KEY")

# Fallback: local file (for your laptop)
if not API_KEY and KEY_FILE.exists():
    API_KEY = KEY_FILE.read_text(encoding="utf-8").strip()

if not API_KEY:
    raise RuntimeError(
        "GEMINI API key not found. Set GEMINI_API_KEY env var or create config/gemini_key.txt"
    )

genai.configure(api_key=API_KEY)



# -------------------------
# MODEL SELECTION
# -------------------------
SYSTEM_PROMPT = """
You are a Bengali Tollywood entertainment news editor.

Rules:
- If the title is Bangla, respond ONLY in Bangla.
- If the title is English, respond ONLY in English.
- Never invent facts.
- Keep outputs short, punchy, and social-media ready.
"""

MODEL_NAME = "models/gemini-2.5-flash"

model = genai.GenerativeModel(
    MODEL_NAME,
    system_instruction=SYSTEM_PROMPT,
)


# -------------------------
# HELPER
# -------------------------
def _ask_gemini(prompt: str) -> str:
    response = model.generate_content(prompt)
    if not response or not getattr(response, "text", None):
        raise RuntimeError("Empty Gemini response")
    return response.text.strip()


# -------------------------
# PUBLIC API
# -------------------------
def summarize_one_liner(title: str, summary: str) -> str:
    prompt = f"""
Summarize this entertainment news into ONE punchy line (max 120 characters).
No emojis.

---NEWS---
Title: {title}
Summary: {summary}
"""
    return _ask_gemini(prompt)[:140]


def telegram_caption(title: str, summary: str, source: str, url: str) -> str:
    prompt = f"""
Write a Telegram caption for this Tollywood news.

Rules:
- 2–3 short lines
- Headline style first line
- Max 2 emojis
- Include a CTA line like: "পুরো খবর পড়ুন নিচের লিঙ্কে:"
- No invented information
- Do NOT shorten or change the URL.
- You don't need to mention the source or URL yourself; that will be added separately.

---NEWS---
Title: {title}
Summary: {summary}
Source: {source}
Link: {url}
"""
    body = _ask_gemini(prompt).strip()

    lines = [body]

    # Ensure source line is present
    if source and source not in body and f"সূত্র: {source}" not in body:
        lines.append(f"সূত্র: {source}")

    # Ensure URL is present
    if url and url not in body:
        lines.append(url)

    return "\n".join(lines)

def instagram_caption(title: str, summary: str, source: str) -> str:
    prompt = f"""
Write an Instagram caption for a Tollywood entertainment post.

Rules:
- Friendly, natural tone
- 3–6 emojis
- 3–6 short lines
- Mention source casually
- End with 5–7 relevant hashtags

---NEWS---
Title: {title}
Summary: {summary}
Source: {source}
"""
    return _ask_gemini(prompt)
