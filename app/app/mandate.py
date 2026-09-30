"""Parse official mandate letters and related public trackers."""

from __future__ import annotations

import csv
import io
import logging
import zipfile
from typing import Any
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from .privacy import redact_text
from .util import parse_date

log = logging.getLogger("cpl.mandate")
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _map_status(raw: str) -> str:
    sl = (raw or "").lower()
    if any(x in sl for x in ("complete", "kept", "fully met", "delivered")):
        return "kept"
    if any(x in sl for x in ("not being pursued", "broken", "not met", "abandoned")):
        return "broken"
    if any(x in sl for x in ("underway", "on track", "on-going", "ongoing", "in progress", "partial")):
        return "partial"
    return "unverified"


def parse_pco_csv(text: str, source_url: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader):
        title = (row.get("Commitment") or "").strip()
        if len(title) < 12:
            continue
        out.append(
            {
                "title": title[:240],
                "minister": (row.get("Minister") or "").strip(),
                "status": _map_status(row.get("Status") or ""),
                "source_url": source_url,
                "source_date": parse_date(row.get("Updated as of") or row.get("Mandate letter date")),
                "body": redact_text((row.get("Results.Statement") or row.get("Comment") or "")[:1500]),
                "language": "en",
            }
        )
        if i >= 250:
            break
    return out


def parse_xlsx_commitments(blob: bytes, source_url: str, source_date: str | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    try:
        zf = zipfile.ZipFile(io.BytesIO(blob))
        strings: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall(f"{NS}si"):
                strings.append("".join(t.text or "" for t in si.iter(f"{NS}t")))
        sheet = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
    except Exception as exc:
        log.warning("mandate xlsx parse failed: %s", exc)
        return out

    def cell_val(c: ET.Element) -> str:
        v = c.find(f"{NS}v")
        if v is None or v.text is None:
            return ""
        if c.attrib.get("t") == "s":
            try:
                return strings[int(v.text)]
            except (ValueError, IndexError):
                return v.text
        return v.text

    rows = []
    for row in sheet.findall(f".//{NS}row"):
        rows.append([cell_val(c) for c in row.findall(f"{NS}c")])
    if not rows:
        return out
    header = [h.strip() for h in rows[0]]
    for raw in rows[1:251]:
        rec = {header[i]: raw[i] if i < len(raw) else "" for i in range(len(header))}
        title = (rec.get("Commitment") or "").strip()
        if len(title) < 12:
            continue
        out.append(
            {
                "title": title[:240],
                "minister": (rec.get("Reporting Lead") or rec.get("All ministers") or "").strip()[:160],
                "status": "unverified",
                "source_url": source_url,
                "source_date": source_date,
                "body": "2021 PCO mandate-letter commitments workbook.",
                "language": "en",
            }
        )
    return out


def parse_carney_mandate_html(html: str, source_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    claims: list[dict[str, Any]] = []
    date = parse_date(soup.get_text(" ", strip=True)[:400]) or "2025-05-21"
    for ol in soup.find_all("ol"):
        items = [li.get_text(" ", strip=True) for li in ol.find_all("li", recursive=False)]
        if len(items) < 5:
            continue
        for i, text in enumerate(items, 1):
            text = redact_text(text)
            if len(text) < 24:
                continue
            claims.append(
                {
                    "title": f"Carney 2025 mandate priority {i}: {text[:200]}",
                    "minister": "Prime Minister / Cabinet",
                    "status": "unverified",
                    "source_url": source_url,
                    "source_date": date,
                    "body": text[:1500],
                    "language": "en",
                    "board": 1,
                    "cohort": "mandate_2025",
                }
            )
        break
    return claims


def parse_carney_tracker(payload: dict[str, Any], source_url: str) -> list[dict[str, Any]]:
    meta = payload.get("meta") or {}
    as_of = parse_date(meta.get("as_of") or meta.get("generated_at"))
    out: list[dict[str, Any]] = []
    for row in payload.get("pledges") or []:
        if not isinstance(row, dict):
            continue
        title = (row.get("title") or row.get("pledge") or "").strip()
        if len(title) < 8:
            continue
        out.append(
            {
                "title": title[:240],
                "minister": "Carney government (2025 platform)",
                "status": _map_status(str(row.get("status") or "")),
                "source_url": source_url,
                "source_date": as_of,
                "body": redact_text(
                    f"{row.get('pledge') or ''} {row.get('note') or ''} "
                    f"(independent tracker; not a PCO dataset)"
                )[:1500],
                "language": "en",
                "board": 1,
                "cohort": "platform_2025",
            }
        )
    return out
