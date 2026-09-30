"""Strip private-person identifiers. Public-office records stay."""

from __future__ import annotations

import re

SIN_RE = re.compile(r"\b\d{3}[-\s]?\d{3}[-\s]?\d{3}\b")
PHONE_RE = re.compile(
    r"\b(?:\+?1[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b"
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
POSTAL_RE = re.compile(r"\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z][ -]?\d[ABCEGHJ-NPRSTV-Z]\d\b", re.I)
STREET_RE = re.compile(
    r"\b\d{1,5}\s+(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\s+"
    r"(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|Crescent|Cres|Way|Place|Pl|Terrace|Ter)\b",
    re.I,
)
DOX_RE = re.compile(
    r"\b(doxx?(?:ing|ed)?|home address|residential address|personal cell|"
    r"private phone|social insurance|sin number|date of birth|dob:|"
    r"unlisted number)\b",
    re.I,
)

PUBLIC_EMAIL_DOMAINS = (
    "parl.gc.ca",
    "canada.ca",
    "gc.ca",
    "ourcommons.ca",
    "sen.parl.gc.ca",
    "elections.ca",
    "liberal.ca",
    "conservative.ca",
    "ndp.ca",
    "blocquebecois.org",
    "greenparty.ca",
)


def _keep_email(match: re.Match[str]) -> str:
    email = match.group(0)
    domain = email.split("@", 1)[-1].lower()
    if any(domain == d or domain.endswith("." + d) for d in PUBLIC_EMAIL_DOMAINS):
        return email
    return "[redacted-email]"


def redact_text(text: str | None) -> str:
    if not text:
        return ""
    out = SIN_RE.sub("[redacted-id]", text)
    out = EMAIL_RE.sub(_keep_email, out)
    out = PHONE_RE.sub("[redacted-phone]", out)
    out = STREET_RE.sub("[redacted-street]", out)
    out = POSTAL_RE.sub("[redacted-postal]", out)
    out = DOX_RE.sub("[redacted]", out)
    return out.strip()


def looks_like_dox(text: str | None) -> bool:
    if not text:
        return False
    lowered = text.lower()
    hits = 0
    for token in (
        "home address",
        "personal cell",
        "social insurance",
        "unlisted",
        "dox",
        "private residence",
        "children's school",
        "spouse's workplace",
    ):
        if token in lowered:
            hits += 1
    return hits >= 1 and "ethics" not in lowered and "disclosure" not in lowered
