from __future__ import annotations

from typing import Any

from .dedup import canonical_key
from .money import format_cad, parse_amount
from .privacy import looks_like_dox, redact_text
from .sources import is_allowed, source_kind
from .util import looks_like_junk_title, parse_date

CATEGORIES = {
    "finance",
    "promise",
    "contradiction",
    "lobbying",
    "contract",
    "ethics",
    "other",
}


def cap_confidence(origin: str, amount: float | None, source_date: str | None, raw: float) -> float:
    raw = max(0.0, min(1.0, raw))
    if origin == "extracted" and amount is not None and source_date:
        return min(raw, 0.95)
    if origin == "extracted":
        return min(raw, 0.8)
    if amount is not None and source_date:
        return min(raw, 0.75)
    return min(raw, 0.55)


def sanitize_finding(item: dict[str, Any], allowed_urls: set[str] | None = None) -> dict[str, Any] | None:
    title = redact_text(str(item.get("title") or "")).strip()
    summary = redact_text(str(item.get("summary") or "")).strip()
    if not title or not summary:
        return None
    if looks_like_junk_title(title):
        return None
    blob = " ".join([title, summary, str(item.get("claim") or ""), str(item.get("evidence") or "")])
    if looks_like_dox(blob):
        return None
    category = str(item.get("category") or "other").lower().strip()
    if category not in CATEGORIES:
        category = "other"
    if category == "contradiction":
        # Same-official two dated statements only. Drop foreign colour / generic "intelligence".
        low = blob.lower()
        if "white house" in low or "u.s. president" in low or "trump" in low:
            if "minister" not in low and "ottawa" not in low:
                return None
    severity = str(item.get("severity") or "medium").lower()
    if severity not in {"low", "medium", "high"}:
        severity = "medium"
    status = str(item.get("promise_status") or "n/a").lower()
    if status not in {"kept", "broken", "partial", "unverified", "n/a"}:
        status = "n/a"
    origin = str(item.get("origin") or "model")
    if origin not in {"extracted", "model", "official"}:
        origin = "model"
    try:
        confidence = float(item.get("confidence") or 0.4)
    except (TypeError, ValueError):
        confidence = 0.4
    entities = item.get("entities") or []
    if not isinstance(entities, list):
        entities = [str(entities)]
    entities = [redact_text(str(e))[:80] for e in entities if str(e).strip()][:12]
    money = item.get("money") if isinstance(item.get("money"), dict) else {}
    amount = item.get("money_amount")
    if amount is None:
        amount = parse_amount(money.get("amount"))
    source_date = item.get("source_date") or parse_date(summary) or parse_date(item.get("claim"))
    confidence = cap_confidence(origin, amount, source_date, confidence)
    sources = []
    for src in item.get("sources") or []:
        if not isinstance(src, dict):
            continue
        url = str(src.get("url") or "").strip()
        country = item.get("country")
        if not url or not is_allowed(url, country):
            continue
        if allowed_urls is not None and url not in allowed_urls:
            continue
        sources.append(
            {
                "url": url,
                "title": redact_text(str(src.get("title") or ""))[:200],
                "kind": source_kind(url, country),
            }
        )
    if not sources:
        return None
    review = item.get("review_status") or ("confirmed" if origin == "extracted" and amount and source_date else "pending")
    out = {
        "title": title[:240],
        "category": category,
        "summary": summary[:2000],
        "claim": redact_text(str(item.get("claim") or ""))[:1200],
        "evidence": redact_text(str(item.get("evidence") or ""))[:2000],
        "entities": entities,
        "money": {
            "amount": format_cad(amount) if amount is not None else (redact_text(str(money.get("amount") or ""))[:80] or None),
            "currency": str(money.get("currency") or "CAD")[:8],
        },
        "money_amount": amount,
        "promise_status": status,
        "confidence": confidence,
        "severity": severity,
        "sources": sources,
        "origin": origin,
        "review_status": review,
        "source_date": source_date,
        "language": item.get("language") or "en",
        "country": item.get("country") or "CA",
        "hidden": 0,
    }
    out["canonical_key"] = canonical_key(out)
    if item.get("money_event"):
        out["money_event"] = item["money_event"]
    return out
