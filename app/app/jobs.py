from __future__ import annotations

import asyncio
import logging
from typing import Any

from . import config, db
from .analyzer import sanitize_finding
from .backup import backup_db
from .claims import apply_promise_status, match_claims
from .scoreboard import refresh_scoreboard
from .collectors import (
    collect_ckan_datasets,
    collect_contracts,
    collect_lobbying,
    collect_mandate_claims,
    collect_openparliament,
    collect_search,
    enrich,
)
from .llm import analyze_story, model_ready
from .countries import normalize as norm_country, profile as country_profile
from .util import looks_like_junk_title

log = logging.getLogger("cpl.jobs")
_scan_lock = asyncio.Lock()


def scan_busy() -> bool:
    return _scan_lock.locked()


async def ensure_model() -> str:
    ready, detail = await model_ready()
    if ready:
        return f"ready:{detail}"
    return f"missing:{detail}"


def _store_extracted(scan_id: int, raw: dict[str, Any], country: str = "CA") -> int | None:
    raw = dict(raw)
    raw["country"] = country
    clean = sanitize_finding(raw)
    if not clean:
        return None
    fid, _ = db.upsert_finding(scan_id, clean)
    event = raw.get("money_event")
    if event:
        event = dict(event)
        event["country"] = country
        db.insert_money_event(scan_id, fid, event)
    return fid


async def run_scan(reason: str = "scheduled", country: str = "CA") -> dict[str, Any]:
    if _scan_lock.locked():
        return {"status": "busy"}
    country = norm_country(country)
    structured = country_profile(country)["structured"]
    async with _scan_lock:
        scan_id = db.start_scan(reason, country=country)
        queries = 0
        hit_count = 0
        finding_count = 0
        try:
            db.quarantine_junk()
            model_state = await ensure_model()

            stored_claims: list = []
            parl: list = []
            ckan: list = []
            contract_hits: list = []
            contract_findings: list = []
            lobby_hits: list = []
            lobby_findings: list = []
            if structured:
                mandate = await collect_mandate_claims()
                for claim in mandate:
                    db.upsert_claim(claim)
                stored_claims = db.list_claims(limit=250)
                parl = await collect_openparliament()
                ckan = await collect_ckan_datasets()
                contract_hits, contract_findings = await collect_contracts()
                lobby_hits, lobby_findings = await collect_lobbying()

            search_hits = await collect_search(scan_id, country=country)
            queries = len({h["query"] for h in search_hits})

            all_hits = search_hits + parl + ckan + contract_hits + lobby_hits
            changed: list[dict[str, Any]] = []
            for hit in all_hits:
                if looks_like_junk_title(hit.get("title") or ""):
                    continue
                hit["country"] = country
                _, is_new = db.upsert_hit(scan_id, hit)
                hit_count += 1
                if is_new or hit.get("kind") == "official":
                    changed.append(hit)

            for raw in contract_findings + lobby_findings:
                if _store_extracted(scan_id, raw, country=country):
                    finding_count += 1

            if structured:
                for vendor, lobbyist in db.overlapping_money_actors():
                    page = "https://open.canada.ca/data/en/dataset/" + config.LOBBY_PACKAGE_ID
                    joined = {
                        "title": f"{vendor} appears in federal contracts and lobbying reports",
                        "category": "finance",
                        "summary": (
                            f"{vendor} is listed as a contract vendor in proactive disclosure "
                            f"and as {lobbyist} in the Registry of Lobbyists."
                        ),
                        "claim": f"{vendor} is both a federal vendor and a registered lobbying actor.",
                        "evidence": "Name match across Open Canada contracts datastore and lobbying monthly reports.",
                        "entities": [vendor, lobbyist],
                        "money": {"amount": None, "currency": "CAD"},
                        "promise_status": "n/a",
                        "confidence": 0.7,
                        "severity": "medium",
                        "sources": [
                            {"url": "https://search.open.canada.ca/contracts/", "title": "Search Government Contracts"},
                            {"url": page, "title": "Monthly Communication Reports"},
                        ],
                        "origin": "extracted",
                        "review_status": "pending",
                        "language": "en",
                    }
                    if _store_extracted(scan_id, joined, country=country):
                        finding_count += 1

            to_fetch = [h for h in changed if h.get("kind") == "official"][: config.FETCH_MAX_OFFICIAL]
            news = [h for h in changed if h.get("kind") == "news"][:12]
            enriched = await enrich(to_fetch + news, max_fetch=config.FETCH_MAX_OFFICIAL)

            stories = []
            seen_url: set[str] = set()
            for hit in enriched:
                url = hit.get("url")
                if not url or url in seen_url or looks_like_junk_title(hit.get("title") or ""):
                    continue
                seen_url.add(url)
                stories.append(hit)
            stories = stories[: config.LLM_MAX_STORIES]

            if structured:
                finding_count += refresh_scoreboard(scan_id, extra=parl + contract_hits)

            for doc in stories:
                raw_findings = await analyze_story(doc, stored_claims)
                allowed = {doc.get("url")}
                for raw in raw_findings:
                    raw["country"] = country
                    clean = sanitize_finding(raw, allowed_urls=allowed)
                    if not clean:
                        continue
                    related = match_claims(clean, stored_claims)
                    matched_full = [
                        c
                        for cid, _score, _note in related
                        for c in stored_claims
                        if int(c["id"]) == cid
                    ]
                    clean = apply_promise_status(clean, matched_full)
                    fid, inserted = db.upsert_finding(scan_id, clean)
                    if inserted:
                        finding_count += 1
                    for cid, score, note in related:
                        db.link_claim(cid, fid, score, note)

            db.finish_scan(scan_id, "ok", queries, hit_count, finding_count)
            backup_db()
            return {
                "status": "ok",
                "scan_id": scan_id,
                "queries": queries,
                "hits": hit_count,
                "findings": finding_count,
                "model": model_state,
            }
        except Exception as exc:
            log.exception("scan failed")
            db.finish_scan(scan_id, "error", queries, hit_count, finding_count, str(exc))
            return {"status": "error", "scan_id": scan_id, "error": str(exc)}
