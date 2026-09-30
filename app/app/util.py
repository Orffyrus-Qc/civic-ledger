from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Any


def lang_text(val: Any, lang: str = "en") -> str:
    if val is None:
        return ""
    if isinstance(val, dict):
        return str(
            val.get(lang) or val.get("en") or val.get("fr") or next(iter(val.values()), "") or ""
        ).strip()
    return str(val).strip()


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return (s or "entity")[:80]


def content_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", "ignore")).hexdigest()[:16]


_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def parse_date(raw: Any) -> str | None:
    if not raw:
        return None
    text = str(raw).strip()
    iso = re.search(r"(20\d{2}-\d{2}-\d{2})", text)
    if iso:
        return iso.group(1)
    named = re.search(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2}),?\s*(20\d{2})",
        text,
        re.I,
    )
    if named:
        month = _MONTHS[named.group(1).lower()]
        return f"{named.group(3)}-{month:02d}-{int(named.group(2)):02d}"
    for fmt, slen in (("%m/%d/%Y", 10), ("%d/%m/%Y", 10), ("%Y/%m/%d", 10)):
        try:
            return datetime.strptime(text[:slen], fmt).date().isoformat()
        except ValueError:
            continue
    year = re.search(r"(20\d{2})", text)
    if year:
        return year.group(1) + "-01-01"
    return None


def looks_like_junk_title(title: str) -> bool:
    t = (title or "").strip()
    if not t or len(t) < 8 or t.isdigit():
        return True
    low = t.lower()
    if low in {
        "home",
        "home - canada.ca",
        "canada.ca",
        "open government",
        "search",
        "accueil",
        "canada - wikipédia",
        "canada - wikipedia",
        "wikipedia",
    }:
        return True
    junk_bits = (
        "tsx composite",
        "stock quote",
        "quote - the globe",
        "pro forma bill",
        "administration of oaths",
        "prestation de serments",
        "wikipédia",
        "wikipedia",
        "white house claims about canada",
        "communication reports available",
        "proactive disclosure of contracts",
        "proactive publication - contracts",
        "proactive publication of contracts",
        "quarterly financial transactions return",
        "limited public access to contract",
        "open government portal",
        "asset declaration",
        "lobbying communication reports",
    )
    if any(bit in low for bit in junk_bits):
        if low.startswith("federal contract:"):
            return False
        return True
    return False
