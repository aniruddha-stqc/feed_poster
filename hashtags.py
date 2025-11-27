# hashtags.py
from typing import Dict, List

BASE_TAGS = ["#Tollywood", "#BanglaCinema", "#EntertainmentNews"]

SOURCE_TAG_MAP = {
    "news18": "#News18Bangla",
    "abplive": "#ABPBangla",
    "hindustantimes": "#HindustanTimesBangla",
}

def build_hashtags(item: Dict) -> List[str]:
    tags = list(BASE_TAGS)
    source = (item.get("source") or "").lower()

    for key, tag in SOURCE_TAG_MAP.items():
        if key in source:
            tags.append(tag)

    # de-dup preserve order
    seen = set()
    final = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            final.append(t)
    return final[:8]
