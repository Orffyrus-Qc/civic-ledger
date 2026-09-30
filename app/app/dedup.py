from __future__ import annotations

import re
from typing import Any

from .util import slugify

_STOP = {
    "the",
    "of",
    "and",
    "for",
    "a",
    "an",
    "to",
    "in",
    "on",
    "now",
    "available",
    "canada",
    "canadian",
}


def normalize_title(title: str) -> str:
    words = re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).split()
    keep = [w for w in words if w not in _STOP and not re.fullmatch(r"20\d{2}", w)]
    return " ".join(keep[:12])


def canonical_key(item: dict[str, Any]) -> str:
    title = normalize_title(str(item.get("title") or ""))
    cat = str(item.get("category") or "other")
    ents = item.get("entities") or []
    entity = ""
    if isinstance(ents, list) and ents:
        entity = slugify(str(ents[0]))
    elif isinstance(ents, str):
        entity = slugify(ents)
    if not title:
        url = ""
        srcs = item.get("sources") or []
        if srcs and isinstance(srcs, list):
            url = str(srcs[0].get("url") or "")
        title = slugify(url)
    cc = str(item.get("country") or "CA").upper()
    return f"{cc}:{cat}:{title}:{entity}"[:180]
