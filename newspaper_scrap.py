import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ==============================
#  BARTAMAN BINODON
# ==============================

BARTAMAN_BASE_URL = "https://bartamanpatrika.com"
BARTAMAN_CATEGORY_URL = "https://bartamanpatrika.com/category/binodon"


def scrape_bartaman_binodon_cards(url: str):
    """Scrape the Bartaman Binodon listing page and return basic card info."""
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


def scrape_bartaman_article(article_url: str):
    """Scrape a single Bartaman article page."""
    resp = requests.get(article_url, headers=HEADERS)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # --- Title ---
    title_tag = soup.select_one("h3.entry-title.articletitle")
    if not title_tag:
        title_tag = soup.find(["h1", "h2", "h3"])
    title = title_tag.get_text(strip=True) if title_tag else None

    # --- Short description ---
    short_desc_tag = soup.select_one("div.entry-content.shortdes p")
    short_description = short_desc_tag.get_text(" ", strip=True) if short_desc_tag else None

    # --- Main article image ---
    img_tag = soup.select_one(".entry-header .entry-thumbnail img") or \
              soup.select_one(".entry-thumbnail img")
    article_image_url = None
    if img_tag:
        img_src = img_tag.get("data-original") or img_tag.get("src")
        if img_src:
            article_image_url = urljoin(article_url, img_src.strip())

    # --- Author + date ---
    author_tag = soup.select_one(".post-author .text h3")
    date_tag = soup.select_one(".post-author .text h6")
    author = author_tag.get_text(strip=True) if author_tag else None
    date_str = date_tag.get_text(strip=True) if date_tag else None

    # --- Full article text ---
    full_paragraphs = []

    # Prefer entry-content blocks that are NOT shortdes
    content_blocks = soup.select("div.entry-content")
    content_block = None

    for block in content_blocks:
        classes = block.get("class", [])
        # We want p-4 but not shortdes
        if "p-4" in classes and "shortdes" not in classes:
            content_block = block
            break

    # Fallback: if we didn't find a clean one, try second entry-content
    if content_block is None and len(content_blocks) >= 2:
        content_block = content_blocks[1]
    if content_block is None and content_blocks:
        content_block = content_blocks[0]

    if content_block is not None:
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


def scrape_bartaman_binodon_with_articles():
    """Entry function for Bartaman: listing page -> each article page."""
    cards = scrape_bartaman_binodon_cards(BARTAMAN_CATEGORY_URL)
    results = []

    for idx, card in enumerate(cards, start=1):
        url = card.get("article_url")
        if not url:
            continue

        print(f"[Bartaman {idx}/{len(cards)}] Fetching article: {url}")
        try:
            article_data = scrape_bartaman_article(url)


        except Exception as e:
            print(f"  !! Error scraping Bartaman article {url}: {e}")
            article_data = None

        combined = {**card, "article_details": article_data}
        results.append(combined)
        time.sleep(1)

    return results


# ==============================
#  DAINIK STATESMAN BINODAN
# ==============================

DS_BASE_URL = "https://www.dainikstatesmannews.com"
DS_CATEGORY_URL = "https://www.dainikstatesmannews.com/binodan/"


