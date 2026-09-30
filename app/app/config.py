from __future__ import annotations

import os
from pathlib import Path


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return default if value is None or value == "" else value


def _env_int(name: str, default: int) -> int:
    raw = _env(name, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = _env(name, "1" if default else "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


SEARXNG_URL = _env("SEARXNG_URL", "http://searxng:8080").rstrip("/")
OLLAMA_URL = _env("OLLAMA_URL", "http://llm:11434").rstrip("/")
OLLAMA_MODEL = _env("OLLAMA_MODEL", "qwen3:8b")
DB_PATH = Path(_env("CPL_DB_PATH", "/data/cpl.sqlite"))
BACKUP_DIR = Path(_env("CPL_BACKUP_DIR", "/data/backups"))
CACHE_DIR = Path(_env("CPL_CACHE_DIR", "/data/cache"))
SCAN_INTERVAL_MINUTES = max(10, _env_int("SCAN_INTERVAL_MINUTES", 30))
# Only boot-scan when the DB is empty. Recreates must not refill junk.
SCAN_ON_START = _env_bool("SCAN_ON_START", False)
PUBLIC_ONLY = _env_bool("PUBLIC_ONLY", True)
HTTP_TIMEOUT = _env_int("HTTP_TIMEOUT", 25)
FETCH_MAX_CHARS = _env_int("FETCH_MAX_CHARS", 6000)
FETCH_MAX_OFFICIAL = _env_int("FETCH_MAX_OFFICIAL", 24)
LLM_MAX_STORIES = _env_int("LLM_MAX_STORIES", 10)
NUM_CTX = _env_int("OLLAMA_NUM_CTX", 6144)
STALE_HOURS = _env_int("STALE_HOURS", 12)
USER_AGENT = _env(
    "CPL_USER_AGENT",
    "CivicLedger/1.0 (+local-sandbox; public-records research; no-dox)",
)
PARLIAMENT_SESSION = _env("PARLIAMENT_SESSION", "45-1")
CONTRACTS_RESOURCE_ID = _env(
    "CONTRACTS_RESOURCE_ID", "fac950c0-00d5-4ec1-a4d3-9cbebf98a305"
)
LOBBY_PACKAGE_ID = _env("LOBBY_PACKAGE_ID", "a34eb330-7136-4f5e-9f5f-3ba41df58b06")
MANDATE_CSV_URL = _env(
    "MANDATE_CSV_URL",
    "https://opendata.pco.gc.ca/data-donnees/rdu-url/mandat/commitments-engagements-eng.csv",
)
MANDATE_XLSX_2021_URL = _env(
    "MANDATE_XLSX_2021_URL",
    "https://opendata.pco.gc.ca/data-donnees/rdu-url/mandat/commitments-engagements-eng-2021.xlsx",
)
MANDATE_LETTER_2025_URL = _env(
    "MANDATE_LETTER_2025_URL",
    "https://www.pm.gc.ca/en/mandate-letters/2025/05/21/mandate-letter",
)
CARNEY_TRACKER_JSON_URL = _env(
    "CARNEY_TRACKER_JSON_URL",
    "https://carneytracker.xyz/data.json",
)
LOBBY_ZIP_URL = _env(
    "LOBBY_ZIP_URL",
    "https://lobbycanada.gc.ca/media/mqbbmaqk/communications_ocl_cal.zip",
)
LOBBY_ZIP_WAYBACK = _env(
    "LOBBY_ZIP_WAYBACK",
    "https://web.archive.org/web/2026id_/https://lobbycanada.gc.ca/media/mqbbmaqk/communications_ocl_cal.zip",
)
BROWSER_UA = _env(
    "CPL_BROWSER_UA",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
)
