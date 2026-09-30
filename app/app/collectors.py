from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from . import config
from .countries import search_jobs as country_search_jobs
from .lobby_dump import is_zip_bytes, parse_lobby_zip
from .mandate import (
    parse_carney_mandate_html,
    parse_carney_tracker,
    parse_pco_csv,
    parse_xlsx_commitments,
)
from .money import format_cad, parse_amount
from .privacy import redact_text
from .search_client import fetch_text, searx_search
from .util import content_hash, lang_text, looks_like_junk_title, parse_date

log = logging.getLogger("cpl.collect")

SEARCH_POOL: list[dict[str, str]] = [
    {"id": "finance-elections", "category": "finance", "lang": "en",
     "query": "site:elections.ca political financing quarterly returns party"},
    {"id": "finance-elections-fr", "category": "finance", "lang": "fr",
     "query": "site:elections.ca financement politique rapports trimestriels parti"},
    {"id": "finance-open", "category": "finance", "lang": "en",
     "query": "site:open.canada.ca political financing OR government contracts proactive disclosure"},
    {"id": "lobbying", "category": "lobbying", "lang": "en",
     "query": "site:lobbycanada.gc.ca communication report OR monthly return"},
    {"id": "lobbying-fr", "category": "lobbying", "lang": "fr",
     "query": "site:lobbycanada.gc.ca rapport de communication mensuel"},
    {"id": "contracts", "category": "contract", "lang": "en",
     "query": "Canada federal contracts canadabuys proactive disclosure 2025 2026"},
    {"id": "ethics", "category": "ethics", "lang": "en",
     "query": "site:ciec-ccie.parl.gc.ca public declaration conflict of interest"},
    {"id": "promises", "category": "promise", "lang": "en",
     "query": "Canada federal campaign promise tracker kept broken 2025 2026"},
    {"id": "promises-fr", "category": "promise", "lang": "fr",
     "query": "promesse électorale brisée tenue Canada 2025 2026 site:ici.radio-canada.ca OR site:ledevoir.com"},
    {"id": "mandate", "category": "promise", "lang": "en",
     "query": "Canada mandate letter tracker ministers results site:canada.ca OR site:cbc.ca"},
    {"id": "contradiction", "category": "contradiction", "lang": "en",
     "query": "Canada minister contradicts earlier statement fact check 2025 2026"},
    {"id": "contradiction-fr", "category": "contradiction", "lang": "fr",
     "query": "ministre contredit déclaration fact check 2025 2026 site:ici.radio-canada.ca"},
    {"id": "money-news", "category": "finance", "lang": "en",
     "query": "Canadian political donations lobbying contracts investigation CBC Globe 2025 2026"},
    {"id": "qc-finance", "category": "finance", "lang": "fr",
     "query": "dons politiques Québec DGEQ lobbying contrat site:ledevoir.com OR site:lapresse.ca"},
    {"id": "on-finance", "category": "finance", "lang": "en",
     "query": "Ontario political donations lobbying Integrity Commissioner 2025 2026"},
    {"id": "pbo", "category": "finance", "lang": "en",
     "query": "site:pbo-dpb.ca cost estimate government spending 2025 2026"},
]


def rotate_search_jobs(
    scan_id: int, take: int = 6, country: str = "CA"
) -> list[dict[str, str]]:
    pool = country_search_jobs(country)
    if not pool:
        return []
    start = (max(scan_id, 1) - 1) * 3 % len(pool)
    out = []
    for i in range(take):
        out.append(pool[(start + i) % len(pool)])
    return out


def _headers() -> dict[str, str]:
    return {"User-Agent": config.USER_AGENT, "Accept": "application/json,text/csv,*/*"}