def scrape_dainik_statesman_binodan_cards(url: str):
    """
    Scrape the Dainik Statesman Binodan listing page and return basic card info.

    HTML example:

    <div class="col-md-4">
      <div class="post-block-style">
        <div class="post-thumb">
          <a href="ARTICLE_URL">
            <img src="IMAGE_URL" ...>
          </a>
        </div>
        <div class="post-content">
          <h3 class="post-title title-md">
            <a href="ARTICLE_URL"> TITLE </a>
          </h3>
          <div class="post-meta mb-7">
            <span class="post-author">... AUTHOR ...</span>
            <span class="post-date">0 mins read</span>
          </div>
        </div>
      </div>
    </div>
    """
    resp = requests.get(url, headers=HEADERS)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    cards_data = []

    for col in soup.select("div.col-md-4"):
        card = col.select_one("div.post-block-style")
        if not card:
            continue

        # --- Title + article URL ---
        title_link = card.select_one(".post-content h3.post-title a")
        if title_link:
            title_text = title_link.get_text(strip=True)
            href = title_link.get("href", "").strip()
            article_url = urljoin(DS_BASE_URL, href)
        else:
            title_text = None
            article_url = None

        # --- Image URL ---
        img_tag = card.select_one(".post-thumb img")
        card_image_url = None
        if img_tag:
            img_src = img_tag.get("src")
            if img_src:
                card_image_url = urljoin(DS_BASE_URL, img_src.strip())

        # --- Author + read-time ---
        author_span = card.select_one(".post-meta .post-author")
        if author_span:
            author_text = author_span.get_text(" ", strip=True).replace("\xa0", " ")
        else:
            author_text = None

        read_span = card.select_one(".post-meta .post-date")
        read_time = read_span.get_text(" ", strip=True) if read_span else None

        cards_data.append({
            "title": title_text,
            "article_url": article_url,
            "card_image_url": card_image_url,
            "author": author_text,
            "read_time": read_time,
        })

    return cards_data


def _ds_extract_author_and_date_from_text(soup: BeautifulSoup):
    """
    Fallback text-based parse for author + 'Published:' line on Dainik Statesman.
    Looks for patterns like:
      'Some Author | Kolkata'
      'Published: December 2, 2025 12:20 pm'
    """
    full_text = soup.get_text("\n", strip=True)

    date_match = re.search(r"Published:\s*(.+)", full_text)
    date_str = date_match.group(1).strip() if date_match else None

    author_match = re.search(
        r"([^\n]+?)\s*\|\s*[^\n]*\n\s*Published:",
        full_text
    )
    author = author_match.group(1).strip() if author_match else None

    return author, date_str


def scrape_dainik_statesman_article(article_url: str):
    """
    Scrape a single Dainik Statesman article page.
    """
    resp = requests.get(article_url, headers=HEADERS)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # --- Title ---
    title_tag = (
        soup.select_one("h1.entry-title")
        or soup.select_one("h1.post-title")
        or soup.find("h1")
        or soup.find("title")
    )
    article_title = title_tag.get_text(strip=True) if title_tag else None

    # --- Main article image ---
    img_tag = (
        soup.select_one("article .post-thumb img")
        or soup.select_one(".single-post-thumb img")
        or soup.select_one("img.wp-post-image")
    )
    article_image_url = None
    if img_tag:
        img_src = img_tag.get("src")
        if img_src:
            article_image_url = urljoin(article_url, img_src.strip())

    # --- Full text paragraphs ---
    content_block = (
        soup.select_one("article div.entry-content")
        or soup.select_one("article")
        or soup.select_one("div.entry-content")
        or soup
    )

    paragraphs = []
    for p in content_block.find_all("p"):
        text = p.get_text(" ", strip=True)
        if not text:
            continue
        if text.lower().startswith("advertisement"):
            continue
        paragraphs.append(text)

    full_text = "\n\n".join(paragraphs) if paragraphs else None
    short_description = paragraphs[0] if paragraphs else None

    # --- Author + date (fallback from text) ---
    author, date_str = _ds_extract_author_and_date_from_text(soup)

    return {
        "article_title": article_title,
        "short_description": short_description,
        "article_image_url": article_image_url,
        "author": author,
        "date": date_str,
        "full_text": full_text,
    }


def scrape_dainik_statesman_binodan_with_articles():
    """
    Entry function for Dainik Statesman:
      1. Scrape listing/cards
      2. For each card, scrape article details
    """
    cards = scrape_dainik_statesman_binodan_cards(DS_CATEGORY_URL)
    results = []

    for idx, card in enumerate(cards, start=1):
        url = card.get("article_url")
        if not url:
            continue

        print(f"[Dainik Statesman {idx}/{len(cards)}] Fetching article: {url}")
        try:
            article_data = scrape_dainik_statesman_article(url)
        except Exception as e:
            print(f"  !! Error scraping DS article {url}: {e}")
            article_data = None

        combined = {**card, "article_details": article_data}
        results.append(combined)
        time.sleep(1)

    return results
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import time

