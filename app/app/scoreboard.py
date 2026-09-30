"""Score 2025 Carney missions and platform pledges against public bills, votes, contracts."""

from __future__ import annotations

import re
from typing import Any

from .util import parse_date

PRIORITY_KEYS: dict[int, tuple[str, ...]] = {
    1: (
        "united states",
        "trading partner",
        "tariff",
        "allies",
        "ally",
        "nato",
        "border",
        "c-2",
        "security relationship",
        "auto worker",
    ),
    2: (
        "interprovincial",
        "internal trade",
        "nation-building",
        "one canadian economy",
        "major project",
        "labour mobility",
        "c-266",
        "skilled trade",
    ),
    3: (
        "affordab",
        "cost of living",
        "bring down cost",
        "tax cut",
        "gst",
        "grocery",
        "get ahead",
    ),
    4: (
        "housing",
        "homes",
        "skilled trade",
        "labour mobility",
        "c-266",
        "build homes",
    ),
    5: (
        "armed forces",
        "sovereignty",
        "border",
        "c-2",
        "defence",
        "defense",
        "rcmp",
        "law enforcement",
        "nato",
    ),
    6: (
        "immigration",
        "talent",
        "temporary foreign",
        "asylum",
        "sustainable level",
    ),
    7: (
        "operating budget",
        "spend less",
        "fiscal anchor",
        "government operations",
        "public service",
        "spending",
        "estimates",
    ),
}

PLATFORM_KEYS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("armed forces", "defence", "defense", "nato", "rebuild"), ("armed forces", "defence", "c-2", "nato")),
    (("tariff", "auto"), ("tariff", "auto", "c-2", "united states")),
    (("housing", "homes"), ("housing", "c-266", "skilled trade")),
    (("energy superpower", "energy"), ("energy", "natural resource", "pipeline")),
    (("immigration",), ("immigration", "asylum")),
    (("cbc", "radio-canada"), ("cbc", "broadcast")),
    (("crime", "safer"), ("rcmp", "law enforcement", "border")),
    (("trade infrastructure", "diversify trade"), ("trade", "infrastructure", "port")),
    (("agrifood", "supply management"), ("agricult", "supply management")),
    (("nature", "biodiversity"), ("environment", "climate", "biodiversity")),
)


def _blob(item: dict[str, Any]) -> str:
    return " ".join(
        str(item.get(k) or "")
        for k in ("title", "summary", "snippet", "claim", "evidence", "text", "body")
    ).lower()


def _priority_num(title: str) -> int | None:
    m = re.search(r"mandate priority\s+(\d+)", title or "", re.I)
    return int(m.group(1)) if m else None


def _hit_strength(item: dict[str, Any]) -> str:
    blob = _blob(item)
    if "3rd reading" in blob or "third reading" in blob or "adoption of bill" in blob:
        if "passed" in blob or "yea" in blob:
            return "kept"
        return "partial"
    if "passed" in blob or "royal assent" in blob:
        return "partial"
    if item.get("category") == "contract" or "federal contract" in blob:
        return "partial"
    if item.get("engine") == "openparliament":
        return "partial"
    return "partial"


def _match_count(blob: str, keys: tuple[str, ...]) -> int:
    return sum(1 for k in keys if k in blob)


def best_evidence(
    claim: dict[str, Any], evidence: list[dict[str, Any]]
) -> tuple[str, dict[str, Any] | None, int]:
    """Return (status, evidence_item, hits)."""
    title = claim.get("title") or ""
    body = (claim.get("body") or "") + " " + title
    pri = _priority_num(title)
    if pri and pri in PRIORITY_KEYS:
        keys = PRIORITY_KEYS[pri]
    else:
        keys = tuple(
            w
            for w in re.findall(r"[a-z]{4,}", body.lower())
            if w
            not in {
                "canada",
                "canadian",
                "government",
                "mandate",
                "priority",
                "carney",
                "minister",
                "platform",
            }
        )[:8]
        for needles, mapped in PLATFORM_KEYS:
            if any(n in body.lower() for n in needles):
                keys = mapped
                break
    if not keys:
        return "unverified", None, 0
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    claim_title = (claim.get("title") or "").strip()
    for item in evidence:
        if (item.get("title") or "").strip() == claim_title:
            continue
        if (item.get("category") == "promise" and item.get("origin") == "extracted"):
            continue
        n = _match_count(_blob(item), keys)
        if n <= 0:
            continue
        ranked.append((n, _hit_strength(item), item))
    if not ranked:
        incoming = claim.get("status") or "unverified"
        return incoming if incoming in {"kept", "broken", "partial"} else "unverified", None, 0
    ranked.sort(key=lambda r: (r[0], 1 if r[1] == "kept" else 0), reverse=True)
    hits, strength, item = ranked[0]
    incoming = claim.get("status") or "unverified"
    if incoming == "broken":
        status = "broken"
    elif incoming == "kept" or (hits >= 2 and strength == "kept"):
        status = "kept"
    elif hits >= 1:
        status = "partial" if incoming != "kept" else "kept"
    else:
        status = incoming
    return status, item, hits


