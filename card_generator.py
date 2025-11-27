# card_generator.py
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import datetime

CARD_SIZE = (1080, 1080)
PADDING = 80
OUTPUT_DIR = Path("cards")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# update to a font that exists on your system and supports Bangla
FONT_PATH = "C:/Windows/Fonts/arial.ttf"
TITLE_FONT_SIZE = 60
META_FONT_SIZE = 36

def _wrap_text(text, font, max_width):
    words = text.split()
    lines = []
    current = []

    for w in words:
        test = " ".join(current + [w])
        w_width, _ = font.getsize(test)
        if w_width <= max_width:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines

def create_card(title: str, source: str = "", date_str: str = "") -> str:
    img = Image.new("RGB", CARD_SIZE, (10, 10, 10))
    draw = ImageDraw.Draw(img)

    title_font = ImageFont.truetype(FONT_PATH, TITLE_FONT_SIZE)
    meta_font = ImageFont.truetype(FONT_PATH, META_FONT_SIZE)

    max_width = CARD_SIZE[0] - 2 * PADDING
    title_lines = _wrap_text(title, title_font, max_width)

    y = PADDING
    for line in title_lines:
        draw.text((PADDING, y), line, font=title_font, fill=(255, 255, 255))
        y += title_font.getsize(line)[1] + 10

    if not date_str:
        date_str = datetime.datetime.utcnow().strftime("%d %b %Y")

    meta_text = f"{source} • {date_str}" if source else date_str
    meta_y = CARD_SIZE[1] - PADDING - META_FONT_SIZE*2

    draw.text((PADDING, meta_y), meta_text, font=meta_font, fill=(200, 200, 200))

    fname = datetime.datetime.utcnow().strftime("card_%Y%m%d_%H%M%S.png")
    out_path = OUTPUT_DIR / fname
    img.save(out_path, "PNG")
    return str(out_path)