def _hit(
    title: str,
    url: str,
    snippet: str,
    engine: str,
    kind: str,
    query: str,
    topic: str,
    category: str,
    text: str = "",
    source_date: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    title = redact_text(title)[:300]
    snippet = redact_text(snippet)[:800]
    body = redact_text(text or snippet)
    item = {
        "title": title,
        "url": url,
        "snippet": snippet,
        "engine": engine,
        "kind": kind,
        "query": query,
        "topic": topic,
        "category_hint": category,
        "text": body[: config.FETCH_MAX_CHARS],
        "content_hash": content_hash(body),
        "source_date": source_date,
    }
    if extra:
        item.update(extra)
    return item


async def collect_search(scan_id: int, country: str = "CA") -> list[dict[str, Any]]:
    jobs = rotate_search_jobs(scan_id, country=country)
    collected: list[dict[str, Any]] = []
    for job in jobs:
        lang = "fr-CA" if job.get("lang") == "fr" else "en-CA"
        hits = await searx_search(job["query"], pages=1, language=lang, country=country)
        for hit in hits[:8]:
            if looks_like_junk_title(hit.get("title") or ""):
                continue
            hit["topic"] = job["id"]
            hit["category_hint"] = job["category"]
            hit["language"] = job.get("lang") or "en"
            hit["country"] = country
            hit["content_hash"] = content_hash(hit.get("snippet") or "")
            collected.append(hit)
    return collected


async def enrich(hits: list[dict[str, Any]], max_fetch: int | None = None) -> list[dict[str, Any]]:
    budget = max_fetch or config.FETCH_MAX_OFFICIAL
    out: list[dict[str, Any]] = []
    fetched = 0
    for hit in hits:
        item = dict(hit)
        if fetched < budget and item.get("kind") == "official" and not item.get("skip_fetch"):
            text = await fetch_text(item["url"])
            if text:
                item["text"] = text
                item["content_hash"] = content_hash(text)
                fetched += 1
        else:
            item.setdefault("text", item.get("snippet") or "")
            item.setdefault("content_hash", content_hash(item.get("text") or ""))
        out.append(item)
    return out


async def collect_openparliament() -> list[dict[str, Any]]:
    docs: list[dict[str, Any]] = []
    session = config.PARLIAMENT_SESSION
    endpoints = [
        (f"https://api.openparliament.ca/bills/?session={session}&format=json&limit=20", "bills"),
        ("https://api.openparliament.ca/votes/?format=json&limit=20", "votes"),
        ("https://api.openparliament.ca/debates/?format=json&limit=5", "debates"),
    ]
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT, headers=_headers(), follow_redirects=True) as client:
        for url, kind in endpoints:
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                payload = resp.json()
            except Exception as exc:
                log.warning("openparliament %s failed: %s", kind, exc)
                continue
            for obj in payload.get("objects") or []:
                number = str(obj.get("number") or "")
                if kind == "bills" and number.upper() in {"C-1", "S-1"}:
                    continue
                if kind == "bills":
                    name = lang_text(obj.get("name"))
                    title = f"Bill {number}: {name}".strip(": ")
                    snippet = f"Introduced {obj.get('introduced') or ''} session {obj.get('session') or ''}"
                    source_date = parse_date(obj.get("introduced"))
                    category = "promise"
                elif kind == "votes":
                    desc = lang_text(obj.get("description"))
                    title = desc or f"Vote {obj.get('number')} session {obj.get('session')}"
                    snippet = (
                        f"Result {obj.get('result')}; yea {obj.get('yea_total')} nay {obj.get('nay_total')}"
                    )
                    source_date = parse_date(obj.get("date"))
                    category = "promise"
                else:
                    title = lang_text(obj.get("date") or obj.get("number") or "Debate")
                    if obj.get("date"):
                        title = f"House debate {obj.get('date')}"
                    snippet = lang_text(obj.get("most_frequent_word") or "")
                    source_date = parse_date(obj.get("date"))
                    category = "other"
                if looks_like_junk_title(title):
                    continue
                href = obj.get("url") or ""
                if href.startswith("/"):
                    href = "https://openparliament.ca" + href
                if not href:
                    continue
                docs.append(
                    _hit(
                        title,
                        href,
                        snippet,
                        "openparliament",
                        "official",
                        f"openparliament:{kind}",
                        f"openparliament-{kind}",
                        category,
                        text=redact_text(str(obj)),
                        source_date=source_date,
                        extra={"skip_fetch": True, "language": "en"},
                    )
                )
    return docs