# ==============================
#  EISAMAY ENTERTAINMENT
# ==============================

EISAMAY_BASE_URL = "https://eisamay.com"
EISAMAY_ENT_CATEGORY_URL = "https://eisamay.com/entertainment"


def _fix_protocol(src: str) -> str:
    """
    Eisamay uses protocol-relative URLs like //media.assettype.com/...
    This normalizes them to https://...
    """
    src = (src or "").strip()
    if not src:
        return ""
    if src.startswith("//"):
        return "https:" + src
    return src


def scrape_eisamay_entertainment_cards(url: str):
    """
    Scrape Eisamay 'Entertainment' listing page and return basic card info.

    We DON'T hardcode the different wrapper blocks.
    We simply grab all story cards:

      <div data-test-id="story-card" ...>
        <a data-test-id="arr--hero-image" href="ARTICLE_URL">
          <img src="IMAGE_URL" ...>
        </a>
        ...
        <div data-test-id="headline">
          <a><h2/h6>HEADLINE</h2/h6></a>
        </div>
        <div data-test-id="subheadline">SUBHEADLINE</div>
      </div>
    """
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    cards_data = []
    seen_urls = set()

    for card in soup.select('[data-test-id="story-card"]'):
        # --- Article URL ---
        hero_link = card.select_one('[data-test-id="arr--hero-image"]') or card.find("a", href=True)
        if not hero_link:
            continue

        href = (hero_link.get("href") or "").strip()
        if not href:
            continue

        article_url = urljoin(EISAMAY_BASE_URL, href)
        if article_url in seen_urls:
            continue

        # --- Image URL ---
        img_tag = hero_link.select_one("img")
        card_image_url = ""
        if img_tag:
            img_src = img_tag.get("src") or img_tag.get("data-src")
            if img_src:
                card_image_url = _fix_protocol(img_src)

        # --- Headline (h2 for lead, h6 for others) ---
        headline_tag = (
            card.select_one('[data-test-id="headline"] h2') or
            card.select_one('[data-test-id="headline"] h6') or
            card.select_one('[data-test-id="headline"]')
        )
        title_text = headline_tag.get_text(" ", strip=True) if headline_tag else None

        # --- Subheadline (short summary on listing) ---
        subheadline_tag = card.select_one('[data-test-id="subheadline"]')
        subheadline = subheadline_tag.get_text(" ", strip=True) if subheadline_tag else None

        cards_data.append({
            "title": title_text,
            "article_url": article_url,
            "card_image_url": card_image_url,
            "listing_subheadline": subheadline,
        })
        seen_urls.add(article_url)

    return cards_data


def _eisamay_extract_author_and_date(soup: BeautifulSoup):
    """
    Best-effort extraction of author + published date from the article page.

    Layouts can change, so we try multiple patterns and fall back gracefully.
    """
    author = None
    date_str = None

    # Typical modern layouts often have explicit author / timestamp containers.
    author_tag = (
        soup.select_one("[data-test-id='author-name']") or
        soup.select_one(".author-name") or
        soup.select_one(".author")
    )
    if author_tag:
        author = author_tag.get_text(" ", strip=True)

    time_tag = (
        soup.select_one("time") or
        soup.select_one("[data-test-id='timestamp']") or
        soup.select_one("span.time") or
        soup.select_one("span.date")
    )
    if time_tag:
        # Prefer machine-readable datetime if available
        date_str = time_tag.get("datetime") or time_tag.get_text(" ", strip=True)

    return author, date_str


