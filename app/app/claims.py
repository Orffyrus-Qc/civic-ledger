from __future__ import annotations

import re
from typing import Any

def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]{4,}", (text or "").lower()) if w not in {"canada", "canadian", "government"}}


def match_claims(finding: dict[str, Any], claims: list[dict[str, Any]], limit: int = 3) -> list[tuple[int, float, str]]:
    blob = _tokens(
        " ".join(
            [
                finding.get("title") or "",
                finding.get("summary") or "",
                finding.get("claim") or "",
            ]
        )
    )
    if not blob:
        return []
    scored: list[tuple[int, float, str]] = []
    for claim in claims:
        ct = _tokens((claim.get("title") or "") + " " + (claim.get("body") or ""))
        if not ct:
            continue
        overlap = blob & ct
        if len(overlap) < 3:
            continue
        score = len(overlap) / max(len(ct), 1)
        if score >= 0.08:
            scored.append((int(claim["id"]), min(1.0, score), ", ".join(sorted(overlap)[:6])))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def apply_promise_status(finding: dict[str, Any], matched: list[dict[str, Any]]) -> dict[str, Any]:
    if finding.get("category") != "promise" and not matched:
        return finding
    if not matched:
        return finding
    statuses = {m.get("status") for m in matched}
    if "broken" in statuses:
        finding["promise_status"] = "broken"
    elif "kept" in statuses and "partial" not in statuses:
        finding["promise_status"] = "kept"
    elif "partial" in statuses or "kept" in statuses:
        finding["promise_status"] = "partial"
    return finding
