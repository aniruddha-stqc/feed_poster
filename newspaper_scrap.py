import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

BASE_URL = "https://bartamanpatrika.com"
CATEGORY_URL = "https://bartamanpatrika.com/category/binodon"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}


def scrape_binodon_cards(url: str):
    """Scrape the listing page and return basic card info."""
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    cards_data = []

    for card in soup.select("div.col-md-4 > div.sg-post"):
        # Title + article URL
        title_link = card.select_one(".entry-content.catepage-grid a")
        if title_link:
            title_text = title_link.get_text(strip=True)
            article_url = urljoin(url, title_link.get("href", "").strip())
        else:
            title_text = None
            article_url = None

        # Image URL
        img_tag = card.select_one(".entry-header.catepage-img img")
        image_url = None
        if img_tag:
            img_src = img_tag.get("data-original") or img_tag.get("src")
            if img_src:
                image_url = urljoin(url, img_src.strip())

        # Category
        cat_link = card.select_one(".category ul.global-list li a")
        if cat_link:
            category_text = cat_link.get_text(strip=True)
            category_url = urljoin(url, cat_link.get("href", "").strip())
        else:
            category_text = None
            category_url = None

        cards_data.append({
            "title": title_text,
            "article_url": article_url,
            "card_image_url": image_url,
            "category": category_text,
            "category_url": category_url,
        })

    return cards_data


def scrape_article(article_url: str):
    """Scrape a single article page: title, short desc, image, author, date, full text."""
    resp = requests.get(article_url, headers=HEADERS)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # --- Title ---
    # Example: <h3 class="entry-title articletitle">বায়োপিকে  তামান্না</h3>
    title_tag = soup.select_one("h3.entry-title.articletitle")
    if not title_tag:
        # fallback (just in case layout varies)
        title_tag = soup.find(["h1", "h2", "h3"])
    title = title_tag.get_text(strip=True) if title_tag else None

    # --- Short description (top paragraph block) ---
    # <div class="entry-content shortdes p-4"><p>...</p></div>
    short_desc_tag = soup.select_one("div.entry-content.shortdes p")
    short_description = short_desc_tag.get_text(" ", strip=True) if short_desc_tag else None

    # --- Main article image ---
    # <div class="entry-thumbnail"><img src="..." data-original="..."></div>
    img_tag = soup.select_one(".entry-header .entry-thumbnail img") or \
              soup.select_one(".entry-thumbnail img")
    article_image_url = None
    if img_tag:
        img_src = img_tag.get("data-original") or img_tag.get("src")
        if img_src:
            article_image_url = urljoin(article_url, img_src.strip())

    # --- Author + date (post-author block) ---
    # <div class="post-author ..."><div class="text"><h3>বর্তমান ওয়েবডেস্ক</h3><h6>ডিসেম্বর ১, ২০২৫</h6>
    author_tag = soup.select_one(".post-author .text h3")
    date_tag = soup.select_one(".post-author .text h6")
    author = author_tag.get_text(strip=True) if author_tag else None
    date_str = date_tag.get_text(strip=True) if date_tag else None

    # --- Full article text ---
    # Your sample:
    # <div class="entry-content p-4">
    #   <div class="paragraph"><p>...</p></div>
    # </div>
    full_paragraphs = []

    # Prefer the main content block with .entry-content and .paragraph
    content_block = soup.select_one("div.entry-content.p-4") or soup.select_one("div.entry-content")
    if content_block:
        # Prefer paragraphs inside a .paragraph div if present
        paragraph_container = content_block.select_one("div.paragraph") or content_block
        for p in paragraph_container.select("p"):
            text = p.get_text(" ", strip=True)
            if text:
                full_paragraphs.append(text)

    full_text = "\n\n".join(full_paragraphs) if full_paragraphs else None

    return {
        "article_title": title,
        "short_description": short_description,
        "article_image_url": article_image_url,
        "author": author,
        "date": date_str,
        "full_text": full_text,
    }


def scrape_binodon_with_articles():
    """Full pipeline: listing page -> each article page."""
    cards = scrape_binodon_cards(CATEGORY_URL)
    results = []

    for idx, card in enumerate(cards, start=1):
        url = card.get("article_url")
        if not url:
            continue

        print(f"[{idx}/{len(cards)}] Fetching article: {url}")
        try:
            article_data = scrape_article(url)
        except Exception as e:
            print(f"  !! Error scraping article {url}: {e}")
            article_data = None

        combined = {**card, "article_details": article_data}
        results.append(combined)

        # Be polite (and reduce risk of being blocked)
        time.sleep(1)

    return results


if __name__ == "__main__":
    data = scrape_binodon_with_articles()
    # Example output
    for item in data:
        print("=" * 80)
        print("CARD TITLE:", item["title"])
        print("ARTICLE URL:", item["article_url"])
        if item["article_details"]:
            print("ARTICLE TITLE:", item["article_details"]["article_title"])
            print("AUTHOR:", item["article_details"]["author"])
            print("DATE:", item["article_details"]["date"])
            print("SHORT DESC:", item["article_details"]["short_description"])
            print("FULL TEXT (first 200 chars):")
            full = item["article_details"]["full_text"] or ""
            print(full[:200], "..." if len(full) > 200 else "")
