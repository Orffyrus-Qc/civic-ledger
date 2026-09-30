"""Parse the official lobbying communications ZIP (live or Wayback)."""

from __future__ import annotations

import csv
import heapq
import io
import logging
import zipfile
from typing import Any

from .privacy import redact_text
from .util import looks_like_junk_title, parse_date

log = logging.getLogger("cpl.lobby")


def _val(row: dict[str, str], *needles: str) -> str:
    lower = {k.lower(): k for k in row}
    for needle in needles:
        n = needle.lower()
        for lk, orig in lower.items():
            if n == lk or n in lk:
                raw = str(row.get(orig) or "").strip()
                if raw and raw.lower() != "null":
                    return raw
    return ""


def _read_csv(zf: zipfile.ZipFile, name: str) -> csv.DictReader:
    raw = zf.read(name)
    text = raw.decode("utf-8-sig", "replace")
    return csv.DictReader(io.StringIO(text))


def _latest_primary(zf: zipfile.ZipFile, limit: int = 25) -> list[dict[str, str]]:
    reader = _read_csv(zf, "Communication_PrimaryExport.csv")
    heap: list[tuple[str, int, dict[str, str]]] = []
    idx = 0
    for row in reader:
        posted = parse_date(_val(row, "POSTED_DATE_PUBLICATION", "COMM_DATE", "SUBMISSION_DATE")) or ""
        if not posted:
            continue
        item = (posted, idx, dict(row))
        idx += 1
        if len(heap) < limit:
            heapq.heappush(heap, item)
        elif posted > heap[0][0]:
            heapq.heapreplace(heap, item)
    heap.sort(key=lambda x: x[0], reverse=True)
    return [row for _d, _i, row in heap]


def _index_by_id(zf: zipfile.ZipFile, name: str, wanted: set[str]) -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {i: [] for i in wanted}
    if name not in zf.namelist() or not wanted:
        return out
    for row in _read_csv(zf, name):
        cid = _val(row, "COMLOG_ID")
        if cid in out:
            out[cid].append(dict(row))
    return out


def parse_lobby_zip(blob: bytes, source_page: str, limit: int = 20) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        zf = zipfile.ZipFile(io.BytesIO(blob))
    except Exception as exc:
        log.warning("lobby zip open failed: %s", exc)
        return out
    if "Communication_PrimaryExport.csv" not in zf.namelist():
        log.warning("lobby zip missing primary export: %s", zf.namelist())
        return out
    primary = _latest_primary(zf, limit=limit)
    wanted = {_val(r, "COMLOG_ID") for r in primary if _val(r, "COMLOG_ID")}
    dpoh = _index_by_id(zf, "Communication_DpohExport.csv", wanted)
    details = _index_by_id(zf, "Communication_SubjectMatterDetailsExport.csv", wanted)
    seen: set[str] = set()
    for row in primary:
        cid = _val(row, "COMLOG_ID")
        org = redact_text(
            _val(row, "EN_CLIENT_ORG_CORP_NM_AN", "FR_CLIENT_ORG_CORP_NM", "CLIENT")
        )
        if not org or looks_like_junk_title(org):
            continue
        date = parse_date(_val(row, "COMM_DATE", "POSTED_DATE_PUBLICATION"))
        posted = parse_date(_val(row, "POSTED_DATE_PUBLICATION"))
        key = f"{org}:{date}:{cid}"
        if key in seen:
            continue
        seen.add(key)
        holders = []
        for h in dpoh.get(cid, [])[:6]:
            name = " ".join(
                x for x in (_val(h, "DPOH_FIRST_NM_PRENOM_TCPD"), _val(h, "DPOH_LAST_NM_TCPD")) if x
            ).strip()
            title = _val(h, "DPOH_TITLE_TITRE_TCPD")
            inst = _val(h, "INSTITUTION")
            label = ", ".join(x for x in (name, title, inst) if x)
            if label:
                holders.append(redact_text(label))
        desc = ""
        for d in details.get(cid, [])[:1]:
            desc = redact_text(_val(d, "DESCRIPTION"))[:400]
        counterpart = holders[0] if holders else "Designated public office holder"
        snippet = (
            f"{org} filed a federal monthly communication report"
            f"{(' on ' + date) if date else ''}."
        )
        if holders:
            snippet += " Office holders: " + "; ".join(holders[:3]) + "."
        if desc:
            snippet += " " + desc
        title = f"Lobbying communication: {org}"
        if holders:
            title = f"Lobbying: {org} → {holders[0].split(',')[0]}"
        entities = [org, "Office of the Commissioner of Lobbying"] + [
            h.split(",")[0] for h in holders[:3]
        ]
        out.append(
            {
                "title": title[:240],
                "category": "lobbying",
                "summary": snippet[:2000],
                "claim": f"{org} reported an oral and arranged communication with a designated public office holder.",
                "evidence": snippet,
                "entities": entities,
                "money": {"amount": None, "currency": "CAD"},
                "money_amount": None,
                "promise_status": "n/a",
                "confidence": 0.9 if date and holders else 0.75,
                "severity": "medium" if holders else "low",
                "sources": [{"url": source_page, "title": f"Monthly Communication Reports (COMLOG {cid})"}],
                "origin": "extracted",
                "review_status": "pending",
                "source_date": date or posted,
                "language": "en",
                "money_event": {
                    "role": "lobbyist",
                    "actor": org,
                    "counterpart": counterpart,
                    "amount": None,
                    "currency": "CAD",
                    "event_date": date or posted,
                    "source_url": source_page,
                },
            }
        )
    return out


def is_zip_bytes(blob: bytes) -> bool:
    return bool(blob) and blob[:2] == b"PK"
