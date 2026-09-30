from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, db
from .bilingual import expand_terms, glossary_other, looks_french
from .countries import list_countries, normalize as norm_country, profile as country_profile
from .jobs import ensure_model, run_scan, scan_busy
from .scoreboard import refresh_scoreboard
from .llm import model_ready, translate_query
from .search_client import searx_search
from .sources import NEWS_HOSTS, OFFICIAL_HOSTS
from .util import slugify as _slugify

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("cpl")

ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(ROOT / "templates"))
templates.env.globals["slugify"] = _slugify
scheduler = AsyncIOScheduler()


async def _boot_scan() -> None:
    try:
        await asyncio.sleep(8)
        await ensure_model()
        if db.stats().get("findings", 0) == 0:
            await run_scan("startup")
    except Exception:
        log.exception("startup scan failed")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    db.quarantine_junk()
    scheduler.add_job(
        run_scan,
        "interval",
        minutes=config.SCAN_INTERVAL_MINUTES,
        args=["interval"],
        id="cpl-scan",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    if config.SCAN_ON_START or db.stats().get("findings", 0) == 0:
        asyncio.create_task(_boot_scan())
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Canadian Political Leak", docs_url=None, redoc_url=None, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


def _page(request: Request, name: str, extra: dict | None = None, status: int = 200) -> HTMLResponse:
    ctx = {
        "request": request,
        "stats": db.stats(),
        "interval": config.SCAN_INTERVAL_MINUTES,
        "model": config.OLLAMA_MODEL,
    }
    if extra:
        ctx.update(extra)
    return templates.TemplateResponse(name, ctx, status_code=status)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return _page(request, "index.html")


@app.get("/finding/{finding_id}", response_class=HTMLResponse)
async def finding_page(request: Request, finding_id: int) -> HTMLResponse:
    item = db.get_finding(finding_id)
    if not item:
        return _page(request, "index.html", {"error": "Finding not found"}, 404)
    return _page(request, "finding.html", {"item": item})


@app.get("/entity/{slug}", response_class=HTMLResponse)
async def entity_page(request: Request, slug: str) -> HTMLResponse:
    item = db.get_entity(slug)
    if not item:
        return _page(request, "index.html", {"error": "Entity not found"}, 404)
    return _page(request, "entity.html", {"entity": item})


@app.get("/api/health")
async def health(country: str = Query(default="CA")) -> JSONResponse:
    ready, detail = await model_ready()
    cc = norm_country(country)
    return JSONResponse(
        {
            "ok": True,
            "model": config.OLLAMA_MODEL,
            "model_ready": ready,
            "model_detail": detail,
            "country": cc,
            "country_name": country_profile(cc)["name"],
            "structured": country_profile(cc)["structured"],
            "stats": db.stats(cc),
        }
    )


@app.get("/api/countries")
async def api_countries() -> JSONResponse:
    return JSONResponse({"items": list_countries(), "default": "CA"})


_translate_cache: dict[str, str] = {}


async def _search_terms(q: str | None) -> tuple[list[str], str]:
    q = (q or "").strip()
    if not q:
        return [], ""
    target = "en" if looks_french(q) else "fr"
    translated = glossary_other(q)
    if not translated:
        cached = _translate_cache.get(q.lower())
        if cached is not None:
            translated = cached
        else:
            translated = await translate_query(q, target)
            _translate_cache[q.lower()] = translated
    terms = expand_terms(q, translated)
    return terms, translated


@app.get("/api/findings")
async def api_findings(
    category: str | None = Query(default="all"),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    hide_low: bool = Query(default=True),
    hide_unverified: bool = Query(default=True),
    hide_rejected: bool = Query(default=True),
    sort: str = Query(default="date"),
    country: str = Query(default="CA"),
) -> JSONResponse:
    terms, translated = await _search_terms(q)
    cc = norm_country(country)
    return JSONResponse(
        {
            "items": db.list_findings(
                category=category,
                q=q,
                q_terms=terms or None,
                limit=limit,
                hide_low=hide_low,
                hide_unverified=hide_unverified,
                hide_rejected=hide_rejected,
                sort=sort,
                country=cc,
            ),
            "q": q or "",
            "q_translated": translated,
            "q_terms": terms,
        }
    )


@app.get("/api/hits")
async def api_hits(country: str = Query(default="CA")) -> JSONResponse:
    return JSONResponse({"items": db.list_hits(120, country=norm_country(country))})


@app.get("/api/scans")
async def api_scans(country: str = Query(default="CA")) -> JSONResponse:
    return JSONResponse({"items": db.list_scans(country=norm_country(country))})


@app.get("/api/money")
async def api_money(country: str = Query(default="CA")) -> JSONResponse:
    return JSONResponse({"items": db.list_money(country=norm_country(country))})


@app.get("/api/scoreboard")
async def api_scoreboard(country: str = Query(default="CA")) -> JSONResponse:
    cc = norm_country(country)
    if cc != "CA":
        return JSONResponse(
            {
                "missions": [],
                "platform": [],
                "counts": {"kept": 0, "partial": 0, "broken": 0, "unverified": 0},
                "scored_at": None,
                "note": "scoreboard_ca_only",
                "country": cc,
            }
        )
    last = (db.stats("CA").get("last_scan") or {}).get("id") or 0
    refresh_scoreboard(int(last))
    data = db.list_scoreboard()
    data["country"] = "CA"
    return JSONResponse(data)


@app.get("/api/claims")
async def api_claims(q: str | None = Query(default=None)) -> JSONResponse:
    terms, translated = await _search_terms(q)
    return JSONResponse(
        {
            "items": db.list_claims(q=q, q_terms=terms or None),
            "q": q or "",
            "q_translated": translated,
        }
    )


@app.get("/api/websearch")
async def api_websearch(
    q: str = Query(default=""),
    lang: str = Query(default="en"),
    country: str = Query(default="CA"),
) -> JSONResponse:
    q = q.strip()
    cc = norm_country(country)
    if len(q) < 2:
        return JSONResponse({"items": [], "q": q, "q_en": "", "q_fr": ""})
    terms, translated = await _search_terms(q)
    p = country_profile(cc)
    named = q if cc == "CA" else f"{q} {p['name']}"
    if looks_french(q):
        q_fr, q_en = named, translated or named
    else:
        q_en, q_fr = named, translated or named
    primary = q_fr if lang == "fr" else q_en
    secondary = q_en if lang == "fr" else q_fr
    hits = await searx_search(
        primary, pages=1, language="fr-CA" if lang == "fr" else p.get("lang") or "en", country=cc
    )
    if secondary and secondary.lower() != primary.lower():
        extra = await searx_search(
            secondary, pages=1, language="en-CA" if lang == "fr" else "fr-CA", country=cc
        )
        seen = {h["url"] for h in hits}
        for hit in extra:
            if hit["url"] not in seen:
                hits.append(hit)
                seen.add(hit["url"])
    return JSONResponse(
        {
            "items": hits[:20],
            "q": q,
            "q_en": q_en,
            "q_fr": q_fr,
            "q_terms": terms,
        }
    )


@app.get("/api/entities")
async def api_entities() -> JSONResponse:
    return JSONResponse({"items": db.list_entities()})


@app.get("/api/sources")
async def api_sources() -> JSONResponse:
    return JSONResponse(
        {
            "official_hosts": sorted(OFFICIAL_HOSTS),
            "news_hosts": sorted(NEWS_HOSTS),
            "policy": "Public figures and public records only. No people-search, no private PII.",
        }
    )


@app.post("/api/scan")
async def api_scan(country: str = Query(default="CA")) -> JSONResponse:
    if scan_busy():
        return JSONResponse({"status": "busy"})
    cc = norm_country(country)
    asyncio.create_task(run_scan("manual", country=cc))
    return JSONResponse({"status": "started", "country": cc})


@app.post("/api/finding/{finding_id}/review")
async def api_review(finding_id: int, status: str = Query(default="pending")) -> JSONResponse:
    ok = db.set_review(finding_id, status)
    if not ok:
        return JSONResponse({"error": "bad status or missing finding"}, status_code=400)
    return JSONResponse({"ok": True, "id": finding_id, "review_status": status})


@app.get("/api/finding/{finding_id}")
async def api_finding(finding_id: int) -> JSONResponse:
    item = db.get_finding(finding_id)
    if not item:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(item)


@app.get("/api/entity/{slug}")
async def api_entity(slug: str) -> JSONResponse:
    item = db.get_entity(slug)
    if not item:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(item)