def is_homepage_card(title: str) -> bool:
    low = (title or "").lower()
    bits = (
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
    if any(b in low for b in bits):
        if low.startswith("federal contract:"):
            return False
        return True
    return False


def refresh_scoreboard(scan_id: int, extra: list[dict[str, Any]] | None = None) -> int:
    from . import db
    from .analyzer import sanitize_finding

    evidence: list[dict[str, Any]] = list(extra or [])
    for h in db.list_hits(250):
        evidence.append(h)
    for f in db.list_findings(
        hide_low=False, hide_unverified=False, hide_rejected=True, limit=300
    ):
        if (f.get("title") or "").startswith("Carney 2025 mandate"):
            continue
        if f.get("category") == "promise" and f.get("origin") == "extracted":
            continue
        srcs = f.get("sources") or []
        evidence.append(
            {
                "title": f.get("title"),
                "summary": f.get("summary"),
                "url": (srcs[0].get("url") if srcs else "") or "",
                "sources": srcs,
                "source_date": f.get("source_date"),
                "category": f.get("category"),
            }
        )
    scored = score_claims(db.list_board_claims(), evidence)
    written = 0
    for row in scored:
        cid = row.get("id")
        if not cid:
            continue
        db.update_claim_score(int(cid), row)
        if row.get("status") not in {"kept", "partial", "broken"}:
            continue
        ev_url = row.get("evidence_url") or row.get("source_url") or ""
        if not ev_url:
            continue
        raw = {
            "title": row.get("title"),
            "category": "promise",
            "summary": row.get("score_note") or row.get("body") or "",
            "claim": row.get("title"),
            "evidence": row.get("score_note") or "",
            "entities": ["Mark Carney", "Government of Canada"],
            "money": {"amount": None, "currency": "CAD"},
            "promise_status": row.get("status"),
            "confidence": 0.8 if row.get("status") == "kept" else 0.65,
            "severity": "high" if row.get("status") == "broken" else "medium",
            "sources": [
                {
                    "url": ev_url,
                    "title": row.get("evidence_title") or "Evidence",
                }
            ],
            "origin": "extracted",
            "review_status": "pending",
            "source_date": row.get("evidence_date") or row.get("source_date"),
            "language": "en",
        }
        clean = sanitize_finding(raw)
        if not clean:
            continue
        fid, inserted = db.upsert_finding(scan_id, clean)
        db.link_claim(int(cid), fid, 1.0, row.get("score_note") or "")
        if inserted:
            written += 1
    return written


def score_claims(
    claims: list[dict[str, Any]], evidence: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    out = []
    for claim in claims:
        status, item, hits = best_evidence(claim, evidence)
        ev_url = ""
        ev_title = ""
        ev_date = None
        note = "No matching bill, vote, or contract yet."
        if item:
            ev_url = item.get("url") or ""
            srcs = item.get("sources") or []
            if not ev_url and srcs:
                ev_url = (srcs[0] or {}).get("url") or ""
                ev_title = (srcs[0] or {}).get("title") or ""
            ev_title = ev_title or item.get("title") or ""
            ev_date = item.get("source_date") or parse_date(item.get("created_at"))
            note = f"{hits} keyword hit(s) on {ev_title}"
        row = dict(claim)
        row["status"] = status
        row["evidence_url"] = ev_url
        row["evidence_title"] = ev_title
        row["score_note"] = note
        row["evidence_date"] = ev_date
        out.append(row)
    return out