def scrape_eisamay_article(article_url: str):
    """
    Scrape a single Eisamay entertainment article page.

    Returns:
      {
        "article_title": ...,
        "short_description": ...,
        "article_image_url": ...,
        "author": ...,
        "date": ...,
        "full_text": ...,
      }
    """
    resp = requests.get(article_url, headers=HEADERS, timeout=10)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # --- Title ---
    title_tag = (
        soup.select_one("h1.headline-m_headline__3_NhV") or
        soup.find("h1") or
        soup.find("title")
    )
    article_title = title_tag.get_text(" ", strip=True) if title_tag else None

    # --- Author + date ---
    author, date_str = _eisamay_extract_author_and_date(soup)

    # --- Main article image ---
    # Try hero image first, then any main content image
    img_tag = (
        soup.select_one("[data-test-id='arr--hero-image'] img") or
        soup.select_one("figure img.qt-image") or
        soup.find("img")
    )
    article_image_url = None
    if img_tag:
        img_src = img_tag.get("src") or img_tag.get("data-src")
        if img_src:
            article_image_url = _fix_protocol(img_src)

    # --- Article body text ---
    # Eisamay (Assettype) typically wraps body in a specific container; we try a few.
    content_block = (
        soup.select_one("[data-test-id='article-body']") or
        soup.select_one("div.article-body") or
        soup.select_one("article") or
        soup
    )

    paragraphs = []
    for p in content_block.find_all("p"):
        text = p.get_text(" ", strip=True)
        if not text:
            continue
        # Basic ad/boilerplate filter (adjust if you see junk in output)
        if text.lower().startswith("advertisement"):
            continue
        paragraphs.append(text)

    full_text = "\n\n".join(paragraphs) if paragraphs else None
    short_description = paragraphs[0] if paragraphs else None

    return {
        "article_title": article_title,
        "short_description": short_description,
        "article_image_url": article_image_url,
        "author": author,
        "date": date_str,
        "full_text": full_text,
    }


def scrape_eisamay_entertainment_with_articles():
    """
    Entry function for Eisamay Entertainment:
      1. Scrape listing/cards
      2. For each card, scrape article details
    """
    cards = scrape_eisamay_entertainment_cards(EISAMAY_ENT_CATEGORY_URL)
    results = []

    for idx, card in enumerate(cards, start=1):
        url = card.get("article_url")
        if not url:
            continue

        print(f"[Eisamay {idx}/{len(cards)}] Fetching article: {url}")
        try:
            article_data = scrape_eisamay_article(url)

        except Exception as e:
            print(f"  !! Error scraping Eisamay article {url}: {e}")
            article_data = None

        combined = {**card, "article_details": article_data}
        results.append(combined)
        time.sleep(1)

    return results


# ==============================
#  DEMO / TEST
# ==============================
if __name__ == "__main__":
    print(">>> EISAMAY ENTERTAINMENT")
    es_data = scrape_eisamay_entertainment_with_articles()
    for item in es_data[:5]:
        print("=" * 80)
        print("CARD TITLE:", item["title"])
        print("ARTICLE URL:", item["article_url"])
        if item["article_details"]:
            det = item["article_details"]
            print("ARTICLE TITLE:", det["article_title"])
            print("AUTHOR:", det["author"])
            print("DATE:", det["date"])
            print("SHORT DESC:", det["short_description"])
            full = det["full_text"] or ""
            print("FULL TEXT :", full)

    print(">>> BARTAMAN BINODON")
    bartaman_data = scrape_bartaman_binodon_with_articles()
    for item in bartaman_data[:3]:
        print("=" * 80)
        print("CARD TITLE:", item["title"])
        print("ARTICLE URL:", item["article_url"])
        if item["article_details"]:
            print("ARTICLE TITLE:", item["article_details"]["article_title"])
            print("AUTHOR:", item["article_details"]["author"])
            print("DATE:", item["article_details"]["date"])
            print("SHORT DESC:", item["article_details"]["short_description"])
            full = item["article_details"]["full_text"] or ""
            print("FULL TEXT :", full)

    print("\n>>> DAINIK STATESMAN BINODAN")
    ds_data = scrape_dainik_statesman_binodan_with_articles()
    for item in ds_data[:3]:
        print("=" * 80)
        print("CARD TITLE:", item["title"])
        print("ARTICLE URL:", item["article_url"])
        if item["article_details"]:
            print("ARTICLE TITLE:", item["article_details"]["article_title"])
            print("AUTHOR:", item["article_details"]["author"])
            print("DATE:", item["article_details"]["date"])
            print("SHORT DESC:", item["article_details"]["short_description"])
            full = item["article_details"]["full_text"] or ""
            print("FULL TEXT :", full)