async def collect_contracts() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return (hits, extracted findings-shaped dicts with money)."""
    url = (
        "https://open.canada.ca/data/en/api/3/action/datastore_search"
        f"?resource_id={config.CONTRACTS_RESOURCE_ID}&limit=20&sort=contract_date%20desc"
    )
    hits: list[dict[str, Any]] = []
    extracted: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT, headers=_headers(), follow_redirects=True) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            records = (resp.json().get("result") or {}).get("records") or []
        except Exception as exc:
            log.warning("contracts datastore failed: %s", exc)
            return hits, extracted
    portal = "https://search.open.canada.ca/contracts/"
    for rec in records:
        vendor = redact_text(str(rec.get("vendor_name") or "Unknown vendor"))
        desc = redact_text(lang_text({"en": rec.get("description_en"), "fr": rec.get("description_fr")}))
        amount = parse_amount(rec.get("contract_value"))
        date = parse_date(rec.get("contract_date"))
        if amount is not None and amount <= 0:
            continue
        ref = rec.get("reference_number") or rec.get("procurement_id") or ""
        page = f"{portal}?q={ref}" if ref else portal
        title = f"Federal contract: {vendor} — {format_cad(amount) or 'undisclosed'}"
        snippet = f"{desc}. Buyer {redact_text(str(rec.get('buyer_name') or 'n/a'))}. Date {date or 'n/a'}."
        hit = _hit(
            title,
            page,
            snippet,
            "open-canada-datastore",
            "official",
            "contracts-datastore",
            "contracts",
            "contract",
            text=snippet,
            source_date=date,
            extra={"skip_fetch": True},
        )
        hits.append(hit)
        extracted.append(
            {
                "title": title,
                "category": "contract",
                "summary": snippet,
                "claim": f"{vendor} received a disclosed federal contract.",
                "evidence": snippet,
                "entities": [vendor, "Government of Canada"],
                "money": {"amount": format_cad(amount), "currency": "CAD"},
                "money_amount": amount,
                "promise_status": "n/a",
                "confidence": 0.9 if amount and date else 0.7,
                "severity": "medium" if (amount or 0) >= 100_000 else "low",
                "sources": [{"url": page, "title": f"Contract {ref}"}],
                "origin": "extracted",
                "review_status": "confirmed" if amount and date else "pending",
                "source_date": date,
                "language": "en",
                "money_event": {
                    "role": "vendor",
                    "actor": vendor,
                    "counterpart": "Government of Canada",
                    "amount": amount,
                    "currency": "CAD",
                    "event_date": date,
                    "source_url": page,
                },
            }
        )
    return hits, extracted


def _lobby_cache_path() -> Path:
    return config.CACHE_DIR / "communications_ocl_cal.zip"


def _cache_fresh(path: Path, days: int = 7) -> bool:
    if not path.exists() or path.stat().st_size < 1000:
        return False
    age = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
    return age < days * 86400


async def _fetch_zip(client: httpx.AsyncClient, url: str) -> bytes | None:
    headers = {
        "User-Agent": config.BROWSER_UA,
        "Accept": "application/zip,application/octet-stream,*/*",
        "Referer": "https://open.canada.ca/data/en/dataset/" + config.LOBBY_PACKAGE_ID,
    }
    try:
        resp = await client.get(url, headers=headers, timeout=180)
    except Exception as exc:
        log.warning("lobby zip fetch %s failed: %s", url, exc)
        return None
    if resp.status_code != 200 or not is_zip_bytes(resp.content):
        log.warning("lobby zip %s status=%s bytes=%s", url, resp.status_code, len(resp.content))
        return None
    return resp.content


async def download_lobby_zip(client: httpx.AsyncClient) -> bytes | None:
    """Live lobbycanada.gc.ca is behind Cloudflare. Prefer cache, then Wayback."""
    cache = _lobby_cache_path()
    cache.parent.mkdir(parents=True, exist_ok=True)
    def _save(blob: bytes) -> None:
        try:
            cache.write_bytes(blob)
        except OSError as exc:
            log.warning("lobby cache write failed: %s", exc)

    blob = await _fetch_zip(client, config.LOBBY_ZIP_URL)
    if blob:
        _save(blob)
        return blob
    if _cache_fresh(cache):
        log.info("using cached lobby zip (%s bytes)", cache.stat().st_size)
        return cache.read_bytes()
    blob = await _fetch_zip(client, config.LOBBY_ZIP_WAYBACK)
    if blob:
        _save(blob)
        return blob
    if cache.exists() and cache.stat().st_size > 1000:
        log.info("using stale cached lobby zip")
        return cache.read_bytes()
    return None


async def collect_lobbying() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hits: list[dict[str, Any]] = []
    extracted: list[dict[str, Any]] = []
    pkg_url = f"https://open.canada.ca/data/en/api/3/action/package_show?id={config.LOBBY_PACKAGE_ID}"
    page = f"https://open.canada.ca/data/en/dataset/{config.LOBBY_PACKAGE_ID}"
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT, headers=_headers(), follow_redirects=True) as client:
        try:
            resp = await client.get(pkg_url)
            resp.raise_for_status()
            pkg = resp.json().get("result") or {}
        except Exception as exc:
            log.warning("lobby package_show failed: %s", exc)
            pkg = {}
        modified = parse_date(pkg.get("date_modified") or pkg.get("metadata_modified"))
        hits.append(
            _hit(
                "Monthly Communication Reports — Registry of Lobbyists",
                page,
                "Official weekly dump of federal monthly lobbying communication reports.",
                "open-canada-ckan",
                "official",
                "lobby-ckan",
                "lobbying",
                "lobbying",
                source_date=modified,
                extra={"skip_fetch": True},
            )
        )
        blob = await download_lobby_zip(client)
        if blob:
            extracted.extend(parse_lobby_zip(blob, page, limit=20))
        else:
            log.warning("lobby zip unavailable (live Cloudflare + no cache/wayback)")
    return hits, extracted


async def collect_mandate_claims() -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    async with httpx.AsyncClient(
        timeout=90,
        headers={"User-Agent": config.BROWSER_UA, "Accept": "*/*"},
        follow_redirects=True,
    ) as client:
        try:
            resp = await client.get(config.MANDATE_CSV_URL)
            resp.raise_for_status()
            claims.extend(parse_pco_csv(resp.content.decode("utf-8", "replace"), config.MANDATE_CSV_URL))
        except Exception as exc:
            log.warning("mandate csv 2015 failed: %s", exc)
        try:
            resp = await client.get(config.MANDATE_XLSX_2021_URL)
            resp.raise_for_status()
            claims.extend(
                parse_xlsx_commitments(resp.content, config.MANDATE_XLSX_2021_URL, "2021-12-16")
            )
        except Exception as exc:
            log.warning("mandate xlsx 2021 failed: %s", exc)
        try:
            resp = await client.get(config.MANDATE_LETTER_2025_URL)
            resp.raise_for_status()
            claims.extend(parse_carney_mandate_html(resp.text, config.MANDATE_LETTER_2025_URL))
        except Exception as exc:
            log.warning("carney mandate letter failed: %s", exc)
        try:
            resp = await client.get(config.CARNEY_TRACKER_JSON_URL)
            resp.raise_for_status()
            claims.extend(parse_carney_tracker(resp.json(), config.CARNEY_TRACKER_JSON_URL))
        except Exception as exc:
            log.warning("carney tracker json failed: %s", exc)
    return claims


async def collect_ckan_datasets() -> list[dict[str, Any]]:
    queries = [
        ("political financing elections canada", "finance"),
        ("proactive disclosure grants contributions", "finance"),
        ("pbo cost estimate", "finance"),
    ]
    hits: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=config.HTTP_TIMEOUT, headers=_headers(), follow_redirects=True) as client:
        for q, cat in queries:
            try:
                resp = await client.get(
                    "https://open.canada.ca/data/en/api/3/action/package_search",
                    params={"q": q, "rows": 3},
                )
                resp.raise_for_status()
                results = (resp.json().get("result") or {}).get("results") or []
            except Exception as exc:
                log.warning("ckan search %s: %s", q, exc)
                continue
            for pkg in results:
                title = lang_text(pkg.get("title_translated") or pkg.get("title"))
                if looks_like_junk_title(title):
                    continue
                pid = pkg.get("id") or pkg.get("name")
                url = f"https://open.canada.ca/data/en/dataset/{pid}"
                notes = lang_text(pkg.get("notes_translated") or pkg.get("notes"))[:500]
                hits.append(
                    _hit(
                        title,
                        url,
                        notes or "Open Government dataset.",
                        "open-canada-ckan",
                        "official",
                        f"ckan:{q}",
                        "ckan",
                        cat,
                        source_date=parse_date(pkg.get("date_modified") or pkg.get("metadata_modified")),
                        extra={"skip_fetch": True},
                    )
                )
    return hits
